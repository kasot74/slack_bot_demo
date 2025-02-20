import openai
from openai import OpenAI
from ..utilities import read_config
from ..database import con_db


# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
ai_db = con_db(config)
XAI_clice = OpenAI(    
    api_key=config['XAI_API_KEY'],
    base_url="https://api.x.ai/v1",    
)
model_target = "grok-2-latest"
collection = ai_db.ai_his


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

def look_conversation_history():
    history = list(collection.find())
    # 建立一個包含所有雞湯語錄的列表    
    all_his = [f"{idx + 1}. {'User:' if h.get('role', '') == 'user' else 'AI:'} {h.get('content', '')}" for idx, h in enumerate(history)]
    # 將列表轉換為單一字串，換行分隔
    his_text = "\n".join(all_his)
    return his_text

def validate_with_openai(text):
    # 使用 OpenAI 的 API 進行檢查
    response = XAI_clice.chat.completions.create(
        messages=[
            {"role": "system", "content": "你是繁體中文錯別字檢查器，只會回答正確或是修正錯別字"},
            {"role": "system", "content": "請用檢查文中是否有錯字 如果沒有請回答'正確'，有錯請回答修正錯字後的句子 "},
            {
                "role": "user",
                "content": text,
            }
        ],
        model=model_target,         
    )    
    print(response.choices[0].message.content)
    return response.choices[0].message.content

def analyze_sentiment(text):
    response = XAI_clice.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "你是一個情感分析器，判定語錄是正能量還是負能量。"},
            {"role": "user", "content": f"這句話：'{text}' 是正能量還是負能量？"}
        ]
    )       
    return response.choices[0].message.content.strip().lower()

def  painting(text):
    response = XAI_clice.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "你是翻譯官，幫我將文字描述翻譯為英文用來提供給StabilityAI繪圖用"},
            {"role": "user", "content": f"幫我轉化：'{text}' "}
        ]
    )       
    return response.choices[0].message.content.strip().lower()
