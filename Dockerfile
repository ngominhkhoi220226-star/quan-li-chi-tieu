FROM python:3.11-slim

# Cài đặt trình biên dịch g++ của Linux trên máy chủ Render
RUN apt-get update && apt-get install -y g++ && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

# Cài đặt đầy đủ các thư viện cần thiết bao gồm cả firebase-admin
RUN pip install streamlit pandas firebase-admin

# Biên dịch chính xác tên file C++.cpp của bạn trên máy chủ đám mây
RUN g++ "C++.cpp" -o processor

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
