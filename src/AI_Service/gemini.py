import requests
import json
import base64
import os
import time
from datetime import datetime
from ..utilities import read_config
from ..database import con_db
from ..AI_Service.openai import painting
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

def painting(text):
    """使用 Gemini 將中文描述轉換為英文圖片提示詞"""
    try:
        url = f"{GEMINI_BASE_URL}/models/{DEFAULT_MODEL}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GEMINI_API_KEY
        }
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"你是翻譯官，幫我將文字描述翻譯為英文用來提供給 AI 繪圖用。請將以下中文描述轉換為英文提示詞給我不需要太多其他建議：'{text}'"
                        }
                    ]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": 300,
                "temperature": 0.3  # 較低的溫度確保翻譯準確性
            }
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        if 'candidates' in result and len(result['candidates']) > 0:
            translated_text = result['candidates'][0]['content']['parts'][0]['text']
            return translated_text.strip()
        else:
            return text  # 如果翻譯失敗，返回原文
            
    except Exception as e:
        print(f"Gemini 翻譯失敗: {e}")
        return text  # 翻譯失敗時返回原文

def create_image(prompt):
    """使用 Imagen 4.0 生成圖片"""
    try:
        # 確保圖片目錄存在
        image_dir = os.path.join("images", "gemini_image")
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)
        prompt = painting(prompt)  # 確保 prompt 是經過處理的
        # 發送請求到 Imagen API
        url = f"{GEMINI_BASE_URL}/models/imagen-4.0-generate-preview-06-06:predict"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY
        }
        
        payload = {
            "instances": [
                {
                    "prompt": prompt
                }
            ],
            "parameters": {
                "sampleCount": 1,  # 生成1張圖片，可調整為1-4
                "personGeneration": "allow_all"  #"dont_allow", "allow_adult", "allow_all"
            }
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        # 檢查回應中是否有圖片數據
        if 'predictions' in result and len(result['predictions']) > 0:
            prediction = result['predictions'][0]
            
            # 查找圖片數據 - Imagen API 回傳格式
            if 'bytesBase64Encoded' in prediction:
                image_data = prediction['bytesBase64Encoded']
                
                # 解碼並儲存圖片
                try:
                    image_bytes = base64.b64decode(image_data)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"imagen_{timestamp}.png"
                    filepath = os.path.join(image_dir, filename)
                    
                    with open(filepath, 'wb') as f:
                        f.write(image_bytes)
                    
                    relative_path = os.path.join("gemini_image", filename)
                    return f"✅ Imagen 圖片生成成功！\n提示詞: {prompt}", relative_path
                    
                except Exception as decode_error:
                    return f"❌ 圖片解碼失敗: {decode_error}", None
            else:
                # 檢查其他可能的圖片數據欄位
                available_keys = list(prediction.keys())
                return f"❌ 找不到圖片數據\n可用欄位: {available_keys}\n回應內容: {prediction}", None
        else:
            return f"❌ Imagen 圖片生成失敗：無有效回應\n完整回應: {result}", None
            
    except requests.exceptions.RequestException as e:
        return f"❌ Imagen 圖片生成請求失敗: {e}", None
    except Exception as e:
        return f"❌ Imagen 圖片生成錯誤: {e}", None

def create_video(prompt, negative_prompt="", max_wait_time=300):
    """使用 Veo 3.0 生成影片"""
    try:
        # 確保影片目錄存在
        video_dir = os.path.join("images", "gemini_video")
        if not os.path.exists(video_dir):
            os.makedirs(video_dir)
        
        # 使用 painting 函數處理提示詞
        processed_prompt = painting(prompt)
        
        # 啟動影片生成
        url = f"{GEMINI_BASE_URL}/models/veo-3.0-generate-preview:generateVideos"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY
        }
        
        payload = {
            "prompt": processed_prompt,
            "config": {
                "negative_prompt": negative_prompt if negative_prompt else ""
            }
        }
        
        # 啟動生成任務
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        if 'name' not in result:
            return f"❌ 影片生成啟動失敗：{result}", None
        
        operation_name = result['name']
        print(f"🎬 影片生成已啟動，操作 ID: {operation_name}")
        
        # 輪詢等待生成完成
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            # 檢查操作狀態
            status_url = f"{GEMINI_BASE_URL}/operations/{operation_name}"
            status_response = requests.get(status_url, headers=headers)
            
            if status_response.status_code == 200:
                status_result = status_response.json()
                
                # 檢查是否完成
                if status_result.get('done', False):
                    if 'result' in status_result and 'generated_videos' in status_result['result']:
                        # 獲取生成的影片
                        generated_videos = status_result['result']['generated_videos']
                        if len(generated_videos) > 0:
                            video_info = generated_videos[0]
                            video_file_name = video_info.get('video', {}).get('name', '')
                            
                            if video_file_name:
                                # 下載影片
                                return download_video_file(video_file_name, video_dir, processed_prompt)
                            else:
                                return f"❌ 無法獲取影片檔案資訊：{video_info}", None
                        else:
                            return "❌ 沒有生成任何影片", None
                    else:
                        error_msg = status_result.get('error', '未知錯誤')
                        return f"❌ 影片生成失敗：{error_msg}", None
                else:
                    # 還在生成中，等待
                    print(f"⏳ 影片生成中... ({int(time.time() - start_time)}秒)")
                    time.sleep(20)
            else:
                print(f"⚠️ 狀態檢查失敗: {status_response.status_code}")
                time.sleep(20)
        
        return f"⏰ 影片生成超時 ({max_wait_time}秒)，請稍後再試", None
        
    except requests.exceptions.RequestException as e:
        return f"❌ Veo 影片生成請求失敗: {e}", None
    except Exception as e:
        return f"❌ Veo 影片生成錯誤: {e}", None

def download_video_file(file_name, video_dir, prompt):
    """下載生成的影片檔案"""
    try:
        # 下載影片
        download_url = f"{GEMINI_BASE_URL}/files/{file_name}"
        headers = {
            "x-goog-api-key": GEMINI_API_KEY
        }
        
        download_response = requests.get(download_url, headers=headers)
        download_response.raise_for_status()
        
        # 儲存影片
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"veo3_{timestamp}.mp4"
        filepath = os.path.join(video_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(download_response.content)
        
        relative_path = os.path.join("gemini_video", filename)
        return f"✅ Veo 3.0 影片生成成功！\n提示詞: {prompt}", relative_path
        
    except Exception as e:
        return f"❌ 影片下載失敗: {e}", None

