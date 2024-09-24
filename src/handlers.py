import re
import random
from .openai_service import generate_summary, analyze_sentiment, validate_with_openai
import os

def register_handlers(app, config, db):
    
    # Call OpenAI
    @app.message(re.compile(r"!openai\s+(.+)"))
    def handle_summary_command(message, say):
        user_input = message['text'].replace('!openai', '').strip()    
        # 調用 OpenAI API 生成摘要
        try:        
            summary = generate_summary(user_input)
            say(f"{summary}")            
        except Exception as e:        
            say(f"非預期性問題 {e}")

    # !熬雞湯    
    @app.message(re.compile(r"^!熬雞湯\s+(.+)$"))
    def new_philosophy_quotes(message, say):
        collection = db.philosophy_quotes
        msg_text = re.match(r"^!熬雞湯\s+(.+)$", message['text']).group(1).strip()
        existing_message = collection.find_one({"quote": msg_text})
        
        if existing_message:
            say("失敗! 已有此雞湯!")
        else:
            sentiment_result = analyze_sentiment(msg_text)
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


    # !add 指令
    @app.message(re.compile(r"^!add\s+(.+)\s+(.+)$"))
    def handle_add_message(message, say):
        match = re.match(r"^!add\s+(.+)\s+(.+)$", message['text'])
        if match:
            msg_text = match.group(1).strip()
            response_text = match.group(2).strip()
            add_commit(msg_text, response_text, say)

    # !show 指令
    @app.message(re.compile(r"^!show$"))
    def handle_show(message, say):        
        collection = db.slock_bot_commit
        messages = collection.find({"is_sys": "N" })
        commit = "自訂指令:\n"
        for msg in messages:        
            commit += f"{msg['message']} => {msg['say']}\n"

        messages = collection.find({"is_sys": "Y" })
        commit += "管理員指令:\n"
        for msg in messages:        
            commit += f"{msg['message']} => {msg['say']}\n"
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
            say(f"<@{random_user}>")
        else:
            say(f"<@{random_user}>")
   
    # DB 新增處理
    def add_commit(message_text, response_text, say):
        try:        
            collection = db.slock_bot_commit
            if re.search(r".*全亨.*", message_text):
                say("[全亨] 保留字不可使用!")
                return             
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
            say("發生例外錯誤!")

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
    def send_image(channel_id, message, file_path=None):
        try:
            if file_path:
                response = app.client.files_upload_v2(
                    channel=channel_id,
                    file=os.path.join('images',file_path),
                    initial_comment=message
                )
                assert response["file"]
            else:
                # 如果沒有提供 file_path，則只發送訊息
                response = app.client.chat_postMessage(
                    channel=channel_id,
                    text=message
                )
                assert response["ok"]
        except Exception as e:
            print(f"Error uploading file: {e.response['error']}")     
        
    #關鍵字
    @app.message(re.compile("(.*)"))
    def handle_message(message,say):
        text = message['text']
        channel = message['channel']        
        collection = db.slock_bot_commit
        keyword = collection.find_one({"message": text })        
        if keyword: 
            # 根據 keyword 資料決定是否傳遞 file_path
            file_path = keyword.get('file')
            send_image(channel, keyword['say'], file_path)    
            return
        if text.length >= 3:
            # 使用 OpenAI 檢查文本
            validation_response = validate_with_openai(text)            
            # 檢查 OpenAI 回覆是否有錯誤
            if validate_with_openai(text) != "正確":
                # 這裡可以進行錯誤處理，例如發送回應或記錄錯誤            
                say(f"發現錯字 :melting_face: {validation_response}")