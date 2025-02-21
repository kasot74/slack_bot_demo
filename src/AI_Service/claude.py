from anthropic import Anthropic
from ..utilities import read_config 
from ..database import con_db

# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
ai_db = con_db(config)
claude = Anthropic(api_key=config['CLAUDE_API_KEY'])
collection = ai_db.ai_his
role_collection = ai_db.ai_role_claude_his


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
        model="claude-3-5-sonnet-20241022",
        max_tokens=1000,
        system="請用繁體中文回答",
        messages=conversation_history
    )
    
    assistant_message = response.content[0].text
    collection.insert_one({"role": "assistant", "content": assistant_message})
    return assistant_message

def clear_conversation_history():
    collection.delete_many({})
    collection.insert_one({"role": "system", "content": "請用繁體中文回答"})

#角色扮演用回應
def role_generate_response(role1, role2,user_input,ts):
    aimodel = "claude"
    if role_collection.find({"tsid": ts, "ai_model": aimodel}).count() == 0:
        role_collection.insert_one({"role": "system", "content": "請用繁體中文回答", "tsid": ts, "ai_model": aimodel })    
        role_collection.insert_one({"role": "system", "content": f"模擬情境{role1} 與 {role2}之間的對話，你當{role1}我當{role2}", "tsid": ts, "ai_model": aimodel })
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
    response = claude.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1000,
        system="請用繁體中文回答",
        messages=formatted_messages
    )
    assistant_message = response.content[0].text
    role_collection.insert_one({"role": "assistant", "content": assistant_message,"tsid": ts, "ai_model": aimodel })    

    return assistant_message

def analyze_sentiment(text):
    response = claude.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1000,
        system="你是一個情感分析器，判定語錄是正能量還是負能量。",
        messages=[
            {"role": "user", "content": f"這句話：'{text}' 是正能量還是負能量？"}
        ]
    )
    return response.content[0].text.strip().lower()

def painting(text):
    response = claude.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1000,
        system="你是翻譯官，幫我將文字描述翻譯為英文用來直接提供給StabilityAI繪圖用，不需要其他說明",
        messages=[
            {"role": "user", "content": f"幫我轉化：'{text}'"}
        ]
    )
    return response.content[0].text