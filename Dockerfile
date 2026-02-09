FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 更新包索引並安裝基礎系統依賴
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 複製需求檔案並安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安裝 Playwright 瀏覽器及其依賴（自動安裝所需系統庫）
RUN playwright install --with-deps chromium

# 複製應用程式代碼
COPY . .
