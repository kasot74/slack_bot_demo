import re
import requests
import time
import json
import threading
from datetime import datetime, timedelta
from pymongo import MongoClient
from slack_sdk import WebClient
from ..stock import get_stock_info, get_historical_data, get_crypto_prices

COMMANDS_HELP = [
    ("!查股 股票代碼", "查詢指定股票的即時資訊"),
    ("!技術分析 股票代碼", "查詢指定股票的技術分析"),
    ("!MAX", "MAX 交易所加密貨幣即時價格"),
]


def register_stock_handlers(app, config, db):
    # !查股    
    @app.message(re.compile(r"^!查股\s+(.+)$"))
    def search_slock(message, say):
        msg_text = re.match(r"^!查股\s+(.+)$", message['text']).group(1).strip()
        say(get_stock_info(msg_text))
    
    # !MAX    
    @app.message(re.compile(r"^!MAX$"))
    def get_max_price(message, say):        
        say(get_crypto_prices())

# (工具函數已移至 ..stock)
