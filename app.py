import streamlit as st
import os
import subprocess
from datetime import datetime
import pandas as pd

st.title("💰 Ứng dụng Quản lý Chi tiêu Nâng cao")

# 1. Quản lý danh sách các tháng (Bảng mới) bằng thanh bên trái (Sidebar)
st.sidebar.header("📅 Quản lý theo Tháng")

# Lấy tháng hiện tại làm mặc định (Định dạng: YYYY-MM)
current_month = datetime.now().strftime("%Y-%m")

# Khởi tạo danh sách các tháng trong session_state nếu chưa có
if "months_list" not in st.session_state:
    st.session_state.months_list = [current_month]

# Ô nhập để tạo tháng mới (Bấm dấu cộng hoặc nhập tháng)
new_month = st.sidebar.text_input("Nhập tháng mới (VD: 2026-08) rồi bấm Enter:", placeholder="YYYY-MM")
if new_month and new_month not in st.session_state.months_list:
    st.session_state.months_list.append(new_month)
    st.sidebar.success(f"Đã tạo bảng cho tháng {new_month}!")

# Hộp chọn tháng để xem dữ liệu
selected_month = st.sidebar.selectbox("Chọn tháng cần xem/nhập liệu:", st.session_state.months_list)

# Xác định tên file dữ liệu riêng cho từng tháng để tránh lẫn lộn
data_file = f"data_{selected_month}.csv"
total_file = f"total_{selected_month}.txt"

# 2. Form nhập liệu chi tiêu cho tháng đã chọn
st.subheader(f"✍️ Nhập chi tiêu cho tháng {selected_month}")
with st.form("expense_form", clear_on_submit=True):
    amount = st.number_input("Số tiền (VNĐ):", min_value=0, step=1000)
    category = st.selectbox("Danh mục:", ["Ăn uống", "Di chuyển", "Mua sắm", "Học tập", "Khác"])
    content = st.text_input("Nội dung chi tiêu:", placeholder="Ví dụ: Mua bút bi, Ăn bún chả...")
    submit = st.form_submit_button("➕ Thêm khoản chi")

if submit and amount > 0:
    # Điền mặc định nếu người dùng để trống nội dung
    if not content:
        content = "Không có nội dung"
        
    # Chuẩn bị dữ liệu để ghi vào file CSV tạm thời (luôn dùng tên data.csv để C++ xử lý)
    # Nếu file của tháng đã tồn tại thì copy sang data.csv trước khi chạy C++
    if os.path.exists(data_file):
        os.system(f"cp {data_file} data.csv")
    elif os.path.exists("data.csv"):
        os.system("rm data.csv") # Xóa file cũ nếu đổi tháng
        
    today = datetime.now().strftime("%Y-%m-%d")
    # Xử lý xóa dấu phẩy trong nội dung để không làm lệch cột CSV
    safe_content = content.replace(",", " ")
    
    with open("data.csv", "a", encoding="utf-8") as f:
        f.write(f"{today},{category},{safe_content},{amount}\n")
    
    # Lưu lại vào file của tháng tương ứng
    os.system(f"cp data.csv {data_file}")
    
    # Gọi file C++ chạy ngầm (Sử dụng đường dẫn tuyệt đối trong WSL)
    cpp_path = "/mnt/g/phanmem/processor"
    if os.path.exists(cpp_path):
        subprocess.run([cpp_path])
        # Lưu kết quả tổng tiền riêng cho tháng đó
        if os.path.exists("total.txt"):
            os.system(f"cp total.txt {total_file}")

# 3. Đọc tổng tiền của tháng đã chọn và hiển thị
total_money = 0
if os.path.exists(total_file):
    with open(total_file, "r") as f:
        content_total = f.read().strip()
        if content_total:
            total_money = int(content_total)

st.metric(label=f"Tổng chi tiêu tháng {selected_month}", value=f"{total_money:,} VNĐ")

# 4. Hiển thị Lịch sử chi tiêu dạng bảng (Table) đẹp mắt
if os.path.exists(data_file):
    st.subheader(f"📊 Lịch sử chi tiêu tháng {selected_month}")
    try:
        df = pd.read_csv(data_file, names=["Ngày", "Danh mục", "Nội dung chi tiêu", "Số tiền (VNĐ)"])
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.info("Chưa có dữ liệu hợp lệ cho tháng này.")
else:
    st.info(f"Tháng {selected_month} chưa có khoản chi nào được ghi nhận.")
