import os
import datetime,time
import requests
import io
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
from io import BytesIO
from PIL import Image
from stability_sdk import client
from .AI_Service.xai import painting
from .utilities import read_config
# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
api_key=config['STABILITY_API_KEY']

#sampler_list ["DDIM", "PLMS", "K_euler", "K_euler_ancestral", "K_heun", "K_dpm_2", "K_dpm_2_ancestral", "K_lms", "K_dpmpp_2m", "K_dpmpp_2s_ancestral"]
#engine_list ["stable-diffusion-512-v2-1","stable-diffusion-xl-beta-v2-2-2"]
#style_preset 
# [3d-model ,analog-film ,anime ,cinematic ,comic-book ,digital-art ,enhance ,fantasy-art 
#  ,isometric ,line-art ,low-poly ,modeling-compound ,neon-punk ,origami ,photographic 
#  ,pixel-art ,tile-texture]
stability_api = client.StabilityInference(key=api_key)
def get_image(text):    
    # Create directory if not exists    
    
    # 構建新的目錄路徑
    image_dir = os.path.join("images", "stability_image")
    # 如果目錄不存在，則創建它    
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)
    # Generate image using Stability AI            
    try:
        prompt_str = painting(text)                
        answers = stability_api.generate(prompt=prompt_str)        
        for resp in answers:
            for artifact in resp.artifacts:                                
                if artifact.type == generation.ARTIFACT_IMAGE:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    img_filename = f"{timestamp}.png"
                    img = Image.open(io.BytesIO(artifact.binary))
                    image_dir = os.path.join(image_dir,img_filename)
                    img.save(image_dir,"png") # Save our generated images with their seed number as the filename.                    
                    
                    #回傳路徑
                    file_path = os.path.join("stability_image",img_filename)
        return f"{text}繪圖成功! :art: ", file_path
    except Exception as e:
        # Handle potential errors during image generation                
        return f"繪圖失敗! {e}", None
def get_image2(test):    
    response = requests.post(
        f"https://api.stability.ai/v2beta/stable-image/generate/ultra",
        headers={
            "authorization": f"Bearer {api_key}",
            "accept": "image/*"
        },
        files={"none": ''},
        data={
            "prompt": test,
            "output_format": "png",
        },
    )
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")    
    if response.status_code == 200:
        img_filename = f"{timestamp}.png"
        with open(f"stability_image/{img_filename}", 'wb') as file:
            file.write(response.content)
        file_path = os.path.join("stability_image",img_filename)
        return f"{test}繪圖成功! :art: ", file_path
    else:
        return f"繪圖失敗! {str(response.json())}", None

def change_style(image_url):
    style_image = "https://herry537.sytes.net/uploads/%E5%90%89%E4%BC%8A%E5%8D%A1%E5%A8%83/1000003082.jpg"
    #檢查URL
    if image_url.startswith("<") and image_url.endswith(">"):
        image_url = image_url[1:-1]
    # 檢查 image_url 是否為 URL，並下載檔案
    if image_url.startswith("http://") or image_url.startswith("https://"):
        response = requests.get(image_url)
        if response.status_code == 200:
            init_image = BytesIO(response.content)
        else:
            return f"無法下載圖片，錯誤代碼：{response.status_code}", None
    else:
        # 如果是本地檔案，直接開啟
        init_image = open(image_url, "rb")

    # 同樣處理 style_image
    style_response = requests.get(style_image)
    if style_response.status_code == 200:
        style_image_data = BytesIO(style_response.content)
    else:
        return f"無法下載風格圖片，錯誤代碼：{style_response.status_code}", None

    response = requests.post(
        f"https://api.stability.ai/v2beta/stable-image/control/style-transfer",
        headers={
            "authorization": f"Bearer {api_key}",
            "accept": "image/*"
        },
        files={
            "init_image": init_image,
            "style_image": style_image_data
        },
        data={
            "output_format": "png",
        },
    )

    if response.status_code == 200:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        img_filename = f"{timestamp}.png"
        with open(f"stability_image/{img_filename}", 'wb') as file:
            file.write(response.content)
        file_path = os.path.join("stability_image", img_filename)
        return f"修改風格成功! :art: ", file_path
    else:
        return f"修改風格失敗! {str(response.json())}", None