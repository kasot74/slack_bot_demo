import os
import datetime,time
import io
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
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
