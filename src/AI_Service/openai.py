import openai
from openai import OpenAI
from ..utilities import read_config
from ..database import con_db, get_ai_model_config
import os
import base64
from datetime import datetime


# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
ai_db = con_db(config)
OpenAI_clice = OpenAI(    
    api_key=config['OPENAI_API_KEY']
)
_model_cfg = get_ai_model_config(ai_db, "openai")
model_target = _model_cfg.get("model", "gpt-5.4")
image_model = _model_cfg.get("image_model", "gpt-image-2")
collection = ai_db.ai_his


# 定義一個函數來轉換每條記錄為 OpenAI API 格式
def convert_to_openai_format(collection_name):
    c_collection = ai_db[collection_name]
    history = list(c_collection.find())    
    # 使用列表解析進行轉換
    formatted_messages = [
        {
            "role": str(h.get("role", "user")),
            "content": str(h.get("content", ""))
        }
        for h in history
    ]
    return formatted_messages

def generate_summary(user_input):
        
    user_message = {"role": "user", "content": user_input}
    collection.insert_one(user_message)
    conversation_history = convert_to_openai_format("ai_his")        
    response = OpenAI_clice.chat.completions.create(
        messages=conversation_history,
        model=model_target        
    )
    assistant_message = response.choices[0].message.content
    collection.insert_one({"role": "assistant", "content": assistant_message})

    return assistant_message

def clear_conversation_history():
    collection.delete_many({})
    collection.insert_one({"role": "system", "content": "用繁體中文"})    
def look_conversation_history():
    history = list(collection.find())
    # 建立一個包含所有雞湯語錄的列表    
    all_his = [f"{idx + 1}. {'User:' if h.get('role', '') == 'user' else 'AI:'} {h.get('content', '')}" for idx, h in enumerate(history)]
    # 將列表轉換為單一字串，換行分隔
    his_text = "\n".join(all_his)
    return his_text


def analyze_sentiment(text):
    response = OpenAI_clice.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "你是一個情感分析器，判定語錄是正能量還是負能量。"},
            {"role": "user", "content": f"這句話：'{text}' 是正能量還是負能量？"}
        ]
    )       
    return response.choices[0].message.content.strip().lower()

def painting(text):
    response = OpenAI_clice.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "你是翻譯官，幫我將文字描述翻譯為英文用來提供給StabilityAI繪圖用"},
            {"role": "user", "content": f"幫我轉化：'{text}' "}
        ]
    )       
    return response.choices[0].message.content.strip().lower()


def create_image_dalle(prompt, quality="medium", size="1024x1024"):
    """
    使用 OpenAI GPT-image-2 API 生成圖像
    
    Args:
        prompt (str): 圖像描述文本
        quality (str): 圖像質量 - "low", "medium", "high" 或 "auto"，預設為 "medium"
        size (str): 圖像尺寸 - "1024x1024", "1792x1024", "1024x1792"，預設為 "1024x1024"
    
    Returns:
        tuple: (狀態訊息, 圖像檔案路徑)
    """
    try:
        # 確保 images 目錄存在
        images_dir = "images"
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)
        
        # 調用最新的 GPT-image-2 API
        response = OpenAI_clice.images.generate(
            model=image_model,  # 使用最新的 gpt-image-2 模型
            prompt=prompt,
            size="1024x1024",
            quality="high",
            n=1            
        )
        
        # 取得 base64 圖像資料
        if not response or not response.data or not response.data[0]:
            raise Exception("OpenAI API 未返回有效回應")
        
        image_base64 = response.data[0].b64_json
        
        if not image_base64:
            raise Exception("未取得圖片資料")
        
        # 轉成 binary
        image_bytes = base64.b64decode(image_base64)
        
        # 檔名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"dalle_{timestamp}.png"
        file_path = os.path.join(images_dir, file_name)
        
        # 寫入圖片
        with open(file_path, "wb") as f:
            f.write(image_bytes)
        
        message = f"✅ 圖像生成成功！\nPrompt: {prompt}"
        return message, file_name
        
    except Exception as e:
        error_message = f"❌ GPT-image-2 圖像生成失敗：{str(e)}\nResponse: {response if 'response' in locals() else 'No response'}"
        return error_message, None


def create_image_dalle_hd(prompt, size="1024x1024"):
    """
    使用 OpenAI GPT-image-2 API 生成高質量圖像
    
    Args:
        prompt (str): 圖像描述文本
        size (str): 圖像尺寸 - "1024x1024", "1792x1024", "1024x1792"
    
    Returns:
        tuple: (狀態訊息, 圖像檔案路徑)
    """
    return create_image_dalle(prompt, quality="high", size=size)


def translate_prompt_to_english(text):
    """
    將中文提示詞翻譯為英文用於 DALL-E
    
    Args:
        text (str): 中文提示詞
    
    Returns:
        str: 英文翻譯
    """
    response = OpenAI_clice.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "你是翻譯官，將用戶的中文圖像描述翻譯為英文，用於圖像生成API。保持描述的藝術性和準確性。"},
            {"role": "user", "content": f"將以下描述翻譯為英文用於圖像生成：'{text}'"}
        ]
    )       
    return response.choices[0].message.content.strip()
