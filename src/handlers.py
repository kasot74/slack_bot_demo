import re
import random
import os
import requests
from PIL import Image
from io import BytesIO
from slack_sdk import WebClient
import time
import threading

from math import comb
from datetime import datetime, timedelta
# openai imports
from .AI_Service.openai import generate_summary as generate_summary_openai
from .AI_Service.openai import clear_conversation_history as openai_clear_conversation_history
from .AI_Service.openai import look_conversation_history as openai_look_conversation_history

# claude imports
from .AI_Service.claude import generate_summary as generate_summary_claude
from .AI_Service.claude import role_generate_response as role_generate_summary_claude

# xai imports
from .AI_Service.xai import generate_summary as generate_summary_xai
from .AI_Service.xai import analyze_sentiment as analyze_sentiment_xai 
from .AI_Service.xai import role_generate_response as role_generate_summary_xai
from .AI_Service.xai import analyze_stock as analyze_stock_xai
from .AI_Service.xai import analyze_stock_inoutpoint as analyze_stock_inoutpoint_xai
from .AI_Service.xai import xai_create_image as xai_create_image


from .stability_model import get_image,get_image2,change_style,change_image
from .stock import get_stock_info
from .stock import get_historical_data

class MemberMonitor:
    def __init__(self, bot_token, say):
        self.client = WebClient(token=bot_token)
        self.last_check_time = None
        self.user_status = {}  # 用於記錄用戶的狀態
        

    def get_all_members(self):
        try:
            result = self.client.users_list()
            return result["members"]
        except Exception as e:
            print(f"Error getting members: {e}")
            return []

    def check_and_greet_members(self):
        members = self.get_all_members()
        
        for member in members:
            # 排除機器人和應用用戶
            if not (member.get("is_bot") or member.get("is_app_user")):
                try:
                    presence = self.client.users_getPresence(user=member["id"])
                    user_id = member["id"]
                    #name = member.get("name", "")
                    #user_name = member.get("real_name", "")
                    user_name = member.get("profile", {}).get("display_name", "")
                    current_presence = presence["presence"] #presence["online"]
                    # 檢查狀態是否變化
                    if user_id in self.user_status:
                        previous_presence = self.user_status[user_id]
                        if previous_presence != current_presence:
                            if current_presence == "active":                                                            
                                self.client.chat_postMessage(
                                    channel="C02QLJMNLAE",  
                                    text=f"親愛的 {user_name} 出現了!",
                                )
                            else:                                
                                self.client.chat_postMessage(
                                    channel="C02QLJMNLAE",  
                                    text=f" {user_name} 掰掰!",
                                )
                    else:
                        # 首次檢查時初始化狀態
                        print(f"用戶 {user_name}狀態初始化為")

                    # 更新用戶狀態
                    self.user_status[user_id] = current_presence
                except Exception as e:
                    print(f"Error processing member {member['id']}: {e}")

        self.last_check_time = datetime.now()

    def start_monitoring(self, interval=30):  # 每60秒檢查一次
        def monitor():
            while True:
                self.check_and_greet_members()
                
                time.sleep(interval)

        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()

def register_handlers(app, config, db):

    # 初始化 MemberMonitor 並傳入 say 方法
    monitor = MemberMonitor(bot_token=config["SLACK_BOT_TOKEN"], say=app.client.chat_postMessage)
    # 啟動定時檢查
    monitor.start_monitoring(interval=30)     
    
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

    # !pk role1 role2
    @app.message(re.compile(r"^!pk\s+(\S+)\s+(\S+)", re.DOTALL))
    def handle_aipk_messages(message, say):
        match = re.match(r"^!pk\s+(\S+)\s+(\S+)", message['text'], re.DOTALL)
        if match:
            role1 = match.group(1).strip()
            role2 = match.group(2).strip()
            thread_ts = message['ts']                        
            answer = "請開始"
            # 使用不同 AI 模型生成問答內容
            for i in range(3):                
                answer = role_generate_summary_claude(role2,role1,answer ,thread_ts)
                say(text=f"*{role2}:* {answer}", thread_ts=thread_ts)
                
                answer = role_generate_summary_xai(role1,role2,answer ,thread_ts)
                say(text=f"*{role1}:* {answer}", thread_ts=thread_ts)                

    # !查股    
    @app.message(re.compile(r"^!查股\s+(.+)$"))
    def search_slock(message, say):
        msg_text = re.match(r"^!查股\s+(.+)$", message['text']).group(1).strip()
        say(get_stock_info(msg_text))

    # !技術分析    
    @app.message(re.compile(r"^!技術分析\s+(.+)$"))
    def analyze_slock(message, say):
        msg_text = re.match(r"^!技術分析\s+(.+)$", message['text']).group(1).strip()
        now_data = get_stock_info(msg_text)
        his_data = []        
        today = datetime.now()        
        for i in range(6):
            first_day_of_month = (today.replace(day=1) - timedelta(days=i*30)).strftime('%Y%m01')
            his_data.append(get_historical_data(msg_text,first_day_of_month))        
        say(analyze_stock_xai(his_data,now_data), thread_ts=message['ts'])

    # !買賣建議    
    @app.message(re.compile(r"^!買賣建議\s+(.+)$"))
    def analyze_slock_point(message, say):
        msg_text = re.match(r"^!買賣建議\s+(.+)$", message['text']).group(1).strip()
        now_data = get_stock_info(msg_text)
        his_data = []        
        today = datetime.now()        
        for i in range(3):
            first_day_of_month = (today.replace(day=1) - timedelta(days=i*30)).strftime('%Y%m01')
            his_data.append(get_historical_data(msg_text,first_day_of_month))        
        say(analyze_stock_inoutpoint_xai(his_data,now_data), thread_ts=message['ts'])

    # !熬雞湯    
    @app.message(re.compile(r"^!熬雞湯\s+(.+)$"))
    def new_philosophy_quotes(message, say):
        collection = db.philosophy_quotes
        msg_text = re.match(r"^!熬雞湯\s+(.+)$", message['text']).group(1).strip()
        existing_message = collection.find_one({"quote": msg_text})
        
        if existing_message:
            say("失敗! 已有此雞湯!")
        else:
            sentiment_result = analyze_sentiment_xai(msg_text)
            if "正能量" in sentiment_result:
                collection.insert_one({"quote": msg_text})
                say("雞湯熬煮成功!")
            else:
                say("這雞湯有毒!")

    # !喝雞湯
    @app.message(re.compile(r"^!喝雞湯$"))
    def get_philosophy_quotes(message, say):
        collection = db.philosophy_quotes
        quotes = list(collection.find())    
        # 檢查是否有可用的語錄
        if quotes:
            # 隨機選擇一條語錄
            selected_quote = random.choice(quotes)                        
            quote_text = selected_quote.get("quote", "沒有找到雞湯語錄")
            # 回應用戶
            say(quote_text)
        else:
            say("目前沒有雞湯語錄可用，請稍後再試。")

    # !雞湯菜單
    @app.message(re.compile(r"^!雞湯菜單$"))
    def get_all_philosophy_quotes(message, say):
        collection = db.philosophy_quotes
        quotes = list(collection.find())    
        # 檢查是否有可用的語錄
        if quotes:
            # 建立一個包含所有雞湯語錄的列表
            all_quotes = [f"{idx + 1}. {quote.get('quote', '沒有找到雞湯語錄')}" for idx, quote in enumerate(quotes)]
            # 將列表轉換為單一字串，換行分隔
            quotes_text = "\n".join(all_quotes)
            # 回應用戶
            say(f"以下是所有雞湯語錄:\n{quotes_text}")
        else:
            say("目前沒有雞湯語錄可用，請稍後再試。")

    # !釣魚
    @app.message(re.compile(r"^!釣魚$"))
    def get_fish(message, say):        
        folder_path=os.path.join('images','fishpond')
        channel = message['channel']
        try:
            # 獲取資料夾中的所有檔案名稱
            quotes = os.listdir(folder_path)            
            # 檢查是否有可用的檔案
            if quotes:
                if random.random() < 0.7:  # 70%的機率釣到檔案
                    # 隨機選取一個或多個檔案                    
                    selected_quote = random.choice(quotes)           
                    message = " :fishing_pole_and_fish: 你釣到了!"
                    file_path = os.path.join(folder_path, selected_quote)                                         
                    response = app.client.files_upload_v2(
                        channel=channel,
                        file=file_path,
                        initial_comment=message
                    )    
                else:
                    # 30%的機率沒釣到
                    say(" :sob: 很遺憾，你什麼也沒釣到！")
            else:
                say("資料夾是空的，沒有檔案可釣取。")
        except Exception as e:
            say(f"發生錯誤：{e}")

    # !曬卡
    @app.message(re.compile(r"^!曬卡.*"))
    def show_card(message, say):
        channel = message['channel']
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
                hide_message = "全是 :rainbow:！你今天是🌈神！"
            if rainbow_count == 0:
                hide_message = "全是 :poop:！你今天是💩神!"
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
        if 'files' in message and len(message['files']) >= 2:
            file_info_1 = message['files'][0]  # 第一個檔案            
            file_info_2 = message['files'][1]  # 第一個檔案            

            # 確保兩個檔案都是圖像格式
            if file_info_1['mimetype'].startswith('image/') and file_info_2['mimetype'].startswith('image/'):
                try:
                    
                    response_1 = requests.get(
                        file_info_1['url_private'],
                        headers={"Authorization": f"Bearer {config['SLACK_BOT_TOKEN']}"}
                    )
                    response_1.raise_for_status()                    

                    response_2 = requests.get(
                        file_info_2['url_private'],
                        headers={"Authorization": f"Bearer {config['SLACK_BOT_TOKEN']}"}
                    )
                    response_2.raise_for_status()      
                    
                    say_text, file_name = change_image(BytesIO(response_1.content), BytesIO(response_2.content),msg_text)
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
        say(f"權限不足!!")
        return
        try:
            openai_clear_conversation_history()
            say("AI聊天紀錄清除成功!")
        except Exception as e:
            say(f"AI聊天紀錄清除錯誤!{e}")
    #!lookai        
    @app.message(re.compile(r"^!lookai$"))
    def lookai(message, say):        
        try:
            his = openai_look_conversation_history()
            say(his)
        except Exception as e:
            say(f"AI聊天紀錄查看錯誤!{e}")

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
            message = doc.get('message')
            if re.search(re.escape(message), text):                            
                file_path = os.path.join('slack_images',doc.get('file'))                
                send_image(channel, doc['say'],say, file_path)            
                return

