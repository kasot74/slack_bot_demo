import os
import time
from PIL import Image
import io
from stability_sdk import client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
from .utilities import read_config
# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
api_key=config['STABILITY_API_KEY']
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
        answers = stability_api.generate(prompt=text)
        for resp in answers:
            for artifact in resp.artifacts:
                if artifact.finish_reason == generation.FILTER:
                    print("Your request activated the API's safety filters and could not be processed."
                        "Please modify the prompt and try again.")                        
                if artifact.type == generation.ARTIFACT_IMAGE:
                    img = Image.open(io.BytesIO(artifact.binary))
                    image_dir = os.path.join(image_dir,str(artifact.seed)+ ".png")
                    img.save(image_dir,"png") # Save our generated images with their seed number as the filename.                    
                    timestamp = int(time.time())
                    file_path = os.path.join("stability_image", str(timestamp)+ ".png")
        return "小畫家繪圖成功! :art: ", file_path
    except Exception as e:
        # Handle potential errors during image generation                
        return f"出錯了畫不出來! {e}", None
