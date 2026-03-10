import re
import requests
import time
import json
import threading
from datetime import datetime, timedelta
from pymongo import MongoClient
from slack_sdk import WebClient
from ..stock import get_stock_info, get_historical_data

COMMANDS_HELP = [
    ("!查股 股票代碼", "查詢指定股票的即時資訊")    
]


def register_stock_handlers(app, config, db):
    # !查股    
    @app.message(re.compile(r"^!查股\s+(.+)$"))
    def search_slock(message, say):
        msg_text = re.match(r"^!查股\s+(.+)$", message['text']).group(1).strip()
        say(get_stock_info(msg_text))
    

