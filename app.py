import streamlit as st
import os
import subprocess
from datetime import datetime
import pandas as pd

st.title("💰 Ứng dụng Quản lý Chi tiêu (Lưu Google Drive)")

# Khởi tạo danh sách các tháng ở Sidebar
st.sidebar.header("📅 Quản lý theo Tháng")
current_month = datetime.now().strftime("%Y-%m")

if "months_list" not in st.session_state:
    st.session_state.months_list = [current_month]

new_month = st.sidebar.text_input("Nhập tháng mới (VD: 2026-08):", placeholder="YYYY-MM")
if new_month and new_month not in st.session_state.months_list:
    st.session_state.months_list.append(new_month)

selected_month = st.sidebar.selectbox("Chọn tháng cần xem:", st.session_state.months_list)

# Tên file lưu trữ cục bộ trên máy chủ Render trước khi đồng bộ
local_csv = f"data_{selected_month}.csv"

# Tạo file tiêu đề nếu file chưa tồn tại
if not os.path.exists(local_csv):
    with open(local_csv, "w", encoding="utf-8") as f:
        f.write("Ngày,Danh mục,Nội dung chi tiêu,Số tiền (VNĐ)\n")

# 1. Form nhập liệu chi tiêu
st.subheader(f"✍️ Nhập chi tiêu cho tháng {selected_month}")
with st.form("expense_form", clear_on_submit=True):
    amount = st.number_input("Số tiền (VNĐ):", min_value=0, step=1000)
    category = st.selectbox("Danh mục:", ["Ăn uống", "Di chuyển", "Mua sắm", "Học tập", "Khác"])
    content = st.text_input("Nội dung chi tiêu:")
    submit = st.form_submit_button("➕ Thêm khoản chi")

if submit and amount > 0:
    if not content:
        content = "Không có nội dung"
    today = datetime.now().strftime("%Y-%m-%d")
    safe_content = content.replace(",", " ")
    
    # Ghi dữ liệu vào file cục bộ
    with open(local_csv, "a", encoding="utf-8") as f:
        f.write(f"{today},{category},{safe_content},{int(amount)}\n")
    st.success("Đã ghi nhận khoản chi mới!")

# 2. Đưa dữ liệu sang file data.csv tạm thời để C++ chạy ngầm tính tổng tiền
if os.path.exists(local_csv):
    # Đọc file bỏ dòng tiêu đề đầu tiên trước khi đưa cho C++
    with open(local_csv, "r", encoding="utf-8") as f:
        lines = f.readlines()[1:]
        
    with open("data.csv", "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line)
            
    # Gọi file C++ chạy ngầm tính toán
    if os.path.exists("./processor"):
        subprocess.run(["./processor"])

# Đọc tổng tiền từ file text do C++ xuất ra
total_money = 0
if os.path.exists("total.txt"):
    with open("total.txt", "r") as f:
        content_total = f.read().strip()
        if content_total:
            total_money = int(content_total)

st.metric(label=f"Tổng chi tiêu tháng {selected_month}", value=f"{total_money:,} VNĐ")

# 3. Hiển thị lịch sử dạng bảng đẹp mắt
try:
    df = pd.read_csv(local_csv)
    if len(df) > 0:
        st.subheader(f"📊 Lịch sử chi tiêu tháng {selected_month}")
        st.dataframe(df, use_container_width=True)
        
        # 4. Nút bấm đồng bộ sao lưu file này lên Google Drive khi cần
        st.write("---")
        st.subheader("☁️ Sao lưu dữ liệu")
        st.info("Tính năng tải file chi tiêu trực tiếp về máy của bạn để cất vào Google Drive:")
        
        # Chuyển đổi dữ liệu thành file CSV để người dùng bấm tải về điện thoại dán vào Drive
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label=f"📥 Tải file data_{selected_month}.csv về máy",
            data=csv_data,
            file_name=f"data_{selected_month}.csv",
            mime="text/csv",
        )
except Exception as e:
    st.info(f"Tháng {selected_month} chưa có khoản chi nào.")
