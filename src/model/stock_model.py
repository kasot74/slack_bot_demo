import re
import time
import json
import threading
from datetime import datetime
from pymongo import MongoClient
from slack_sdk import WebClient

# stock_model
from .stock import get_stock_info
from .stock import get_historical_data

def register_stock_handlers(app, config, db):
    # !查股    
    @app.message(re.compile(r"^!查股\s+(.+)$"))
    def search_slock(message, say):
        msg_text = re.match(r"^!查股\s+(.+)$", message['text']).group(1).strip()
        say(get_stock_info(msg_text))

    # !技術分析    
    @app.message(re.compile(r"^!技術分析\s+(.+)$"))
    def analyze_slock(message, say):
        msg_text = re.match(r"^!技術分析\s+(.+)$", message['text']).group(1).strip()
        now_data = get_stock_info(msg_text)
        his_data = []        
        today = datetime.now()        
        for i in range(6):
            first_day_of_month = (today.replace(day=1) - timedelta(days=i*30)).strftime('%Y%m01')
            his_data.append(get_historical_data(msg_text,first_day_of_month))        
        say(analyze_stock_xai(his_data,now_data), thread_ts=message['ts'])

    # !進出點分析
    @app.message(re.compile(r"^!進出點分析\s+(.+)$"))
    def analyze_slock_point(message, say):
        msg_text = re.match(r"^!進出點分析\s+(.+)$", message['text']).group(1).strip()
        now_data = get_stock_info(msg_text)
        his_data = []        
        today = datetime.now()        
        for i in range(3):
            first_day_of_month = (today.replace(day=1) - timedelta(days=i*30)).strftime('%Y%m01')
            his_data.append(get_historical_data(msg_text,first_day_of_month))        
        say(analyze_stock_inoutpoint_xai(his_data,now_data), thread_ts=message['ts'])