import openai
import base64
import os
import requests
import json
from datetime import datetime
from PIL import Image
from io import BytesIO
from openai import OpenAI
from ..utilities import read_config
from ..database import con_db
from opencc import OpenCC

cc = OpenCC('s2t')  # 簡體轉繁體


# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
ai_db = con_db(config)
model_target = "nalang-xl-10"
api_key = config['DZMM_API_KEY']
api_url = config['DZMM_API_URL']

def generate_summary(user_input, collection_name="ai_dzmm_his"):
    collection_his = ai_db[collection_name]

    # 儲存使用者訊息
    user_message = {"role": "user", "content": user_input}
    collection_his.insert_one(user_message)

    # 建立初始 system prompt
    system_prompt = {"role": "system", "content": "請扮演一個有耐心的感情教練 好好教導我學習如何的當個好男友，對方可能就是臭直男經驗不足小問題都要好好指出，會指點出問題並給予建議，請用繁體中文回答"}

    # 取得歷史訊息（不含 _id）
    history_messages = list(collection_his.find({}, {"_id": 0}))

    # 合併成完整對話歷程
    conversation_history = [system_prompt] + history_messages

    # 建立請求 payload
    payload = {
        "model": model_target,
        "messages": conversation_history,
        "stream": True,
        "temperature": 0.7,
        "max_tokens": 800,
        "top_p": 0.35,
        "repetition_penalty": 1.05
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # 發送 POST 請求並處理串流回應
    response = requests.post(
        api_url,
        headers=headers,
        data=json.dumps(payload),
        stream=True
    )

    if response.status_code != 200:
        raise Exception(f"HTTP error! status: {response.status_code}")

    full_reply = ""
    for line in response.iter_lines():
        line = line.decode("utf-8").strip()    
        if line and line.startswith("data: "):
            try:
                json_data = json.loads(line[6:].strip())
                delta = json_data.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content")
                if content:
                    print(content, end='', flush=True)
                    full_reply += content
            except Exception as e:
                print("Error parsing JSON:", e)
    full_reply = cc.convert(full_reply)
    # 儲存 AI 回應
    assistant_message = {"role": "assistant", "content": full_reply}
    collection_his.insert_one(assistant_message)

    return full_reply

