import re
import requests
import time
import json
import threading
from datetime import datetime
from pymongo import MongoClient
from slack_sdk import WebClient
from ..AI_Service.xai  import analyze_stock as analyze_stock_xai 
from ..AI_Service.xai  import analyze_stock_inoutpoint as analyze_stock_inoutpoint_xai 

COMMANDS_HELP = [
    ("!查股 股票代碼", "查詢指定股票的即時資訊"),
    ("!技術分析 股票代碼", "查詢指定股票的技術分析"),
    ("!進出點分析 股票代碼", "查詢指定股票的進出點建議"),
]


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
        for i in range(3):
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


#取現價
def get_stock_info(stock_code):
    api_url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?json=1&delay=0&ex_ch=tse_{stock_code}.tw"
    response = requests.get(api_url)
    if response.status_code == 200:
        data = response.json()
        return format_stock_info(data)
    else:
        print(f"請求失敗，狀態碼：{response.status_code}")
        return "無法取得股票資訊"

def format_stock_info(data):
    if not data or 'msgArray' not in data or len(data['msgArray']) == 0:
        return "無法取得股票資訊。"

    stock_info = data["msgArray"][0]
    formatted_info = (
        f"公司名稱: {stock_info.get('nf', 'N/A')} ({stock_info.get('ch', 'N/A')})\n"
        f"最新成交價: {stock_info.get('z', 'N/A')} 新台幣\n"
        f"成交時間: {stock_info.get('t', 'N/A')} (當地時間)\n"
        f"今日開盤價: {stock_info.get('o', 'N/A')} 新台幣\n"
        f"最高價: {stock_info.get('h', 'N/A')} 新台幣\n"
        f"最低價: {stock_info.get('l', 'N/A')} 新台幣\n"
        f"昨日收盤價: {stock_info.get('y', 'N/A')} 新台幣\n"
        f"漲停價: {stock_info.get('u', 'N/A')} 新台幣\n"
        f"跌停價: {stock_info.get('w', 'N/A')} 新台幣\n"
        f"成交股數: {stock_info.get('v', 'N/A')} 股\n"
        f"委買價: {stock_info.get('b', 'N/A').replace('_', ', ')} 新台幣\n"
        f"委賣價: {stock_info.get('a', 'N/A').replace('_', ', ')} 新台幣\n"
    )
    return formatted_info

def get_historical_data(stock_code, date):
    historical_api_url = f"https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date={date}&stockNo={stock_code}&response=json"
    response = requests.get(historical_api_url)
    if response.status_code == 200:
        historical_data = response.json()
        return format_historical_data(historical_data)
    else:        
        return f"請求失敗，狀態碼：{response.status_code}"

def format_historical_data(data):
    try:
        if not data:
            return "無法取得歷史資料。"
        
        formatted_data = "歷史資料:\n"
        fields = data["fields"]
        for record in data["data"]:
            formatted_data += (
                f"日期: {record[0]}, "
                f"成交股數: {record[1]}, "
                f"成交金額: {record[2]}, "
                f"開盤價: {record[3]}, "
                f"最高價: {record[4]}, "
                f"最低價: {record[5]}, "
                f"收盤價: {record[6]}, "
                f"漲跌價差: {record[7]}, "
                f"成交筆數: {record[8]}\n"
            )
        return formatted_data
    except KeyError as e:
        return f"資料格式錯誤，缺少欄位: {e}"
    except Exception as e:
        return f"發生錯誤: {e}"