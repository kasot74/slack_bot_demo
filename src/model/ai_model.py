import re
import random
import os
import requests
import json 
import time

from PIL import Image
from io import BytesIO
from slack_sdk import WebClient

from math import comb
from datetime import datetime, timedelta
# openai imports
from ..AI_Service.openai import generate_summary as generate_summary_openai
from ..AI_Service.openai import look_conversation_history as openai_look_conversation_history
from ..AI_Service.openai import create_image_dalle as openai_create_image_dalle
from ..AI_Service.openai import create_image_dalle_hd as openai_create_image_dalle_hd
from ..AI_Service.openai import translate_prompt_to_english as openai_translate_prompt

# claude imports
from ..AI_Service.claude import generate_summary as generate_summary_claude

from ..AI_Service.xai import clear_conversation_history as ai_clear_conversation_history
 #dzmm imports
from ..AI_Service.dzmm import generate_summary as generate_summary_dzmm
# gemini imports
from ..AI_Service.gemini import generate_summary as generate_summary_gemini
from ..AI_Service.gemini import create_image as gemini_create_image
from ..AI_Service.gemini import create_video as gemini_create_video
from ..AI_Service.gemini import create_video_from_bytes as gemini_create_video_from_bytes

from ..AI_Service.gemini import edit_image_from_bytes as gemini_edit_image
from ..AI_Service.gemini import model_list as gemini_model_list
from ..database import update_ai_model_config, list_ai_model_configs

COMMANDS_HELP = [
        ("!openai 內容", "詢問 GPT "),
        ("!claude 內容", "詢問 Claude "),    
        ("!gemini 內容", "詢問 gemini"),    
        ("!ai 內容", "AI角色扮演"),    
        ("!畫 內容", "用 Gemini Imagen 產生圖片"),
        ("!dalle 內容", "用 OpenAI GPT-image-2 產生圖片"),    
        ("!改圖 內容", "用 Gemini 進行圖片編輯"),
        ("!clearai", "清除 AI 聊天紀錄"),
        ("!setmodel <service> <field> <value>", "更新 AI 模型設定"),
        ("!listmodels", "查看目前 AI 模型設定")
    ]


def register_handlers(app, config, db):

    #!models
    @app.message(re.compile(r"^!models$"))
    def list_models(message, say):
        try:
            models = gemini_model_list()
            model_list_text = "Gemini 可用模型列表：\n" + "\n".join(models)
            say(model_list_text)
        except Exception as e:
            say(f"取得模型列表失敗：{e}")

    #!ai
    @app.message(re.compile(r"!ai\s+(.+)"))
    def handle_summary_command(message, say):
        user_input = message['text'].replace('!ai', '').strip()    
        # 調用 OpenAI API
        try:        
            summary = generate_summary_dzmm(user_input)
            say(f"{summary}", thread_ts=message['ts'])            
        except Exception as e:        
            say(f"非預期性問題 {e}")

    # Call OpenAI
    @app.message(re.compile(r"!openai\s+(.+)"))
    def handle_summary_command(message, say):
        user_input = message['text'].replace('!openai', '').strip()    
        # 調用 OpenAI API
        try:        
            summary = generate_summary_openai(user_input)
            say(f"{summary}", thread_ts=message['ts'])            
        except Exception as e:        
            say(f"非預期性問題 {e}")

    # Call Claude
    @app.message(re.compile(r"!claude\s+(.+)"))
    def handle_summary_command(message, say):
        user_input = message['text'].replace('!claude', '').strip()    
        # 調用 Claude API
        try:        
            summary = generate_summary_claude(user_input)
            say(f"{summary}", thread_ts=message['ts'])                        
        except Exception as e:        
            say(f"非預期性問題 {e}")        
                       
    # Call gemini
    @app.message(re.compile(r"!gemini\s+(.+)"))
    def handle_summary_command(message, say):
        user_input = message['text'].replace('!gemini', '').strip()    
        # 調用 gemini API
        try:        
            summary = generate_summary_gemini(user_input)
            say(f"{summary}", thread_ts=message['ts'])            
        except Exception as e:        
            say(f"非預期性問題 {e}")

    # 發送圖片函數
    def send_image(channel_id, message, say, file_path=None):        
        if not file_path:  # 检查 file_path 是否为空或 None
            say(message)
            return
        try:
            if not isinstance(file_path, str):
                say(f"{message}\n❌ 錯誤：無效的檔案路徑")
                return
                
            imagefile = os.path.join('images', file_path)
            if os.path.isfile(imagefile):                
                response = app.client.files_upload_v2(
                    channel=channel_id,
                    file=imagefile,
                    initial_comment=message
                )                
            else:
                say(f"{message} \n❌ 找不到檔案：{file_path}")                
        except Exception as e:
            say(f"{message}\n❌ 圖片上傳失敗：{e}")

    # 發送影片函數
    def send_video(channel_id, message, say, file_path=None):        
        if not file_path:  # 检查 file_path 是否为空或 None
            say(message)
            return
        try:
            videofile = os.path.join('images', file_path)
            if os.path.isfile(videofile):                
                response = app.client.files_upload_v2(
                    channel=channel_id,
                    file=videofile,
                    initial_comment=message
                )                
            else:
                say(f"{message} \n找不到影片檔案：{file_path}")                
        except Exception as e:
            print(f"Error send_video uploading file: {e}")
            say(f"影片上傳失敗：{e}")            

    #!畫
    @app.message(re.compile(r"^!畫\s+(.+)$"))
    def create_image(message, say):        
        channel = message['channel']
        msg_text = re.match(r"^!畫\s+(.+)$", message['text']).group(1).strip()
        say_text, file_name = gemini_create_image(msg_text)                        
        send_image(channel, say_text, say, file_name)

    #!clearai
    @app.message(re.compile(r"^!clearai$"))
    def clearai(message, say):
        try:            
            ai_clear_conversation_history()
            ai_clear_conversation_history("ai_dzmm_his","你是一個樂於助人的AI助理，請根據使用者的需求提供有用且準確的資訊。")            
            say("AI 聊天紀錄清除成功！")
        except Exception as e:
            say(f"AI 聊天紀錄清除錯誤！{e}")

    # !setmodel <service> <field> <value>
    @app.message(re.compile(r"^!setmodel\s+(\S+)\s+(\S+)\s+(\S+)$"))
    def handle_set_model(message, say):
        match = re.match(r"^!setmodel\s+(\S+)\s+(\S+)\s+(\S+)$", message['text'])
        service, field, value = match.group(1), match.group(2), match.group(3)
        allowed_fields = {"model", "image_model"}
        if field not in allowed_fields:
            say(f"❌ 不支援的欄位 `{field}`，可用：{', '.join(f'`{f}`' for f in allowed_fields)}")
            return
        ok = update_ai_model_config(db, service, field, value)
        if ok:
            say(f"✅ 已更新 `{service}` 的 `{field}` 為 `{value}`，下次呼叫 API 即生效。")
        else:
            say(f"❌ 找不到 service `{service}`，請先確認 service 名稱是否正確。")

    # !listmodels
    @app.message(re.compile(r"^!listmodels$"))
    def handle_list_models_config(message, say):
        try:
            configs = list_ai_model_configs(db)
            if not configs:
                say("目前沒有任何 AI 模型設定。")
                return
            lines = ["🤖 目前 AI 模型設定："]
            for cfg in configs:
                service = cfg.get("service", "?")
                model = cfg.get("model", "-")
                image_model = cfg.get("image_model", "")
                line = f"• `{service}` — model: `{model}`"
                if image_model:
                    line += f", image_model: `{image_model}`"
                lines.append(line)
            say("\n".join(lines))
        except Exception as e:
            say(f"❌ 取得模型設定失敗：{e}")

    #!dalle - GPT-image-2 圖像生成
    @app.message(re.compile(r"^!dalle\s+(.+)$"))
    def create_image_dalle(message, say):
        channel = message['channel']
        msg_text = re.match(r"^!dalle\s+(.+)$", message['text']).group(1).strip()
        
        try:
            # 回應用戶
            say("🎨 GPT-image-2 正在生成圖像，請稍候...")
            
            # 創建圖像
            say_text, file_name = openai_create_image_dalle(msg_text, quality="medium", size="1024x1024")
            
            # 發送圖像到 Slack
            send_image(channel, say_text, say, file_name)
        except Exception as e:
            say(f"❌ 圖像生成失敗：{e}")
   
    # !改圖
    @app.message(re.compile(r"^!改圖\s+(.+)$"))
    def handle_edit_image(message, say):
        channel = message['channel']

        # 提取改圖描述
        text_prompt = message['text'].replace('!改圖', '').strip()
        if not text_prompt:
            say("請提供改圖描述，例如：!改圖 在我旁邊添加一隻可愛的羊駝")
            return
        
        # 先回應用戶，告知改圖進行中
        say("🎨 開始改圖，請稍候...")
        image_bytes_list = []
        file_name = "uploaded"
        try:
            # 若有附加圖片則下載（圖片為可選）
            if 'files' in message:
                for file_info in message['files']:
                    file_url = file_info['url_private']
                    file_name = file_info['name']
                    headers = {'Authorization': f'Bearer {config["SLACK_BOT_TOKEN"]}'}
                    response = requests.get(file_url, headers=headers)
                    if response.status_code == 200:
                        image_bytes_list.append(response.content)

            # 調用 Gemini 改圖／生圖功能（圖片可選）
            result_text, file_path = gemini_edit_image(image_bytes_list, text_prompt, file_name)

            if file_path:
                send_image(channel, result_text, say, file_path)
            else:
                say(result_text)
                
        except Exception as e:
            say(f"❌ 改圖失敗：{e}")

            

