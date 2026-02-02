import requests
import json
from datetime import datetime

def get_current_date():
    """取得目前的日期與時間。
    
    Returns:
        str: 格式化後的日期與時間字串
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

#取現價
def get_stock_info(stock_code: str):
    """取得股票即時資訊。
    
    Args:
        stock_code: 股票代碼 (例如: '2330')
    """
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

def get_historical_data(stock_code: str, date: str):
    """取得股票歷史資料。
    
    Args:
        stock_code: 股票代碼 (例如: '2330')
        date: 日期 (格式: 'YYYYMMDD')
    """
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

def get_crypto_prices():
    """取得 MAX 交易所的加密貨幣即時價格。"""
    url = "https://max-api.maicoin.com/api/v3/wallet/m/index_prices"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        
        # 抓出指定幣別的價格
        btc_usdt = data.get("btcusdt")
        btc_twd = data.get("btctwd")
        usdt_twd = data.get("usdttwd")
        bnb_twd = data.get("bnbtwd")

        # 組成易懂字串
        result = (
            f"MAX 交易所 幣價資訊：\n"
            f"BTC 對 USDT：{btc_usdt} 美元\n"
            f"BTC 對 TWD：{btc_twd} 台幣\n"
            f"USDT 對 TWD：{usdt_twd} 台幣\n"
            f"BNB 對 TWD：{bnb_twd} 台幣\n"
        )
        return result        
    else:
        return f"請求失敗，狀態碼：{response.status_code}"