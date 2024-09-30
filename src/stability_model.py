import os
import time
from PIL import Image
import io
from stability_sdk import client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
from .openai_service import painting
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
stability_api = client.StabilityInference(key=api_key,engine="stable-diffusion-512-v2-1")
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
        answers = stability_api.generate(prompt=prompt_str, guidance_strength=0.8, steps=25,cfg_scale=7.5,sampler="K_dpm_2_ancestral", style_preset="fantasy-art")
        for resp in answers:
            for artifact in resp.artifacts:
                if artifact.finish_reason == generation.FILTER:
                    return f"繪圖失敗! {artifact.description}", None
                if artifact.type == generation.ARTIFACT_IMAGE:
                    timestamp = int(time.time())
                    img_filename = str(timestamp)+ ".png"
                    img = Image.open(io.BytesIO(artifact.binary))
                    image_dir = os.path.join(image_dir,img_filename)
                    img.save(image_dir,"png") # Save our generated images with their seed number as the filename.                    
                    
                    # 打開源文件並將其內容寫入新路徑的文件
                    new_dir = os.path.join("/home/ubuntu/web/uploads/stability_image",img_filename)
                    with open(image_dir, 'rb') as src_file:
                        with open(new_dir, 'wb') as dest_file:
                            dest_file.write(src_file.read())

                    #回傳路徑
                    file_path = os.path.join("stability_image",img_filename)
        return "繪圖成功! :art: ", file_path
    except Exception as e:
        # Handle potential errors during image generation                
        return f"BUG {e}", None
