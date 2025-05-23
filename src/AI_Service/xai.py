import openai
import base64
import os
import requests
from datetime import datetime
from PIL import Image
from io import BytesIO
from openai import OpenAI
from ..utilities import read_config
from ..database import con_db
from ..stock import get_stock_info
from ..stock import get_historical_data

# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
ai_db = con_db(config)
XAI_clice = OpenAI(    
    api_key=config['XAI_API_KEY'],
    base_url="https://api.x.ai/v1",    
)
model_target = "grok-3-beta" #grok-2-latest
collection = ai_db.ai_his
role_collection = ai_db.ai_role_xai_his

# 定義一個函數來轉換每條記錄為 
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
    response = XAI_clice.chat.completions.create(
        messages=conversation_history,
        model=model_target        
    )
    assistant_message = response.choices[0].message.content
    collection.insert_one({"role": "assistant", "content": assistant_message})

    return assistant_message

def clear_conversation_history():
    collection.delete_many({})
    collection.insert_one({"role": "system", "content": "請用繁體中文回答"})    
                 
#角色扮演用回應
def role_generate_response(role1, role2,user_input,ts):
    aimodel = "XAI"
    if role_collection.count_documents({"tsid": ts, "ai_model": aimodel}) == 0:        
        role_collection.insert_one({"role": "system", "content": f"用繁體中文回覆，你當{role1}我是{role2}", "tsid": ts, "ai_model": aimodel })
        role_collection.insert_one({"role": "user", "content": user_input, "tsid": ts, "ai_model": aimodel })
    else:
        user_message = {"role": "user", "content": user_input, "tsid": ts, "ai_model": aimodel }
        role_collection.insert_one(user_message)
        
    history = list(role_collection.find({"tsid": ts, "ai_model": aimodel }))    
    # 使用列表解析進行轉換
    formatted_messages = [
        {
            "role": str(h.get("role", "user")),
            "content": str(h.get("content", ""))
        }
        for h in history
    ]            
    response = XAI_clice.chat.completions.create(
        messages=formatted_messages,
        model=model_target        
    )
    assistant_message = response.choices[0].message.content
    role_collection.insert_one({"role": "assistant", "content": assistant_message,"tsid": ts, "ai_model": aimodel })

    return assistant_message

def create_image(prompt):
    try:
        # 呼叫 XAI API 生成圖片
        response = XAI_clice.images.generate(
            model="grok-2-image",
            prompt=prompt,
            response_format="b64_json"
        )

        # 獲取 base64 圖片數據
        b64_data = response.data[0].b64_json

        # 將 base64 解碼為二進位數據
        image_data = base64.b64decode(b64_data)

        # 確保目錄存在
        output_dir = os.path.join("images", "xai_generated")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 檢測圖片格式
        img = Image.open(BytesIO(image_data))
        img_format = img.format.lower()  # 獲取圖片格式 (如 'png', 'jpeg')        

        # 生成檔案名稱
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        img_filename = f"{timestamp}.{img_format}"
        img_path = os.path.join(output_dir, img_filename)

        # 將圖片數據寫入檔案
        with open(img_path, "wb") as img_file:
            img_file.write(image_data)
        
        return f"圖片已成功儲存", os.path.join("xai_generated",img_filename)
    except Exception as e:        
        return f"生成圖片失敗: {e}", None

def analyze_sentiment(text):
    response = XAI_clice.chat.completions.create(
        model=model_target,
        messages=[
            {"role": "system", "content": "你是一個情感分析器，判定語錄是正能量還是負能量。"},
            {"role": "user", "content": f"這句話：'{text}' 是正能量還是負能量？"}
        ]
    )       
    return response.choices[0].message.content.strip().lower()

def analyze_stock(his_data, now_data):
    historical_data_strs = [f"這是股票的歷史紀錄：\n{record}" for record in his_data]
    messages = [{"role": "system", "content": "你是一個股票的專業技術分析專家，給你股票歷史紀錄與現況幫我分析趨勢"}]
    for record_str in historical_data_strs:
        messages.append({"role": "user", "content": record_str})

    messages.append({"role": "user", "content": f"這是該股現況 {now_data}"})
    response = XAI_clice.chat.completions.create(
        model=model_target,
        messages=messages
    )       
    return response.choices[0].message.content.strip().lower()    

def analyze_stock_inoutpoint(his_data, now_data):
    historical_data_strs = [f"這是股票的歷史紀錄：\n{record}" for record in his_data]
    messages = [{"role": "system", "content": "你是一個股票的專業技術分析專家，給你股票歷史紀錄，提供我長中短期交易買點建議"}]
    for record_str in historical_data_strs:
        messages.append({"role": "user", "content": record_str})

    messages.append({"role": "user", "content": f"這是該股現況 {now_data}"})
    response = XAI_clice.chat.completions.create(
        model=model_target,
        messages=messages
    )       
    return response.choices[0].message.content.strip().lower()    

def  painting(text):
    response = XAI_clice.chat.completions.create(
        model=model_target,
        messages=[
            {"role": "system", "content": "你是翻譯官，幫我將文字描述翻譯為英文用來提供給StabilityAI繪圖用"},
            {"role": "user", "content": f"幫我轉化：'{text}' "}
        ]
    )       
    return response.choices[0].message.content.strip().lower()

def create_greet(member,types):
    # 呼叫 XAI API 生成問候
    response = XAI_clice.chat.completions.create(
        model=model_target,
        messages=[
            {"role": "system", "content": f"你是一個有趣的上下線通知生成器，給你成員名稱，幫我生成一句{types}通知"},
            {"role": "user", "content": f"成員名稱：'{member}' "}
        ]
    )       
    return response.choices[0].message.content.strip().lower()


def generate_search_summary(user_input, search_type):
    # 僅允許 "web"、"x"、"news"
    if search_type not in ["web", "x", "news"]:
        return "無效的搜尋類型 可選類型: web、x、news"

    # 儲存用戶查詢到資料庫
    user_message = {"role": "user", "content": user_input}
    collection.insert_one(user_message)

    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['XAI_API_KEY']}"
    }
    payload = {
        "messages": [
            {
                "role": "user",
                "content": user_input
            }
        ],
        "search_parameters": {
            "mode": "on",            
            "return_citations": True,
            "search_type": search_type
        },
        "model": "grok-3-latest"
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        assistant_message = data["choices"][0]["message"]["content"]
        # 儲存 AI 回覆到資料庫
        collection.insert_one({"role": "assistant", "content": assistant_message})
        return assistant_message        
    except Exception as e:
        return f"查詢失敗: {e}"