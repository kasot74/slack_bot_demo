import requests
import json
import re
import base64
import os
import time
import filetype
from PIL import Image
from io import BytesIO
from datetime import datetime
from google import genai
from google.genai import types
from ..utilities import read_config
from ..database import con_db
from ..AI_Service.openai import painting
from ..AI_Service.ai_tool import read_url_content
from ..stock import get_stock_info, get_historical_data, get_crypto_prices, get_current_date

# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
ai_db = con_db(config)
GEMINI_API_KEY = config['GEMINI_API_KEY']

# Gemini API 設定
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-2.5-flash"
IMAGE_MODEL = "gemini-2.5-flash-image"
collection = ai_db.ai_his


# 定義可供 Gemini 使用的工具 (不含內建搜尋，稍後動態加入)
TOOLS = [
    #get_stock_info, 
    #get_historical_data, 
    #get_crypto_prices, 
    #get_current_date,
    #read_url_content
]

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
    """生成摘要 - 支援 Function Calling"""
    user_message = {"role": "user", "content": user_input}
    collection.insert_one(user_message)
    
    conversation_history = convert_to_gemini_format("ai_his")
    
    # 初始化 Gemini 客戶端
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # 準備完整的工具清單 (包含自定義函數與 Google 搜尋)
    # 根據官方文件，Google 搜尋可透過 types.Tool 定義
    all_tools = list(TOOLS)
    all_tools.append(types.Tool(google_search=types.GoogleSearch()))
    #all_tools.append(types.Tool(google_search_retrieval=types.GoogleSearchRetrieval()))
    try:
        # 在系統提示中引導 AI 只有在「不知道」或「需要即時資料」時才搜尋        

        # 使用 SDK 的 Chat Session 支援自動 Function Calling
        # 排除掉剛才加入的最新訊息，透過 send_message 發送
        chat = client.chats.create(
            model=DEFAULT_MODEL,
            history=conversation_history[:-1],
            config=types.GenerateContentConfig(                
                tools=all_tools,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False),
                temperature=0.7
            )
        )

        # 發送最新訊息
        response = chat.send_message(user_input)

        # 提取所有被呼叫的工具名稱
        called_tools = []
        
        # 1. 偵測 Function Calling (如股價、自定義工具)
        if response.function_calls:
            for fn in response.function_calls:
                called_tools.append(fn.name)
        
        # 2. 偵測 Google 搜尋驗證 (Grounding)
        # 搜尋不會顯示在 function_calls 中，必須檢查 grounding_metadata
        try:
            # 檢查是否有搜尋查詢詞，若有則代表觸發了 Google 搜尋
            if response.candidates and response.candidates[0].grounding_metadata:
                metadata = response.candidates[0].grounding_metadata
                if hasattr(metadata, 'search_entry_point') or (hasattr(metadata, 'web_search_queries') and metadata.web_search_queries):
                    called_tools.append("google_search")
        except:
            pass

        if response.text:
            assistant_message = response.text
            
            # 3. 如果有呼叫工具，在回覆的最後面加上提示
            if called_tools:
                # 移除重複的工具名稱並美化顯示
                unique_tools = list(dict.fromkeys(called_tools))
                tools_display = "、".join([f"`{t}`" for t in unique_tools])
                assistant_message += f"\n\n```diff\n+ 💡 使用工具：{tools_display}\n```"
        else:
            assistant_message = "無法生成回應"
            
        collection.insert_one({"role": "assistant", "content": assistant_message})
        return assistant_message
        
    except Exception as e:
        return f"生成失敗: {e}"

def painting(text):
    """使用 Gemini 將中文描述轉換為英文圖片提示詞"""
    try:
        # 初始化 Gemini 客戶端
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # 使用 SDK 發送請求
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents=f"你是翻譯官，幫我將文字描述翻譯為英文用來提供給 AI 生成用。請將以下中文描述轉換為英文提示詞給我不需要太多其他建議：'{text}'",
            config=types.GenerateContentConfig(
                max_output_tokens=300,
                temperature=0.3  # 較低的溫度確保翻譯準確性
            )
        )
        
        if response.text:
            return response.text.strip()
        else:
            return text  # 如果翻譯失敗，返回原文
            
    except Exception as e:
        print(f"Gemini 翻譯失敗: {e}")
        return text  # 翻譯失敗時返回原文

def model_list():
    """列出可用的 Gemini 模型"""
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        models = []
        for model in client.models.list():
            models.append(str(model))            
        return models  # 回傳模型列表
    except Exception as e:
        print(f"Gemini 模型列表獲取失敗: {e}")
        return []  # 發生錯誤時回傳空列表

def analyze_stock(his_data, now_data):
    """使用 Gemini 分析股票趨勢"""
    try:
        collection_stock = ai_db.ai_analyze_stock_his
        # 初始化 Gemini 客戶端
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # 構建提示詞
        system_prompt = "你是一個股票的專業技術分析專家，給你股票歷史紀錄與現況幫我分析趨勢\n\n"
        historical_data = "歷史記錄：\n" + "\n".join([str(record) for record in his_data])
        current_data = f"\n現況：\n{now_data}"
        
        full_prompt = system_prompt + historical_data + current_data
        user_message = {"role": "user", "content": full_prompt}
        collection_stock.insert_one(user_message)
        
        conversation_history = convert_to_gemini_format("ai_analyze_stock_his")
        
        try:
            # 使用 SDK 發送請求
            response = client.models.generate_content(
                model=DEFAULT_MODEL,
                contents=conversation_history,
                config=types.GenerateContentConfig(
                    temperature=0.7
                )
            )
            
            if response.text:
                assistant_message = response.text
            else:
                assistant_message = "無法生成回應"                            
            return assistant_message
            
        except Exception as e:
            return f"生成失敗: {e}"
            
    except Exception as e:
        print(f"Gemini 股票分析錯誤: {e}")
        return f"分析過程發生錯誤: {e}"

def create_image(prompt):
    """使用 Imagen 4.0 生成圖片"""
    try:
        # 確保圖片目錄存在
        image_dir = os.path.join("images", "gemini_image")
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)
        
        #prompt = painting(prompt)  # 確保 prompt 是經過處理的
        
        # 使用 SDK 發送請求到 Imagen API
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,  # 生成1張圖片，可調整為1-4
            )
        )
        
        # 檢查回應中是否有圖片數據
        if response.generated_images:
            generated_image = response.generated_images[0]
            
            # 儲存圖片
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"imagen_{timestamp}.png"
            filepath = os.path.join(image_dir, filename)
            # 直接使用 Image 物件的 save 方法
            generated_image.image.save(filepath)
            
            # 方法2: 手動存取 image_bytes（替代方案）
            # if generated_image.image.image_bytes:
            #     with open(filepath, 'wb') as f:
            #         f.write(generated_image.image.image_bytes)
            
            relative_path = os.path.join("gemini_image", filename)
            return f"✅ Imagen 圖片生成成功！\n提示詞: {prompt}", relative_path
        else:
            return f"❌ Imagen 圖片生成失敗：無有效回應", None
        
    except Exception as e:
        return f"❌ Imagen 圖片生成錯誤: {e}", None

def create_video(prompt, negative_prompt="", max_wait_time=300, image_bytes=None):
    """使用 Google Genai 客戶端生成影片，支援圖片輸入"""
    try:
        # 確保影片目錄存在
        video_dir = os.path.join("images", "gemini_video")
        if not os.path.exists(video_dir):
            os.makedirs(video_dir)
        
        # 使用 painting 函數處理提示詞
        processed_prompt = painting(prompt)
        
        # 初始化 Google Genai 客戶端
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # 處理圖片輸入 - 只處理 image_bytes
        image = None
        temp_image_path = None
        if image_bytes:            
            try:
                # 判斷 MIME 類型和副檔名
                kind = filetype.guess(image_bytes)
                if not kind:
                    print("❌ 無法判斷圖片格式，使用預設 .jpg")
                    file_extension = ".jpg"
                else:
                    file_extension = f".{kind.extension}"
                    print(f"🎨 檢測到圖片格式: {kind.mime}, 副檔名: {file_extension}")
                
                # 創建臨時檔案路徑
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                temp_filename = f"temp_image_{timestamp}{file_extension}"
                temp_image_path = os.path.join(video_dir, temp_filename)
                
                # 儲存圖片到本機
                print(f"💾 儲存圖片到: {temp_image_path}")
                with open(temp_image_path, 'wb') as f:
                    f.write(image_bytes)
                
                # 使用 types.Image.from_file 載入圖片
                print(f"🔄 使用 types.Image.from_file 載入圖片...")
                image = types.Image.from_file(location=temp_image_path)
                print(f"✅ 圖片載入成功，類型: {type(image)}")
                
            except Exception as img_error:
                print(f"❌ 圖片處理失敗: {img_error}")
                # 清理臨時檔案
                if temp_image_path and os.path.exists(temp_image_path):
                    os.remove(temp_image_path)
                return f"❌ 圖片處理失敗: {img_error}", None
        
        # 配置影片生成參數
        config = types.GenerateVideosConfig()
        if negative_prompt:
            config.negative_prompt = negative_prompt
        
        print(f"🎬 開始影片生成...")
        
        # 統一使用 generate_videos 方法
        if image:
            # 有圖片輸入時，使用 image 參數
            operation = client.models.generate_videos(
                model="veo-3.0-generate-preview",
                prompt=processed_prompt,
                image=image,
                config=config,
            )
            print(f"🎬 圖片轉影片生成已啟動，操作 ID: {operation.name}")
        else:
            # 純文字影片生成
            operation = client.models.generate_videos(
                model="veo-3.0-generate-preview",
                prompt=processed_prompt,
                config=config,
            )
            print(f"🎬 文字轉影片生成已啟動，操作 ID: {operation.name}")
        
        # 等待影片生成完成
        start_time = time.time()
        while not operation.done and (time.time() - start_time) < max_wait_time:
            elapsed_time = int(time.time() - start_time)
            print(f"⏳ 影片生成中... ({elapsed_time}秒)")
            time.sleep(20)
            operation = client.operations.get(operation)
        
        if not operation.done:
            return f"⏰ 影片生成超時 ({max_wait_time}秒)，請稍後再試", None
        
        # 處理生成結果
        if hasattr(operation, 'response') and operation.response and operation.response.generated_videos:
            generated_video = operation.response.generated_videos[0]
            
            # 下載影片檔案
            video_file = client.files.download(file=generated_video.video)
            
            # 儲存影片
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_type = "img2vid" if image else "txt2vid"
            filename = f"veo3_{video_type}_{timestamp}.mp4"
            filepath = os.path.join(video_dir, filename)
            
            # 儲存影片檔案
            with open(filepath, 'wb') as f:
                f.write(video_file)
            
            relative_path = os.path.join("gemini_video", filename)
            
            result_text = f"✅ Veo 3.0 影片生成成功！\n"
            result_text += f"類型: {'圖片轉影片' if image else '純文字轉影片'}\n"
            result_text += f"提示詞: {processed_prompt}\n"
            if negative_prompt:
                result_text += f"負面提示: {negative_prompt}\n"
            
            return result_text, relative_path
        
        # 也檢查 operation.result (向後相容)
        elif hasattr(operation, 'result') and operation.result and operation.result.generated_videos:
            generated_video = operation.result.generated_videos[0]
            
            # 下載影片檔案
            video_file = client.files.download(file=generated_video.video)
            
            # 儲存影片
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_type = "img2vid" if image else "txt2vid"
            filename = f"veo3_{video_type}_{timestamp}.mp4"
            filepath = os.path.join(video_dir, filename)
            
            # 儲存影片檔案
            with open(filepath, 'wb') as f:
                f.write(video_file)
            
            relative_path = os.path.join("gemini_video", filename)
            
            result_text = f"✅ Veo 3.0 影片生成成功！\n"
            result_text += f"類型: {'圖片轉影片' if image else '純文字轉影片'}\n"
            result_text += f"提示詞: {processed_prompt}\n"
            if negative_prompt:
                result_text += f"負面提示: {negative_prompt}\n"
            
            return result_text, relative_path
        else:
            error_msg = getattr(operation, 'error', '未知錯誤')
            return f"❌ 影片生成失敗：{error_msg}", None
            
    except Exception as e:
        return f"❌ Veo 影片生成錯誤: {e}", None

def create_video_from_bytes(image_bytes, prompt, negative_prompt="", max_wait_time=300):
    """從圖片位元組生成影片的便利函數"""
    return create_video(prompt, negative_prompt, max_wait_time, image_bytes=image_bytes)

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

def edit_image_from_bytes(image_bytes_list, text_prompt, original_filename="uploaded"):
    """從位元組數據改圖"""
    try:
        # 確保圖片目錄存在
        image_dir = os.path.join("images", "gemini_image")
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)        
        
        # 初始化 Google Genai 客戶端
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # 處理提示詞
        #processed_prompt = painting(text_prompt)
        contents = []
        for image_bytes in image_bytes_list: 
            kind = filetype.guess(image_bytes) 
            if kind is None:                 
                continue 
            mime_type = kind.mime
            if not mime_type.startswith("image/"):                 
                continue 
            contents.append({ "inline_data": { "mime_type": mime_type, "data": image_bytes } })

        # 生成內容
        contents.append(text_prompt)
        response = client.models.generate_content(
            model=IMAGE_MODEL,            
            contents=contents
        )
        
        # 處理回應
        generated_text = ""
        generated_image = None
        
        for part in response.candidates[0].content.parts:
            if part.text is not None:
                generated_text += part.text
            elif part.inline_data is not None:
                generated_image = Image.open(BytesIO(part.inline_data.data))
        
        if generated_image:
            # 儲存生成的圖片
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gemini_edit_{timestamp}.png"
            filepath = os.path.join(image_dir, filename)
            
            generated_image.save(filepath)
            
            relative_path = os.path.join("gemini_image", filename)
            
            result_text = f"✅ Gemini 改圖成功！\n"
            result_text += f"原始檔案: {original_filename}\n"
            result_text += f"提示: {text_prompt}\n"            
            if generated_text:
                result_text += f"AI 回應: {generated_text}\n"
            
            return result_text, relative_path
        else:
            return f"❌ 改圖失敗：未生成圖片\nAI 回應: {generated_text}", None
            
    except Exception as e:
        return f"❌ Gemini 改圖錯誤: {e}", None