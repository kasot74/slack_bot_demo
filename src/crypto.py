import requests
import json
from datetime import datetime

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

def get_pending_orders(status="wait"):
    """取得交易訂單資料。"""
    url = f"https://herry537.sytes.net/max_api/trading/orders?status={status}"
    headers = {
        'accept': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            orders = data.get("orders", [])
            count = data.get("count", 0)
            
            if not orders:
                return f"目前沒有狀態為 {status} 的訂單"
            
            # 格式化訂單資訊
            result = f"📋 **狀態為 {status} 的訂單** (共 {count} 筆)\n\n"
            
            for order in orders:
                order_id = order.get("id", "N/A")
                symbol = order.get("symbol", "N/A")
                order_type = "買單" if order.get("order_type") == "buy" else "賣單"
                price = order.get("price", 0)
                quantity = order.get("quantity", 0)
                created_at = order.get("created_at", "")
                
                # 格式化時間
                try:
                    if created_at:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        formatted_time = dt.strftime("%m-%d %H:%M")
                    else:
                        formatted_time = "N/A"
                except:
                    formatted_time = created_at[:16] if created_at else "N/A"
                
                result += (
                    f"訂單 {order_id}**\n"
                    f"幣種: {symbol} | {order_type}\n"
                    f"價格: {price:,.0f} | 數量: {quantity}\n"
                    f"時間: {formatted_time}\n\n"
                )
            
            return result
            
        else:
            return f"API請求失敗，狀態碼：{response.status_code}"
            
    except requests.exceptions.RequestException as e:
        return f"網路請求錯誤：{e}"
    except Exception as e:
        return f"處理訂單資料時發生錯誤：{e}"