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
from ..AI_Service.openai import clear_conversation_history as openai_clear_conversation_history
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

COMMANDS_HELP = [
    ("!openai 內容", "詢問 GPT "),
    ("!claude 內容", "詢問 Claude "),
    ("!xai 內容", "詢問 grok"),
    ("!xai查 [web|x|news] 查詢內容", "AI 搜尋摘要"),
    ("!畫 內容", "用 StabilityAI 產生圖片"),
    ("!畫2 內容", "用 StabilityAI 產生圖片(第二模型)"),
    ("!xai畫 內容", "用 xai 產生圖片"),
    ("!改風格 內容", "兩張圖進行風格轉換"),
    ("!改圖 內容", "單張圖進行內容修改"),
    ("!動起來", "將圖片轉為影片"),
    ("!clearai", "清除 AI 聊天紀錄"),
    ("!lookai", "查看 AI 聊天紀錄")
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

    #!畫
    @app.message(re.compile(r"^!畫\s+(.+)$"))
    def create_image(message, say):        
        channel = message['channel']
        msg_text = re.match(r"^!畫\s+(.+)$", message['text']).group(1).strip()
        say_text, file_name = get_image(msg_text)                        
        send_image(channel, say_text, say, file_name)

    #!畫2
    @app.message(re.compile(r"^!畫2\s+(.+)$"))
    def create_image(message, say):        
        channel = message['channel']
        msg_text = re.match(r"^!畫2\s+(.+)$", message['text']).group(1).strip()
        say_text, file_name = get_image2(msg_text)                        
        send_image(channel, say_text, say, file_name)
        

    #!xai畫
    @app.message(re.compile(r"^!xai畫\s+(.+)$"))
    def create_image(message, say):        
        channel = message['channel']
        msg_text = re.match(r"^!xai畫\s+(.+)$", message['text']).group(1).strip()
        say_text, file_name = xai_create_image(msg_text)                        
        send_image(channel, say_text, say, file_name)

    #!改風格
    @app.message(re.compile(r"^!改風格\s+(.+)$"))
    def change_image_style(message, say):        
        channel = message['channel']
        msg_text = re.match(r"^!改風格\s+(.+)$", message['text']).group(1).strip()
        # 檢查是否有上傳的圖檔
        if 'files' in message and len(message['files']) >= 2:
            file_info_1 = message['files'][0]  # 第一個檔案
            file_info_2 = message['files'][1]  # 第二個檔案

            # 確保兩個檔案都是圖像格式
            if file_info_1['mimetype'].startswith('image/') and file_info_2['mimetype'].startswith('image/'):
                try:
                    # 下載第一個圖檔
                    response_1 = requests.get(
                        file_info_1['url_private'],
                        headers={"Authorization": f"Bearer {config['SLACK_BOT_TOKEN']}"}
                    )
                    response_1.raise_for_status()

                    # 下載第二個圖檔
                    response_2 = requests.get(
                        file_info_2['url_private'],
                        headers={"Authorization": f"Bearer {config['SLACK_BOT_TOKEN']}"}
                    )
                    response_2.raise_for_status()

                    # 將兩個圖檔傳遞給 change_style 函數
                    say_text, file_name = change_style(BytesIO(response_1.content), BytesIO(response_2.content),msg_text)
                    send_image(channel, say_text, say, file_name)
                    return
                except requests.exceptions.RequestException as e:
                    say(f"無法下載圖檔：{e}")
                    return
                except Exception as e:
                    say(f"無法處理上傳的圖檔：{e}")
                    return
            else:
                say("上傳的檔案中有非圖像格式的檔案！")
                return

        # 如果沒有上傳足夠的檔案，提示用戶
        say("請上傳兩個圖檔以進行風格修改！ 第一張是修改原圖，第二張是風格參考圖！")

    #!改圖
    @app.message(re.compile(r"^!改圖\s+(.+)$"))    
    def change_image_text(message, say):
        channel = message['channel']
        msg_text = re.match(r"^!改圖\s+(.+)$", message['text']).group(1).strip()
        # 檢查是否有上傳的圖檔
        if 'files' in message and len(message['files']) >= 1:
            file_info_1 = message['files'][0]  # 第一個檔案                        

            # 確保兩個檔案都是圖像格式
            if file_info_1['mimetype'].startswith('image/') :
                try:
                    
                    response_1 = requests.get(
                        file_info_1['url_private'],
                        headers={"Authorization": f"Bearer {config['SLACK_BOT_TOKEN']}"}
                    )
                    response_1.raise_for_status()                    
                       
                    say_text, file_name = change_image(BytesIO(response_1.content),msg_text)
                    send_image(channel, say_text, say, file_name)
                    return
                except requests.exceptions.RequestException as e:
                    say(f"無法下載圖檔：{e}")
                    return
                except Exception as e:
                    say(f"無法處理上傳的圖檔：{e}")
                    return
            else:
                say("上傳的檔案中有非圖像格式的檔案！")
                return

        # 如果沒有上傳足夠的檔案，提示用戶
        say("請上傳1個圖檔以進行修改！")

    #!動起來
    @app.message(re.compile(r"^!動起來.*"))    
    def image_video(message, say):
        channel = message['channel']        
        # 檢查是否有上傳的圖檔
        if 'files' in message and len(message['files']) >= 1:
            file_info_1 = message['files'][0]  # 第一個檔案                        

            # 確保檔案是圖像格式
            if file_info_1['mimetype'].startswith('image/') :
                try:
                    
                    response_1 = requests.get(
                        file_info_1['url_private'],
                        headers={"Authorization": f"Bearer {config['SLACK_BOT_TOKEN']}"}
                    )
                    response_1.raise_for_status()                    
                       
                    say_text, file_name = image_to_video(BytesIO(response_1.content))
                    send_image(channel, say_text, say, file_name)
                    return
                except requests.exceptions.RequestException as e:
                    say(f"無法下載圖檔：{e}")
                    return
                except Exception as e:
                    say(f"無法處理上傳的圖檔：{e}")
                    return
            else:
                say("上傳的檔案中有非圖像格式的檔案！")
                return

        # 如果沒有上傳足夠的檔案，提示用戶
        say("請上傳1個圖檔以進行修改！")        

    #!clearai
    @app.message(re.compile(r"^!clearai$"))
    def clearai(message, say):
        try:
            # 獲取發送指令的使用者 ID
            user_id = message['user']
            openai_clear_conversation_history()
            say("AI 聊天紀錄清除成功！")
        except Exception as e:
            say(f"AI 聊天紀錄清除錯誤！{e}")
    #!lookai        
    @app.message(re.compile(r"^!lookai$"))
    def lookai(message, say):        
        try:
            his = openai_look_conversation_history()
            say(his)
        except Exception as e:
            say(f"AI聊天紀錄查看錯誤!{e}")

