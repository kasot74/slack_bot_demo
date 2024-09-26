import requests
import asyncio
import aiohttp
from datetime import datetime
from .utilities import read_config
# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
api_key=config['STABILITY_API_KEY']

async def get_image(text):
    url = "https://api.stability.ai/v2beta/stable-image/generate/core"  # 使用較少積分的核心模型
    headers =  {"authorization": f"Bearer {api_key}", "accept": "image/*" }
    data =  { "prompt": text, "output_format": "jpeg" } # 使用傳入的文字作為提示詞
    files={"none": ''}

    flag = True
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers , data=data) as response:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"images/stability_image/{timestamp}.jpeg"
            if response.status_code == 200:                
                with open(file_name, 'wb') as file:
                    file.write(await response.read())                                
            else:
                flag = False
                # 處理 API 回傳錯誤                
    if flag:
        return file_name, f"我畫完 {text}"
    else:
        return None, f"錯誤!! 太難了! {response.status_code}"
