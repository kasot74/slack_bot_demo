from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from .handlers import register_handlers
from .model.coin_model import register_coin_handlers
from .model.member_monitor import register_member_handlers
from .model.stock_model import register_stock_handlers
from .model.shop_model import register_shop_handlers
from .model.ai_model import register_handlers as register_ai_handlers
from .model.adventure_model import register_adventure_handlers

from .handlers import COMMANDS_HELP as HANDLER_COMMANDS
from .model.coin_model import COMMANDS_HELP as COIN_COMMANDS
from .model.member_monitor import COMMANDS_HELP as MEMBER_COMMANDS
from .model.stock_model import COMMANDS_HELP as STOCK_COMMANDS
from .model.shop_model import COMMANDS_HELP as SHOP_COMMANDS
from .model.ai_model import COMMANDS_HELP as AI_COMMANDS
from .model.adventure_model import COMMANDS_HELP as ADVENTURE_COMMANDS

from .utilities import read_config
from .database import con_db
import os
import re

# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
db = con_db(config)
# 初始化 Slack App
app = App(token=config['SLACK_BOT_TOKEN'], signing_secret=config['SLACK_SIGNING_SECRET'])

ALL_COMMANDS = []

def get_all_commands_text():
    help_text = "*可用指令列表：*\n"
    for cmd, desc in ALL_COMMANDS:
        help_text += f"`{cmd}`：{desc}\n"
    return help_text
@app.message(re.compile(r"^!help$|^!指令$"))
def show_help(message, say):
    say(get_all_commands_text())

# 貨幣模組
ALL_COMMANDS += COIN_COMMANDS
register_coin_handlers(app, config, db)

# 註冊成員打招呼模組
ALL_COMMANDS += MEMBER_COMMANDS
register_member_handlers(app, config, db)

# 商店模組
ALL_COMMANDS += SHOP_COMMANDS
register_shop_handlers(app, config, db)

# 股票模組
ALL_COMMANDS += STOCK_COMMANDS
register_stock_handlers(app, config, db)

# AI 模組
ALL_COMMANDS += AI_COMMANDS
register_ai_handlers(app, config, db)

# 冒險遊戲模組
ALL_COMMANDS += ADVENTURE_COMMANDS
register_adventure_handlers(app, config, db)

# 註冊其他處理器
ALL_COMMANDS += HANDLER_COMMANDS
register_handlers(app, config, db)

# 啟動 SocketModeHandler
if __name__ == "__main__":    
    SocketModeHandler(app, config['SLACK_APP_TOKEN']).start()    