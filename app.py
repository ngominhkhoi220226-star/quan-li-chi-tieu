import streamlit as st
import os
import subprocess
from datetime import datetime
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

st.title("💰 Ứng dụng Quản lý Chi tiêu Đám mây v2")

# 1. Kết nối Google Sheets trực tiếp qua Biến môi trường Render
scope = ["https://google.com", "https://googleapis.com"]
google_creds_raw = os.environ.get("GOOGLE_CREDENTIALS")

if not google_creds_raw:
    st.error("❌ Hệ thống chưa thiết lập cấu hình kết nối Google Drive! Vui lòng kiểm tra lại mục Environment trên Render.")
    st.stop()

try:
    info = json.loads(google_creds_raw)
    creds = Credentials.from_service_account_info(info, scopes=scope)
    gc = gspread.authorize(creds)
    # Mở file Google Trang tính nằm trên Google Drive của bạn
    sh = gc.open("QuanLyChiTieu")
except Exception as e:
    st.error(f"❌ Lỗi xác thực với Google: {e}. Vui lòng kiểm tra lại ô Value trên Render hoặc quyền chia sẻ file Trang tính.")
    st.stop()

# Quản lý danh sách các tháng ở Sidebar
st.sidebar.header("📅 Quản lý theo Tháng")
current_month = datetime.now().strftime("%Y-%m")

if "months_list" not in st.session_state:
    st.session_state.months_list = [current_month]

new_month = st.sidebar.text_input("Nhập tháng mới (VD: 2026-08):", placeholder="YYYY-MM")
if new_month and new_month not in st.session_state.months_list:
    st.session_state.months_list.append(new_month)

selected_month = st.sidebar.selectbox("Chọn tháng cần xem:", st.session_state.months_list)

# Tên trang tính riêng cho từng tháng trên Google Drive
try:
    worksheet = sh.worksheet(selected_month)
except gspread.exceptions.WorksheetNotFound:
    worksheet = sh.add_worksheet(title=selected_month, rows="1000", cols="4")
    worksheet.append_row(["Ngày", "Danh mục", "Nội dung chi tiêu", "Số tiền (VNĐ)"])

# 2. Form nhập liệu chi tiêu
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
    
    # Ghi dữ liệu trực tiếp lên đám mây Google Drive / Google Sheets
    worksheet.append_row([today, category, safe_content, int(amount)])
    st.success("Đã lưu dữ liệu thẳng lên Google Drive của bạn!")

# lấy toàn bộ dữ liệu từ Google Drive về máy chủ để đồng bộ xử lý
all_records = worksheet.get_all_values()

# 3. Tính năng xóa khoản chi gần nhất nếu lỡ ghi nhầm
if len(all_records) > 1:
    st.write("---")
    if st.button("↩️ Xóa khoản chi vừa nhập (Nếu ghi nhầm)"):
        # Lệnh xóa dòng cuối cùng trên file Google Drive
        worksheet.delete_rows(len(all_records))
        st.warning("Đã xóa khoản chi gần nhất! Hãy bấm nút 'Cập nhật lại dữ liệu' hoặc tải lại trang.")
        st.rerun()

# 4. Đồng bộ dữ liệu sang file tạm thời để file C++.cpp chạy ngầm tính tổng tiền
if len(all_records) > 1:
    data_to_cpp = all_records[1:]
    with open("data.csv", "w", encoding="utf-8") as f:
        for row in data_to_cpp:
            if len(row) >= 4:
                f.write(f"{row},{row},{row},{row}\n")
            
    # Gọi file C++.cpp đã biên dịch để tính toán
    if os.path.exists("./processor"):
        subprocess.run(["./processor"])

# Đọc tổng tiền do file C++ tính toán xuất ra
total_money = 0
if os.path.exists("total.txt"):
    with open("total.txt", "r") as f:
        content_total = f.read().strip()
        if content_total:
            total_money = int(content_total)

st.metric(label=f"Tổng chi tiêu tháng {selected_month}", value=f"{total_money:,} VNĐ")

# 5. Hiển thị lịch sử dạng bảng từ Drive
if len(all_records) > 1:
    st.subheader(f"📊 Lịch sử chi tiêu tháng {selected_month}")
    df = pd.DataFrame(all_records[1:], columns=all_records)
    st.dataframe(df, use_container_width=True)
else:
    st.info(f"Tháng {selected_month} chưa có khoản chi nào vĩnh viễn trên Drive.")
