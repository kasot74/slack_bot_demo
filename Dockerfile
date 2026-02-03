# 使用官方 Python 基礎映像檔
FROM python:3.9-slim

# 設定工作目錄
WORKDIR /app

COPY . .

# 安裝需求
RUN pip install --no-cache-dir -r requirements.txt
