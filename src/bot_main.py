from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from .handlers import register_handlers
from .utilities import read_config
from .database import db

# 從配置文件中讀取 tokens
config = read_config('config/config.txt')

# 初始化 Slack App
app = App(token=config['SLACK_BOT_TOKEN'], signing_secret=config['SLACK_SIGNING_SECRET'])

# 註冊所有處理器
register_handlers(app, config, db)

# 啟動 SocketModeHandler
if __name__ == "__main__":
    SocketModeHandler(app, config['SLACK_APP_TOKEN']).start()