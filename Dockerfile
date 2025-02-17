# 使用官方 Python 基礎映像檔
FROM python:3.9-slim

# 設定工作目錄
WORKDIR /app

# 複製需求文件到容器
COPY requirements.txt .

# 安裝需求
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式文件到容器
COPY . .

# 指定運行應用程式的命令
CMD ["python", "-m", "src.bot_main"]