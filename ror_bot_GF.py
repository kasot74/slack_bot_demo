from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from pymongo import MongoClient
import re
import random
import logging
from slack_sdk.errors import SlackApiError
import os

# 從配置文件中讀取
def read_config(file_path):
    config = {}
    with open(file_path, 'r') as file:
        for line in file:
            key, value = line.strip().split('=')
            config[key] = value
    return config

# 讀取 tokens
config = read_config('config.txt')

#DB連線
client = MongoClient("mongodb://localhost:27017/")
db = client.myDatabase
collection = db.slock_bot_commit

# 初始化
app = App(token=config['SLACK_BOT_TOKEN'], signing_secret=config['SLACK_SIGNING_SECRET'])

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
def handle_add_message(message, say):
    db = client.myDatabase
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
@app.message(re.compile(r"誰.*"))
def rand_tag_user(message, say, client):
    # 取當前用戶列表
    result = client.conversations_members(channel=channel_id)
    channel_id = message['channel']
    members = result['members']

    # 取在線人員
    members = get_online_members(client, channel_id)

    # 隨機抽選用户
    if members:
        random_user = random.choice(members)
        say(f"<@{random_user}>")
    else:
        say(f"<@{random_user}>")

# 回傳目前在線用户
def get_online_members(client, channel_id):
    result = client.conversations_members(channel=channel_id)
    members = result['members']    
    members = [member for member in members ]

    # 篩選出上限member
    online_members = []
    for member in members:
        profile = client.users_getPresence(user=member)
        if profile['presence'] == 'active':
            online_members.append(member)
    print(f"online_members")
    return online_members

# 發送圖片函數
def send_image(channel_id, message, file_path=None):
    try:
        if file_path:
            response = app.client.files_upload_v2(
                channel=channel_id,
                file=file_path,
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
    except SlackApiError as e:
        print(f"Error uploading file: {e.response['error']}")            

# DB 新增處理
def add_commit(message_text, response_text, say):
    try:        
        if re.search(r".*全亨.*", message_text):
            say("[全亨] 保留字不可使用!")
            return             
        if re.search(r"!.*", message_text):
            say("[!開頭] 保留字不可使用!")
            return  
        # 检查是否已有相同的 message
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

# 儲存已提交的數字
submitted_numbers = int()
submitted_numbers_max = 100
submitted_numbers_min = 1

# 處理消息事件，發送包含按鈕的訊息
@app.message("!猜數字")
def send_button(message, say):
    global submitted_numbers
    if submitted_numbers:
        say("遊戲已經開始!!")
    else:
        say(
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "點擊下面的按鈕來設定數字。"},
                    "accessory": {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "設定"},
                        "action_id": "open_modal_button"
                    }
                }
            ]
        )

# 處理按鈕事件，打開模態對話框
@app.action("open_modal_button")
def open_modal_button(ack, body, client):
    global submitted_numbers
    # 獲取用戶 ID 和頻道 ID
    channel_id = body['channel']['id']
    submitter_id = body['user']['id']
    
    # 檢查是否已經有數字被提交
    if submitted_numbers:
        try:
            # 發送提示訊息
            client.chat_postEphemeral(
                channel=channel_id,
                user=submitter_id,
                text="遊戲已經開始!!"
            )
        except SlackApiError as e:
            print(f"Error posting ephemeral message: {e.response['error']}")
        return
    
    # 確認收到按鈕事件
    ack()
    
    try:
        # 打開模態對話框
        client.views_open(
            trigger_id=body['trigger_id'],
            view={
                "type": "modal",
                "callback_id": "input_modal",
                "title": {"type": "plain_text", "text": "輸入資料"},
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "input_block",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "input_action",
                            "placeholder": {"type": "plain_text", "text": "輸入一個數字 (1 到 100)..."}
                        },
                        "label": {"type": "plain_text", "text": "你的數字"}
                    }
                ],
                "submit": {"type": "plain_text", "text": "提交"},
                "private_metadata": body['user']['id']  # 儲存打開模態的使用者 ID
            }
        )
    except SlackApiError as e:
        print(f"Error opening modal: {e.response['error']}")

#處理模態提交的事件
@app.view("input_modal")
def handle_input_submission(ack, body, client):
    global submitted_numbers
    ack()

    # 獲取用戶提交的數字
    user_input = body['view']['state']['values']['input_block']['input_action']['value']
    submitter_id = body['user']['id']
    opener_id = body['view']['private_metadata']

    # 嘗試將提交的數字轉換為整數
    try:
        number = int(user_input)
    except ValueError:
        number = None

    # 獲取頻道 ID
    channel_id = body['view']['private_metadata']

    # 確認提交者是否是打開模態的用戶
    if submitter_id == opener_id:
        # 檢查數字是否在範圍內
        if number is not None and 1 <= number <= 100:
            # 檢查數字是否已經被提交過
            submitted_numbers = number
            try:
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=submitter_id,
                    text=f"<@{submitter_id}> 提交的數字是: {number}"
                )
            except SlackApiError as e:
                print(f"Error posting ephemeral message: {e.response['error']}")            
        else:
            # 如果數字不在有效範圍內，更新模態並提示用戶
            try:
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"<@{submitter_id}>是壞蛋!想壞壞! 請輸入1~100!"
                )
            except SlackApiError as e:
                print(f"Error updating modal: {e}")
    else:
        # 如果提交者不是打開模態的用戶，通知用戶無權提交
        try:
            client.chat_postEphemeral(
                channel=channel_id,
                user=submitter_id,
                text="你無權提交這個模態。"
            )
        except SlackApiError as e:
            print(f"Error posting error message: {e.response['error']}")

#關鍵字
@app.message(re.compile("(.*)"))
def handle_message(message, say):
    text = message['text']
    channel = message['channel']
    submitter_id = message['user']
    keyword = collection.find_one({"message": text })        
    if keyword: 
        # 根據 keyword 資料決定是否傳遞 file_path
        file_path = keyword.get('file')
        send_image(channel, keyword['say'], file_path)    
    global submitted_numbers, submitted_numbers_min , submitted_numbers_max    
    if submitted_numbers:                
        if text.isdigit() :
            number = int(text)            
            if number == submitted_numbers:            
                say(f"恭喜<@{submitter_id}>猜對 正解:{number}!")                            
                submitted_numbers = int()
                submitted_numbers_max = 100
                submitted_numbers_min = 1
            else:
                if number < submitted_numbers:
                    submitted_numbers_min = number
                else:
                    submitted_numbers_max = number                    
                hint = f"範圍是{submitted_numbers_min}~{submitted_numbers_max} "                
                say(f"猜錯了!，{hint}")

# 應用啟動
if __name__ == "__main__":    
    handler = SocketModeHandler(app, config['SLACK_APP_TOKEN'])
    handler.start()