import requests
import json

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

#轉換現價格式
def format_stock_info(data):
    if not data:
        return "無法取得股票資訊。"
    
    stock_info = data["msgArray"][0]
    formatted_info = (
        f"公司名稱: {stock_info['nf']} ({stock_info['ch']})\n"
        f"最新成交價: {stock_info['z']} 新台幣\n"
        f"成交時間: {stock_info['t']} (當地時間)\n"
        f"今日開盤價: {stock_info['o']} 新台幣\n"
        f"最高價: {stock_info['h']} 新台幣\n"
        f"最低價: {stock_info['l']} 新台幣\n"
        f"昨日收盤價: {stock_info['y']} 新台幣\n"
        f"漲停價: {stock_info['u']} 新台幣\n"
        f"跌停價: {stock_info['w']} 新台幣\n"
        f"成交股數: {stock_info['v']} 股\n"
        f"委買價: {stock_info['b'].replace('_', ', ')} 新台幣\n"
        f"委賣價: {stock_info['a'].replace('_', ', ')} 新台幣\n"
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