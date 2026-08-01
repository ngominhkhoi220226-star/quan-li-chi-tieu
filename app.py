import streamlit as st
import os
import subprocess
from datetime import datetime
import pandas as pd
import json

# Thư viện Firebase Admin chính thức của Google
import firebase_admin
from firebase_admin import credentials, firestore

st.title(" Ứng dụng Quản lý Chi tiêu ")

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
current_month = datetime.now().strftime("%Y-%m")

if "months_list" not in st.session_state:
    st.session_state.months_list = [current_month]

new_month = st.sidebar.text_input("Nhập tháng mới (VD: 2026-08):", placeholder="YYYY-MM")
if new_month and new_month not in st.session_state.months_list:
    st.session_state.months_list.append(new_month)

selected_month = st.sidebar.selectbox("Chọn tháng cần xem:", st.session_state.months_list)

# 2. Lấy dữ liệu CHUẨN từ đám mây Firebase Firestore về máy chủ Render
collection_ref = db.collection(f"chi_tieu_{selected_month}")
docs = collection_ref.order_by("timestamp", direction=firestore.Query.ASCENDING).stream()

all_records = []
doc_ids = [] 

for doc in docs:
    data = doc.to_dict()
    all_records.append([data["date"], data["category"], data["content"], int(data["amount"])])
    doc_ids.append(doc.id)

# 3. Định nghĩa danh sách các món ăn/nội dung gợi ý sẵn cho từng Danh mục
menu_goi_y = {
    "Ăn uống": ["Cơm", "Phở", "Bún chả", "Mỳ tôm", "Trà sữa", "Cà phê", "Bánh mỳ", "Món khác (Tự nhập)..."],
    "Di chuyển": ["Xăng xe", "Vé xe buýt", "Grab/Be", "Sửa xe/Thay dầu", "Món khác (Tự nhập)..."],
    "Mua sắm": ["Quần áo", "Giày dép", "Đồ dùng cá nhân", "Sách vở", "Món khác (Tự nhập)..."],
    "Học tập": ["Học phí", "Tài liệu học", "Khóa học online", "Món khác (Tự nhập)..."],
    "Khác": ["Tiền điện/nước", "Nạp thẻ điện thoại", "Đi đám cưới/sinh nhật", "Món khác (Tự nhập)..."]
}

# 4. FORM NHẬP LIỆU CHI TIÊU NÂNG CAO (Không dùng st.form để các ô tương tác được với nhau)
st.subheader(f"✍️ Nhập chi tiêu cho tháng {selected_month}")

amount = st.number_input("Số tiền (VNĐ):", min_value=0, step=1000)

# Ô chọn Danh mục chính
category = st.selectbox("Danh mục chính:", list(menu_goi_y.keys()))

# Ô chọn Món gợi ý (Tự động thay đổi danh sách dựa trên Danh mục chính)
selected_suggest = st.selectbox(f"📋 Chọn món gợi ý cho [{category}]:", menu_goi_y[category])

# Nếu người dùng chọn "Món khác (Tự nhập)...", hiện thêm ô nhập tay
if selected_suggest == "Món khác (Tự nhập)...":
    content = st.text_input("✍️ Mời bạn tự nhập tên món mới:", placeholder="Ví dụ: Lẩu thái, buffet, trà chanh...")
else:
    content = selected_suggest # Nếu chọn món có sẵn thì lấy luôn tên món đó

submit = st.button("➕ Thêm khoản chi")

if submit and amount > 0:
    if not content:
        content = "Không có nội dung"
    today = datetime.now().strftime("%Y-%m-%d")
    safe_content = content.replace(",", " ")
    
    # Đẩy dữ liệu trực tiếp lên Firebase Firestore
    new_doc_data = {
        "date": today,
        "category": category,
        "content": safe_content,
        "amount": int(amount),
        "timestamp": firestore.SERVER_TIMESTAMP
    }
    collection_ref.add(new_doc_data)
    st.success(f"🎉 Đã lưu vĩnh viễn món [{safe_content}] lên Firebase!")
    st.rerun()

# 5. Tính năng xóa khoản chi gần nhất nếu lỡ ghi nhầm
if len(all_records) > 0:
    st.write("---")
    if st.button("↩️ Xóa khoản chi vừa nhập (Nếu ghi nhầm)"):
        try:
            collection_ref.document(doc_ids[-1]).delete()
            st.warning("Đã xóa khoản chi gần nhất trên hệ thống Firebase!")
            all_records.pop()
            doc_ids.pop()
            
            with open("data.csv", "w", encoding="utf-8") as f:
                for row in all_records:
                    f.write(f"{row},{row},{row},{row}\n")
            
            if os.path.exists("./processor"):
                subprocess.run(["./processor"])
                
            st.rerun()
        except Exception as e:
            st.error(f"Lỗi khi xóa: {e}")

# 6. ĐỒNG BỘ SANG FILE data.csv để file C++.cpp chạy ngầm tính tổng tiền
if os.path.exists("total.txt"):
    os.remove("total.txt")

if len(all_records) > 0:
    with open("data.csv", "w", encoding="utf-8") as f:
        for row in all_records:
            f.write(f"{row},{row},{row},{row}\n")
            
    if os.path.exists("./processor"):
        subprocess.run(["./processor"])

total_money = 0
if os.path.exists("total.txt"):
    with open("total.txt", "r") as f:
        content_total = f.read().strip()
        if content_total:
            total_money = int(content_total)

st.metric(label=f"Tổng chi tiêu tháng {selected_month} (Xử lý bởi C++)", value=f"{total_money:,} VNĐ")

# 7. Hiển thị lịch sử và tính năng TÌM KIẾM
if len(all_records) > 0:
    st.write("---")
    st.subheader(f"📊 Lịch sử chi tiêu tháng {selected_month}")
    
    df = pd.DataFrame(all_records, columns=["Ngày", "Danh mục", "Nội dung chi tiêu", "Số tiền (VNĐ)"])
    
    search_query = st.text_input("🔍 Tìm kiếm nhanh trong bảng:", placeholder="Nhập từ khóa cần tìm...")
    
    if search_query:
        filtered_df = df[
            df["Nội dung chi tiêu"].str.contains(search_query, case=False, na=False) |
            df["Danh mục"].str.contains(search_query, case=False, na=False)
        ]
        filtered_total = filtered_df["Số tiền (VNĐ)"].sum()
        st.caption(f"💡 Tìm thấy {len(filtered_df)} kết quả. Tổng nhóm này: {filtered_total:,} VNĐ")
        st.dataframe(filtered_df, use_container_width=True)
    else:
        st.dataframe(df, use_container_width=True)
else:
    st.info(f"Tháng {selected_month} chưa có khoản chi nào trên Firebase.")
