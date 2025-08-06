import requests
import json
import base64
import os
from datetime import datetime
from ..utilities import read_config
from ..database import con_db

# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
ai_db = con_db(config)
GEMINI_API_KEY = config['GEMINI_API_KEY']

# Gemini API 設定
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-2.0-flash"
IMAGE_MODEL = "gemini-2.0-flash-preview-image-generation"
collection = ai_db.ai_his

def convert_to_gemini_format(collection_name):
    """轉換資料庫格式為 Gemini API 格式"""
    c_collection = ai_db[collection_name]
    history = list(c_collection.find())
    
    contents = []
    for h in history:
        role = h.get("role", "user")
        content = h.get("content", "")
        
        if role == "system":
            # Gemini 沒有 system role，轉為 user message
            contents.append({
                "role": "user",
                "parts": [{"text": f"系統提示: {content}"}]
            })
        elif role == "user":
            contents.append({
                "role": "user", 
                "parts": [{"text": content}]
            })
        elif role == "assistant":
            contents.append({
                "role": "model",
                "parts": [{"text": content}]
            })
    
    return contents

def generate_summary(user_input):
    """生成摘要 - 參考 openai.py 的 generate_summary"""
    user_message = {"role": "user", "content": user_input}
    collection.insert_one(user_message)
    
    conversation_history = convert_to_gemini_format("ai_his")
    
    # 發送請求到 Gemini API
    url = f"{GEMINI_BASE_URL}/models/{DEFAULT_MODEL}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GEMINI_API_KEY
    }
    
    payload = {
        "contents": conversation_history,
        "generationConfig": {
            "maxOutputTokens": 1000,
            "temperature": 0.7
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        if 'candidates' in result and len(result['candidates']) > 0:
            assistant_message = result['candidates'][0]['content']['parts'][0]['text']
        else:
            assistant_message = "無法生成回應"
            
        collection.insert_one({"role": "assistant", "content": assistant_message})
        return assistant_message
        
    except Exception as e:
        return f"生成失敗: {e}"

def create_image(prompt):
    """使用 Gemini 生成圖片"""
    try:
        # 確保圖片目錄存在
        image_dir = os.path.join("images", "gemini_image")
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)
        
        # 發送請求到 Gemini 圖片生成 API
        url = f"{GEMINI_BASE_URL}/models/{IMAGE_MODEL}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GEMINI_API_KEY
        }
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt}
                ]
            }],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"]
            }
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        # 檢查回應中是否有圖片數據
        if 'candidates' in result and len(result['candidates']) > 0:
            candidate = result['candidates'][0]
            
            # 查找圖片數據
            image_data = None
            text_response = ""
            
            for part in candidate.get('content', {}).get('parts', []):
                if 'inlineData' in part:
                    image_data = part['inlineData']['data']
                elif 'text' in part:
                    text_response = part['text']
            
            if image_data:
                # 解碼並儲存圖片
                try:
                    image_bytes = base64.b64decode(image_data)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"gemini_{timestamp}.png"
                    filepath = os.path.join(image_dir, filename)
                    
                    with open(filepath, 'wb') as f:
                        f.write(image_bytes)
                    
                    relative_path = os.path.join("gemini_image", filename)
                    return f"✅ Gemini 圖片生成成功！\n{text_response if text_response else prompt}", relative_path
                    
                except Exception as decode_error:
                    return f"❌ 圖片解碼失敗: {decode_error}", None
            else:
                return f"❌ 回應中沒有圖片數據\n回應內容: {text_response}", None
        else:
            return "❌ Gemini 圖片生成失敗：無有效回應", None
            
    except requests.exceptions.RequestException as e:
        return f"❌ Gemini 圖片生成請求失敗: {e}", None
    except Exception as e:
        return f"❌ Gemini 圖片生成錯誤: {e}", None


