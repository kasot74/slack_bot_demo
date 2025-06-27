# 使用官方 Python 基礎映像檔
FROM python:3.9-slim
RUN apt-get update && apt-get install -y tzdata && \
    ln -sf /usr/share/zoneinfo/Asia/Taipei /etc/localtime && \
    echo "Asia/Taipei" > /etc/timezone && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
# 設定工作目錄
WORKDIR /app

COPY . .

# 安裝需求
RUN pip install --no-cache-dir -r requirements.txt
