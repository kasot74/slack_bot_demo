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
                if artifact.finish_reason == generation.FILTER:
                    print("Your request activated the API's safety filters and could not be processed."
                        "Please modify the prompt and try again.")                        
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
        return "小畫家繪圖成功! :art: ", file_path
    except Exception as e:
        # Handle potential errors during image generation                
        return f"出錯了畫不出來! {e}", None
