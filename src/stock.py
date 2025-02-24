import requests
import json

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