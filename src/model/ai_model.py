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

# claude imports
from ..AI_Service.claude import generate_summary as generate_summary_claude
from ..AI_Service.claude import role_generate_response as role_generate_summary_claude

# xai imports
from ..AI_Service.xai import generate_summary as generate_summary_xai
from ..AI_Service.xai import analyze_sentiment as analyze_sentiment_xai 
from ..AI_Service.xai import role_generate_response as role_generate_summary_xai
from ..AI_Service.xai import analyze_stock as analyze_stock_xai
from ..AI_Service.xai import analyze_stock_inoutpoint as analyze_stock_inoutpoint_xai
from ..AI_Service.xai import create_image as xai_create_image
from ..AI_Service.xai import create_greet as xai_create_greet
from ..AI_Service.xai import generate_search_summary as generate_search_summary
from ..AI_Service.xai import clear_conversation_history as ai_clear_conversation_history

# gemini imports
from ..AI_Service.gemini import generate_summary as generate_summary_gemini
from ..AI_Service.gemini import create_image as gemini_create_image
from ..AI_Service.gemini import create_video as gemini_create_video


COMMANDS_HELP = [
    ("!openai 內容", "詢問 GPT "),
    ("!claude 內容", "詢問 Claude "),
    ("!xai 內容", "詢問 grok4"),
    ("!X 內容", "詢問 grok4(不受約束版本)"),
    ("!gemini 內容", "詢問 gemini"),
    ("!xai查 [web|x|news] 查詢內容", "AI 搜尋摘要"),
    ("!畫 內容", "用 Gemini Imagen 產生圖片"),
    ("!影片 內容", "用 Gemini Veo 3.0 生成影片"),                
    ("!clearai", "清除 AI 聊天紀錄")
    
]
  


def register_handlers(app, config, db):
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

    # Call XAI
    @app.message(re.compile(r"!xai\s+(.+)"))
    def handle_summary_command(message, say):
        user_input = message['text'].replace('!xai', '').strip()    
        # 調用 xai API
        try:        
            summary = generate_summary_xai(user_input)
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

    # Call XAI
    @app.message(re.compile(r"!X\s+(.+)"))
    def handle_summary_command(message, say):
        user_input = message['text'].replace('!X', '').strip()    
        # 調用 xai API
        try:        
            summary = generate_summary_xai(user_input,"X_his")
            say(f"{summary}", thread_ts=message['ts'])            
        except Exception as e:        
            say(f"非預期性問題 {e}")        

    # Call XAI查
    @app.message(re.compile(r"!xai查\s+(\w+)\s+(.+)"))
    def handle_search_summary_command(message, say):
        try:
            match = re.match(r"!xai查\s+(\w+)\s+(.+)", message['text'])
            if not match:
                say("請輸入正確格式：!xai查 [web|x|news] 查詢內容")
                return
            search_type = match.group(1).strip()
            user_input = match.group(2).strip()
            summary = generate_search_summary(user_input, search_type)
            say(f"{summary}", thread_ts=message['ts'])
        except Exception as e:
            say(f"非預期性問題 {e}")

    # 發送圖片函數
    def send_image(channel_id, message, say, file_path=None):        
        if not file_path:  # 检查 file_path 是否为空或 None
            say(message)
            return
        try:
            imagefile = os.path.join('images',file_path)
            if os.path.isfile(imagefile):                
                response = app.client.files_upload_v2(
                    channel=channel_id,
                    file=os.path.join('images',file_path),
                    initial_comment=message
                )                
            else:
                say(f"{message} \n找不到{file_path}" )                
        except Exception as e:
            print(f"Error send_image uploading file ")

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

    #!影片
    @app.message(re.compile(r"^!影片\s+(.+)$"))
    def create_video_handler(message, say):        
        channel = message['channel']
        msg_text = re.match(r"^!影片\s+(.+)$", message['text']).group(1).strip()
        
        # 先回應用戶，告知影片生成中
        say("🎬 開始生成影片，這可能需要幾分鐘時間，請稍候...")
        
        try:
            # 調用 gemini_create_video，預設 5 分鐘超時
            say_text, file_name = gemini_create_video(msg_text, "", 300)
            
            if file_name:
                send_video(channel, say_text, say, file_name)
            else:
                say(say_text)  # 顯示錯誤訊息
        except Exception as e:
            say(f"影片生成失敗：{e}")
    
    #!clearai
    @app.message(re.compile(r"^!clearai$"))
    def clearai(message, say):
        try:
            # 獲取發送指令的使用者 ID
            user_id = message['user']
            ai_clear_conversation_history()
            say("AI 聊天紀錄清除成功！")
        except Exception as e:
            say(f"AI 聊天紀錄清除錯誤！{e}")
            

