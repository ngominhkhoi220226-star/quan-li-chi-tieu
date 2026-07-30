import streamlit as st
import os
import subprocess
from datetime import datetime
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.title("💰 Ứng dụng Quản lý Chi tiêu Đám mây")

# 1. Kết nối Google Sheets
scope = ["https://google.com", "https://googleapis.com"]
try:
    creds = Credentials.from_service_account_file("google_creds.json", scopes=scope)
    gc = gspread.authorize(creds)
    sh = gc.open("QuanLyChiTieu")
except Exception as e:
    st.error("Lỗi kết nối Google Sheets. Vui lòng kiểm tra lại file google_creds.json")

# Quản lý danh sách các tháng ở Sidebar
st.sidebar.header("📅 Quản lý theo Tháng")
current_month = datetime.now().strftime("%Y-%m")

if "months_list" not in st.session_state:
    st.session_state.months_list = [current_month]

new_month = st.sidebar.text_input("Nhập tháng mới (VD: 2026-08):", placeholder="YYYY-MM")
if new_month and new_month not in st.session_state.months_list:
    st.session_state.months_list.append(new_month)

selected_month = st.sidebar.selectbox("Chọn tháng cần xem:", st.session_state.months_list)

# Tên trang tính (Worksheet) riêng cho từng tháng
try:
    worksheet = sh.worksheet(selected_month)
except gspread.exceptions.WorksheetNotFound:
    worksheet = sh.add_worksheet(title=selected_month, rows="1000", cols="4")
    worksheet.append_row(["Ngày", "Danh mục", "Nội dung chi tiêu", "Số tiền (VNĐ)"])

# 2. Form nhập liệu
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
    
    # Ghi dữ liệu trực tiếp lên đám mây Google Sheets
    worksheet.append_row([today, category, safe_content, int(amount)])
    st.success("Đã lưu dữ liệu lên Google Sheets!")

# 3. Đồng bộ về máy chủ Render để chạy C++ tính tổng tiền
all_records = worksheet.get_all_values()

# Tạo file data.csv tạm thời từ Google Sheets để C++ đọc
if len(all_records) > 1:
    data_to_cpp = all_records[1:]
    with open("data.csv", "w", encoding="utf-8") as f:
        for row in data_to_cpp:
            # Ghi định dạng chuẩn CSV: Ngày,Danh mục,Nội dung,Số tiền
            f.write(f"{row[0]},{row[1]},{row[2]},{row[3]}\n")
            
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

# 4. Hiển thị lịch sử dạng bảng
if len(all_records) > 1:
    st.subheader(f"📊 Lịch sử chi tiêu tháng {selected_month}")
    df = pd.DataFrame(all_records[1:], columns=all_records[0])
    st.dataframe(df, use_container_width=True)
else:
    st.info(f"Tháng {selected_month} chưa có khoản chi nào.")
