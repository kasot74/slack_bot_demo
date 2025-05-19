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
    prompt_str = painting(text)  
    response = requests.post(
        f"https://api.stability.ai/v2beta/stable-image/generate/ultra",
        headers={
            "authorization": f"Bearer {api_key}",
            "accept": "image/*"
        },
        files={"none": ''},
        data={
            "prompt": prompt_str,
            "output_format": "png",
        },
    )
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")    
    if response.status_code == 200:
        # 確保目錄存在
        image_dir = os.path.join("images", "stability_image")
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)

        # 儲存圖片到指定路徑
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        img_filename = f"{timestamp}.png"
        img_path = os.path.join(image_dir, img_filename)

        # 將 JPEG 位元組轉換為 PNG 並儲存
        try:
            img = Image.open(BytesIO(response.content))  # 開啟 JPEG 圖片
            img.save(img_path, "PNG")  # 儲存為 PNG 格式
            file_path = os.path.join("stability_image",img_filename)
            return f"繪圖成功! :art: ", file_path
        except Exception as e:
            return f"繪圖失敗! {e}", None
    else:
        return f"繪圖失敗! {str(response.json())}", None

def change_style(image_input,style_image,text):
    if not isinstance(image_input, BytesIO):  # 確保輸入是 BytesIO
        return "無效的圖片輸入類型，請提供 BytesIO 圖片資料", None
    if not isinstance(style_image, BytesIO):  # 確保輸入是 BytesIO
        return "無效的圖片輸入類型，請提供 BytesIO 圖片資料", None
    prompt_str = painting(text)  
    # 發送請求到 Stability AI 的風格轉換 API
    try:
        response = requests.post(
            f"https://api.stability.ai/v2beta/stable-image/control/style-transfer",
            headers={
                "authorization": f"Bearer {api_key}",
                "accept": "image/*"
            },
            files={
                "init_image": image_input,
                "style_image": style_image
            },
            data={
                "prompt": prompt_str,                
                "output_format": "png",
                "style_strength": 0.5,  # 風格強度
                "composition_fidelity": 0.5  # 組合保真度
            },
        )
    except Exception as e:
        return f"change_style 請求失敗：{e}", None
    finally:
        style_image.close()  # 確保風格圖片檔案被正確關閉

    # 處理 API 回應
    if response.status_code == 200:
        # 確保目錄存在
        image_dir = os.path.join("images", "change_style")
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)

        # 儲存圖片到指定路徑
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        img_filename = f"{timestamp}.png"
        img_path = os.path.join(image_dir, img_filename)

        # 儲存圖片
        try:
            img = Image.open(BytesIO(response.content))  # 開啟圖片
            img.save(img_path, "PNG")  # 儲存為 PNG 格式
            file_path = os.path.join("change_style", img_filename)
            return f"修改風格成功! :art: ", file_path
        except Exception as e:
            return f"圖片處理失敗! {e}", None
    else:
        return f"修改風格失敗! {str(response.json())}", None

def change_image(image_input,text):
    if not isinstance(image_input, BytesIO):  # 確保輸入是 BytesIO
        return "無效的圖片輸入類型，請提供 BytesIO 圖片資料", None
    
    prompt_str = painting(text)  
    # 發送請求到 Stability AI 的風格轉換 API
    try:
        response = requests.post(
            f"https://api.stability.ai/v2beta/stable-image/control/style-transfer",
            headers={
                "authorization": f"Bearer {api_key}",
                "accept": "image/*"
            },
            files={
                "init_image": image_input,
                "style_image": image_input
            },
            data={
                "prompt": prompt_str,                
                "output_format": "png",
                "style_strength": 1,  # 風格強度
                "composition_fidelity": 1  # 組合保真度
            },
        )
    except Exception as e:
        return f"change_style 請求失敗：{e}", None
    finally:
        image_input.close()  # 確保風格圖片檔案被正確關閉

    # 處理 API 回應
    if response.status_code == 200:
        # 確保目錄存在
        image_dir = os.path.join("images", "change_style")
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)

        # 儲存圖片到指定路徑
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        img_filename = f"{timestamp}.png"
        img_path = os.path.join(image_dir, img_filename)

        # 儲存圖片
        try:
            img = Image.open(BytesIO(response.content))  # 開啟圖片
            img.save(img_path, "PNG")  # 儲存為 PNG 格式
            file_path = os.path.join("change_style", img_filename)
            return f"修改成功! :art: ", file_path
        except Exception as e:
            return f"圖片處理失敗! {e}", None
    else:
        return f"修改失敗! {text} {str(response.json())}", None