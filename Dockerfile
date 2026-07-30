# Sử dụng môi trường Python chính thức
FROM python:3.11-slim

# Cài đặt trình biên dịch g++ của Linux trên máy chủ
RUN apt-get update && apt-get install -y g++ && rm -rf /var/lib/apt/lists/*

# Tạo thư mục làm việc trong máy chủ
WORKDIR /app

# Sao chép toàn bộ code của bạn vào máy chủ
COPY . /app

# Cài đặt các thư viện Python cần thiết
RUN pip install streamlit pandas

# Biên dịch file C++ ngay trên máy chủ Linux
RUN g++ C++.cpp -o processor

# Mở cổng kết nối của Streamlit
EXPOSE 8501

# Lệnh để chạy app khi máy chủ khởi động
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
