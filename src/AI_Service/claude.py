from anthropic import Anthropic
from ..utilities import read_config 
from ..database import con_db

# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
ai_db = con_db(config)
claude = Anthropic(api_key=config['CLAUDE_API_KEY'])
collection = ai_db.ai_his
role_collection = ai_db.ai_role_claude_his
model_target = "claude-3-7-sonnet-20250219"

def convert_to_claude_format(collection_name):
    c_collection = ai_db[collection_name]
    history = list(c_collection.find())
    formatted_messages = [
        {
            "role": "user" if h.get("role") == "user" else "assistant",
            "content": str(h.get("content", ""))
        }
        for h in history if h.get("role") != "system"
    ]
    return formatted_messages

def generate_summary(user_input):
    user_message = {"role": "user", "content": user_input}
    collection.insert_one(user_message)
    conversation_history = convert_to_claude_format("ai_his")
    
    response = claude.messages.create(
        model=model_target,
        max_tokens=1000,
        system="用繁體中文回答",
        messages=conversation_history
    )
    
    assistant_message = response.content[0].text
    collection.insert_one({"role": "assistant", "content": assistant_message})
    return assistant_message

def clear_conversation_history():
    collection.delete_many({})
    collection.insert_one({"role": "system", "content": "用繁體中文回答"})


def analyze_sentiment(text):
    response = claude.messages.create(
        model=model_target,
        max_tokens=1000,
        system="你是一個情感分析器，判定語錄是正能量還是負能量。",
        messages=[
            {"role": "user", "content": f"這句話：'{text}' 是正能量還是負能量？"}
        ]
    )
    return response.content[0].text.strip().lower()

def painting(text):
    response = claude.messages.create(
        model=model_target,
        max_tokens=1000,
        system="你是翻譯官，幫我將文字描述翻譯為英文用來直接提供給StabilityAI繪圖用，不需要其他說明",
        messages=[
            {"role": "user", "content": f"幫我轉化：'{text}'"}
        ]
    )
    return response.content[0].text