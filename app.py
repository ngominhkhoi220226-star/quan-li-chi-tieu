import streamlit as st
import os
import subprocess
from datetime import datetime
import pandas as pd
import json

# Thư viện Firebase Admin chính thức của Google
import firebase_admin
from firebase_admin import credentials, firestore

st.title(" Ứng dụng Quản lý Chi tiêu của cả nhà ")

# 1. Khởi tạo kết nối Firebase bằng biến môi trường Render
google_creds_raw = os.environ.get("GOOGLE_CREDENTIALS")

if not google_creds_raw:
    st.error("❌ Chưa thiết lập cấu hình GOOGLE_CREDENTIALS trong Environment của Render!")
    st.stop()

# Khởi tạo Firebase App duy nhất một lần
if not firebase_admin._apps:
    try:
        info = json.loads(google_creds_raw)
        cred = credentials.Certificate(info)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"❌ Lỗi cấu hình file bí mật JSON: {e}")
        st.stop()

# Kết nối cơ sở dữ liệu Firestore
db = firestore.client()

# Quản lý danh sách các tháng ở Sidebar
st.sidebar.header("📅 Quản lý theo Tháng")
current_month = datetime.now().strftime("%m-%y")

if "months_list" not in st.session_state:
    st.session_state.months_list = [current_month]

new_month = st.sidebar.text_input("Nhập tháng mới (VD: 1-08-2026):", placeholder="D-MM-YYYY")
if new_month and new_month not in st.session_state.months_list:
    st.session_state.months_list.append(new_month)

selected_month = st.sidebar.selectbox("Chọn tháng cần xem:", st.session_state.months_list)

# 2. Đồng bộ dữ liệu từ đám mây Firebase Firestore về máy chủ Render
# Truy cập vào bảng dữ liệu (Collection) tương ứng của tháng
collection_ref = db.collection(f"chi_tieu_{selected_month}")
docs = collection_ref.order_by("timestamp", direction=firestore.Query.ASCENDING).stream()

all_records = [["Ngày", "Danh mục", "Nội dung chi tiêu", "Số tiền (VNĐ)"]]
doc_ids = [] # Lưu lại ID của các phần tử để xóa nếu nhập nhầm

for doc in docs:
    data = doc.to_dict()
    all_records.append([data["date"], data["category"], data["content"], int(data["amount"])])
    doc_ids.append(doc.id)

# 3. Form nhập liệu chi tiêu
st.subheader(f"✍️ Nhập chi tiêu cho tháng {selected_month}")
with st.form("expense_form", clear_on_submit=True):
    amount = st.number_input("Số tiền (VNĐ):", min_value=0, step=1000)
    category = st.selectbox("Danh mục:", ["Ăn uống", "Di chuyển", "Mua sắm", "Học tập", "Khác"])
    content = st.text_input("Nội dung chi tiêu:")
    submit = st.form_submit_button("➕ Thêm khoản chi")

if submit and amount > 0:
    if not content:
        content = "Không có nội dung"
    today = datetime.now().strftime("%d-%m-%y")
    safe_content = content.replace(",", " ")
    
    # Đẩy dữ liệu trực tiếp lên Firebase Firestore (Lưu vĩnh viễn không sợ mất)
    new_doc_data = {
        "date": today,
        "category": category,
        "content": safe_content,
        "amount": int(amount),
        "timestamp": firestore.SERVER_TIMESTAMP # Lưu mốc thời gian để sắp xếp thứ tự
    }
    collection_ref.add(new_doc_data)
    st.success("🎉 Đã lưu dữ liệu thẳng lên đám mây Firebase vĩnh viễn!")
    st.rerun()

# 4. Tính năng xóa khoản chi gần nhất nếu lỡ ghi nhầm (Đã sửa lỗi không trừ tiền)
if len(all_records) > 1:
    st.write("---")
    if st.button("↩️ Xóa khoản chi vừa nhập (Nếu ghi nhầm)"):
        try:
            # Tiến hành xóa phần tử cuối cùng trên Firebase
            collection_ref.document(doc_ids[-1]).delete()
            st.warning("Đã xóa khoản chi gần nhất trên hệ thống Firebase!")
            
            # Ép buộc đồng bộ bộ nhớ tạm thời ngay lập tức
            all_records.pop()
            doc_ids.pop()
            
            # Ghi đè lại file data.csv sạch để đưa cho C++ tính lại số tiền
            with open("data.csv", "w", encoding="utf-8") as f:
                for row in all_records[1:]:
                    f.write(f"{row},{row},{row},{row}\n")
            
            # Gọi file C++.cpp chạy ngầm tính toán lại tiền mới ngay lập tức
            if os.path.exists("./processor"):
                subprocess.run(["./processor"])
                
            # Tải lại giao diện để hiển thị số tiền mới và bảng mới
            st.rerun()
        except Exception as e:
            st.error(f"Lỗi khi xóa: {e}")

# 5. Đồng bộ dữ liệu sang file data.csv cho luồng chạy thông thường
if len(all_records) > 1:
    with open("data.csv", "w", encoding="utf-8") as f:
        for row in all_records[1:]:
            # Ghi định dạng chuẩn 4 cột: Ngày,Danh mục,Nội dung,Số tiền
            f.write(f"{row},{row},{row},{row}\n")
            
    # Gọi file C++.cpp của bạn đã biên dịch để tính toán tổng tiền
    if os.path.exists("./processor"):
        subprocess.run(["./processor"])

# Đọc tổng tiền do file C++ tính toán xuất ra
total_money = 0
if os.path.exists("total.txt"):
    with open("total.txt", "r") as f:
        content_total = f.read().strip()
        if content_total:
            total_money = int(content_total)

st.metric(label=f"Tổng chi tiêu tháng {selected_month} (Xử lý bởi C++)", value=f"{total_money:,} VNĐ")

# 6. Hiển thị lịch sử và tính năng TÌM KIẾM nâng cao
if len(all_records) > 1:
    st.write("---")
    st.subheader(f"📊 Lịch sử chi tiêu tháng {selected_month}")
    
    # Tạo bảng dữ liệu pandas từ records
    df = pd.DataFrame(all_records[1:], columns=all_records[0])
    
    # Ô nhập từ khóa tìm kiếm (Tìm theo Danh mục hoặc Nội dung chi tiêu)
    search_query = st.text_input("🔍 Tìm kiếm khoản chi (Nhập từ khóa nội dung hoặc danh mục):", placeholder="Ví dụ: cơm, trà sữa, mua sắm...")
    
    # Thực hiện lọc dữ liệu nếu có từ khóa
    if search_query:
        # Lọc không phân biệt chữ hoa chữ thường
        filtered_df = df[
            df["Nội dung chi tiêu"].str.contains(search_query, case=False, na=False) |
            df["Danh mục"].str.contains(search_query, case=False, na=False)
        ]
        
        # Tính toán nhanh tổng tiền của các khoản vừa lọc được bằng Python để hiển thị thêm
        filtered_total = filtered_df["Số tiền (VNĐ)"].sum()
        st.caption(f"💡 Tìm thấy {len(filtered_df)} kết quả phù hợp. Tổng tiền nhóm này: {filtered_total:,} VNĐ")
        
        # Hiển thị bảng đã lọc
        st.dataframe(filtered_df, use_container_width=True)
    else:
        # Nếu không tìm kiếm, hiển thị toàn bộ bảng như cũ
        st.dataframe(df, use_container_width=True)
else:
    st.info(f"Tháng {selected_month} chưa có khoản chi nào.")
