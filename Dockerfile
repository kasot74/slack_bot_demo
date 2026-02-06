# 使用官方 Python 基礎映像檔 (升級至 3.11 以避免 EOL 警告並提升穩定性)
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

COPY . .

# 安裝需求
RUN pip install --no-cache-dir -r requirements.txt
