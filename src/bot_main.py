from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.rtm_v2 import RTMClient
from slack_sdk import WebClient
from .handlers import register_handlers
from .utilities import read_config
from .database import con_db
import os

# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
db = con_db(config)
# 初始化 Slack App
app = App(token=config['SLACK_BOT_TOKEN'], signing_secret=config['SLACK_SIGNING_SECRET'])

# 註冊所有處理器
register_handlers(app, config, db)

# 初始化 RTMClient
rtm_client = RTMClient(token=config['SLACK_BOT_TOKEN'])


@rtm_client.on("open")
def subscribe_presence(client):
    try:
        # 從資料庫中讀取用戶 ID
        collection = db.slackuserid  # 指定 MongoDB 集合
        user_ids = [user["user_id"] for user in collection.find()]  # 獲取所有用戶的 ID

        if not user_ids:
            print("資料庫中沒有用戶 ID，無法訂閱在線狀態！")
            return

        # 訂閱所有用戶的 presence_change 事件
        client.send_json({"type": "presence_sub", "ids": user_ids})
        print(f"成功訂閱用戶的在線狀態！訂閱的用戶 ID：{user_ids}")
    except Exception as e:
        print(f"訂閱用戶在線狀態失敗：{e}")

@rtm_client.on("presence_change")
def user_online(client, event):
    user_id = event.get("user")
    presence = event.get("presence")

    if presence == "active":
        try:
            user_info = client.users_info(user=user_id)
            user_name = user_info["user"]["name"]
            print(f"{user_name} 上線啦！")  # 替換為你需要的動作，例如發送訊息
        except Exception as e:
            print(f"無法獲取用戶資訊：{e}")

# 啟動 SocketModeHandler
if __name__ == "__main__":
    print(f"Slack Bot 啟動成功!")    
    SocketModeHandler(app, config['SLACK_APP_TOKEN']).start()
    #rtm_client.start()