from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from .handlers import register_handlers
from .model.coin_model import register_coin_handlers
from .model.member_monitor import register_member_handlers
from .model.stock_model import register_stock_handlers
from .utilities import read_config
from .database import con_db
import os

# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
db = con_db(config)
# 初始化 Slack App
app = App(token=config['SLACK_BOT_TOKEN'], signing_secret=config['SLACK_SIGNING_SECRET'])

# 貨幣模組
register_coin_handlers(app, config, db)

# 註冊成員打招呼模組
register_member_handlers(app, config, db)

# 股票模組
register_stock_handlers(app, config, db)

# 註冊其他處理器
register_handlers(app, config, db)

# 啟動 SocketModeHandler
if __name__ == "__main__":    
    SocketModeHandler(app, config['SLACK_APP_TOKEN']).start()    