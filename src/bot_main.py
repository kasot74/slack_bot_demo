from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from .handlers import register_handlers
from .utilities import read_config
from .database import con_db
import logging

#logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', filename='app.log',  # 輸出到 app.log 檔案 filemode='w')  # 'w' 會覆蓋檔案，'a' 會追加到檔案末尾

# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
db = con_db(config)
# 初始化 Slack App
app = App(token=config['SLACK_BOT_TOKEN'], signing_secret=config['SLACK_SIGNING_SECRET'])

# 註冊所有處理器
register_handlers(app, config, db)

# 啟動 SocketModeHandler
if __name__ == "__main__":
    print(f"Slack Bot 啟動成功!")    
    SocketModeHandler(app, config['SLACK_APP_TOKEN']).start()