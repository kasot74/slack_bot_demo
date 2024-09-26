import requests
from datetime import datetime
from .utilities import read_config
# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
api_key=config['STABILITY_API_KEY']

def get_image(text):
    response = requests.post(
        f"https://api.stability.ai/v2beta/stable-image/generate/core",  # 使用較少積分的核心模型
        headers={
            "authorization": f"Bearer {api_key}",
            "accept": "image/*"
        },
        files={"none": ''},
        data={
            "prompt": text,  # 使用傳入的文字作為提示詞
            "output_format": "jpeg",
        },
    )

    if response.status_code == 200:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 使用時間戳作為檔案名稱，將圖片存放於指定路徑
        file_name = f"images/stability_image/{timestamp}.jpeg"
        with open(file_name, 'wb') as file:
            file.write(response.content)

        # 傳回圖片檔案路徑與成功訊息
        return file_name, f"我畫完{text}"
    else:
        # 處理 API 回傳錯誤
        return None,f"錯誤!! 太難了! {response.status_code} "