import re
import random
import os
import requests
import json  
import time
import threading 
from threading import Lock
from PIL import Image
from io import BytesIO
from slack_sdk import WebClient

from math import comb
from datetime import datetime, timedelta




COMMANDS_HELP = [    
    ("!曬卡", "隨機曬卡趣味指令"),
    ("!add 指令 回覆", "新增自訂指令"),
    ("!show", "顯示所有自訂指令"),
    ("!remove 指令", "刪除自訂指令")
]

def register_handlers(app, config, db):
    
    # !曬卡
    @app.message(re.compile(r"^!曬卡.*"))
    def show_card(message, say):        
        try:            
            # 1%
            if random.random() < 0.01:
                say("💔💔💔💔💔💔💔💔💔💔")
                return
            # 5%
            if random.random() < 0.05:
                # 隨機生成 1 到 8 個 :fish_body:
                num_fish_body = random.randint(0, 8)  
                fish_body = ":fish_body:" * num_fish_body
                fish = f":fish_head:{fish_body}:fish_tail:"
                say(fish + "機率:5%")
                return
            # quotes 中的可選元素
            quotes = [":rainbow:", ":poop:"]
            
            # 設置每次選擇 :rainbow: 的機率為 20%
            weights = [0.65, 0.35]
            
            # 抽選 10 次 quotes 的元素
            selected_quotes = random.choices(quotes, weights=weights, k=10)
            # 統計 :rainbow: 的出現次數
            rainbow_count = selected_quotes.count(":rainbow:")
            
            # 計算該情況的機率
            n = 10  # 總抽選次數
            p = 0.2  # 每次選擇 :rainbow: 的機率
            probability = comb(n, rainbow_count) * (p ** rainbow_count) * ((1 - p) ** (n - rainbow_count))
            
            hide_message = ""
            if rainbow_count == 10:
                hide_message = "全是 :rainbow:！你今天是🌈運！"
            if rainbow_count == 0:
                hide_message = "全是 :poop:！你今天是💩運!"
            # 傳送結果和機率
            say(f"{' '.join(selected_quotes)}\n {hide_message} ")
            

        except Exception as e:
            # 當發生錯誤時傳送錯誤訊息
            say(f"發生錯誤：{e}")

    # !add 指令
    @app.message(re.compile(r"^!add\s+(.+)\s+([\s\S]+)", re.DOTALL))
    def handle_add_message(message, say):
        match = re.match(r"^!add\s+(.+)\s+([\s\S]+)", message['text'], re.DOTALL)
        if match:
            msg_text = match.group(1).strip()  
            # 保留response_text中的原始格式，包括換行符
            response_text = match.group(2)  
            add_commit(msg_text, response_text, say)

    # !show 指令
    @app.message(re.compile(r"^!show$"))
    def handle_show(message, say):        
        collection = db.slock_bot_commit
        messages = collection.find({"is_sys": "N" })
        commit = "自訂指令:\n"
        for msg in messages:        
            commit += f"{msg['message']} => {msg['say']}\n"

        #messages = collection.find({"is_sys": "Y" })
        #commit += "管理員指令:\n"
        #for msg in messages:        
            #commit += f"{msg['message']} => {msg['say']}\n"
        say(commit)         

    # !remove 指令
    @app.message(re.compile(r"^!remove\s+(.+)$"))
    def handle_remove_message(message, say):
        match = re.match(r"^!remove\s+(.+)$", message['text'])
        if match:
            msg_text = match.group(1).strip()
            remove_commit(msg_text, say)        

    # Bot被提及回 "蛤?"
    @app.event("app_mention")
    def handle_app_mention_events(body, say):
        say(f"蛤?")    
    
    # 抽選人員Tag" 
    @app.message(re.compile(r"^誰.*"))
    def rand_tag_user(message, say, client):
        # 取當前用戶列表
        channel_id = message['channel']
        result = client.conversations_members(channel=channel_id)
        members = result['members']    

        # 隨機抽選用户
        if members:
            random_user = random.choice(members)
            user_info = client.users_info(user=random_user)
            user_name = user_info['user']['real_name'] 
            # 解析 "誰" 後面的所有字串 
            text = message['text']
            additional_text = text[text.index("誰") + 1:].strip() 
            # 顯示用戶名稱和附加字串 
            say(f" {user_name} {additional_text} !")                        
    
    # DB 新增處理    
    def add_commit(message_text, response_text, say):
        try:        
            collection = db.slock_bot_commit   
            if re.search(r"!.*", message_text):
                say("[!開頭] 保留字不可使用!")
                return  
            # 檢查是否已有相同的 message
            existing_message = collection.find_one({"message": message_text, "is_sys": "N" })
            
            if existing_message:
                # 更新現有指令            
                say("已有相關指令!")
            else:
                # 新增指令
                collection.insert_one({"message": message_text, "say": response_text, "is_sys": "N"})
                say("指令已新增!")            
        except Exception as e:
            # 異常處理
            print(f"Error inserting/updating document: {e}")
            # 發生例外錯誤!
            say(f"發生例外錯誤!{e}")

    # DB 刪除處理
    def remove_commit(message_text, say):
        try:
            collection = db.slock_bot_commit
            # 刪除指令
            result = collection.delete_many({"message": message_text, "is_sys": "N"})
            if result.deleted_count > 0:
                say("指令已刪除!")                        
            else:
                say("未找到相關指令!")
        except Exception as e:
            # 異常處理
            print(f"Error deleting document: {e}")
            say("發生例外錯誤!")

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

    #關鍵字
    @app.message(re.compile("(.*)"))
    def handle_message(message,say):        
        text = message['text']
        if re.search(r"^!.*", text):
            say("目前無此指令功能!")            
            return        
        channel = message['channel']        
        collection = db.slock_bot_commit
        keyword_all = collection.find()        
        # 遍歷每條資料
        for doc in keyword_all:            
            message_text = doc.get('message')
            if re.search(re.escape(message_text), text):                            
                file_path = os.path.join('slack_images',doc.get('file'))                
                send_image(channel, doc['say'],say, file_path)            
                return
