from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from .model.handlers_model import register_handlers as base_register_handlers
from .model.coin_model import register_coin_handlers
from .model.stock_model import register_stock_handlers
from .model.shop_model import register_shop_handlers
from .model.ai_model import register_handlers as register_ai_handlers


from .model.handlers_model import COMMANDS_HELP as HANDLER_COMMANDS
from .model.coin_model import COMMANDS_HELP as COIN_COMMANDS
from .model.stock_model import COMMANDS_HELP as STOCK_COMMANDS
from .model.shop_model import COMMANDS_HELP as SHOP_COMMANDS
from .model.ai_model import COMMANDS_HELP as AI_COMMANDS


from .utilities import read_config
from .database import con_db
from .model.resource_monitor import ResourceCleaner, register_resource_commands
import os
import re

# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
db = con_db(config)
# 初始化 Slack App
app = App(token=config['SLACK_BOT_TOKEN'], signing_secret=config['SLACK_SIGNING_SECRET'])

ALL_COMMANDS = [("!help 或 !指令", "顯示所有可用指令")]

def get_all_commands_text():
    help_text = "*可用指令列表：*\n"
    for cmd, desc in ALL_COMMANDS:
        help_text += f"`{cmd}`：{desc}\n"
    return help_text
@app.message(re.compile(r"^!help$|^!指令$"))
def show_help(message, say):
    say(get_all_commands_text())

# 建立資源清理器
#cleaner = ResourceCleaner(interval_hours=6, memory_threshold_mb=400)

# 註冊資源管理命令
#RESOURCE_COMMANDS = register_resource_commands(app, cleaner)
#ALL_COMMANDS += RESOURCE_COMMANDS

# 貨幣模組
ALL_COMMANDS += COIN_COMMANDS
register_coin_handlers(app, config, db)

# 商店模組
ALL_COMMANDS += SHOP_COMMANDS
register_shop_handlers(app, config, db)

# 股票模組
ALL_COMMANDS += STOCK_COMMANDS
register_stock_handlers(app, config, db)

# AI 模組
ALL_COMMANDS += AI_COMMANDS
register_ai_handlers(app, config, db)

# 註冊其他處理器
ALL_COMMANDS += HANDLER_COMMANDS
base_register_handlers(app, config, db)

# 啟動 SocketModeHandler
if __name__ == "__main__":    

    # 啟動資源監控
    cleaner.start_monitoring()
    SocketModeHandler(app, config['SLACK_APP_TOKEN']).start()    