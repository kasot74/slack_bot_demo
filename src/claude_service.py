from anthropic import Anthropic
from .utilities import read_config 
from .database import con_db

# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
ai_db = con_db(config)
claude = Anthropic(api_key=config['CLAUDE_API_KEY'])
collection = ai_db.ai_his

def convert_to_claude_format(collection_name):
    c_collection = ai_db[collection_name]
    history = list(c_collection.find())
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
    conversation_history = convert_to_claude_format("ai_his")
    
    messages = []
    for msg in conversation_history:
        if msg["role"] == "user":
            messages.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            messages.append({"role": "assistant", "content": msg["content"]})
        elif msg["role"] == "system":
            messages.append({"role": "system", "content": msg["content"]})
    
    response = claude.messages.create(
        model="claude-3-5-sonnet-20241022",
        messages=messages
    )
    
    assistant_message = response.content[0].text
    collection.insert_one({"role": "assistant", "content": assistant_message})
    return assistant_message

def clear_conversation_history():
    collection.delete_many({})
    collection.insert_one({"role": "system", "content": "請用繁體中文回答"})

def look_conversation_history():
    history = list(collection.find())
    all_his = [f"{idx + 1}. {'User:' if h.get('role', '') == 'user' else 'AI:'} {h.get('content', '')}" 
               for idx, h in enumerate(history)]
    his_text = "\n".join(all_his)
    return his_text

def validate_with_claude(text):
    response = claude.messages.create(
        model="claude-3-5-sonnet-20241022",
        messages=[
            {"role": "system", "content": "你是繁體中文錯別字檢查器，只會回答正確或是修正錯別字"},
            {"role": "system", "content": "請用檢查文中是否有錯字 如果沒有請回答'正確'，有錯請回答修正錯字後的句子 "},
            {"role": "user", "content": text}
        ]
    )
    print(response.content[0].text)
    return response.content[0].text

def analyze_sentiment(text):
    response = claude.messages.create(
        model="claude-3-5-sonnet-20241022",
        messages=[
            {"role": "system", "content": "你是一個情感分析器，判定語錄是正能量還是負能量。"},
            {"role": "user", "content": f"這句話：'{text}' 是正能量還是負能量？"}
        ]
    )
    return response.content[0].text.strip().lower()

def painting(text):
    response = claude.messages.create(
        model="claude-3-5-sonnet-20241022",
        messages=[
            {"role": "system", "content": "你是翻譯官，幫我將文字描述翻譯為英文用來提供給StabilityAI繪圖用"},
            {"role": "user", "content": f"幫我轉化：'{text}' "}
        ]
    )
    return response.content[0].text.strip().lower()