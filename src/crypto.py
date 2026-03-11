import requests
import json
from datetime import datetime, timedelta

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

        # 組成易懂字串
        result = (
            f"MAX 交易所 幣價資訊：\n"
            f"BTC 對 USDT：{btc_usdt} 美元\n"
            f"BTC 對 TWD：{btc_twd} 台幣\n"
            f"USDT 對 TWD：{usdt_twd} 台幣\n"            
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
                        # 轉換為 UTC+8 時區
                        dt_utc8 = dt + timedelta(hours=8)
                        formatted_time = dt_utc8.strftime("%m-%d %H:%M")
                    else:
                        formatted_time = "N/A"
                except:
                    formatted_time = created_at[:16] if created_at else "N/A"
                
                result += (f"幣種:{symbol}|{order_type}|價格:{price:,.2f}|數量:{quantity}|時間:{formatted_time}\n")
            
            return result
            
        else:
            return f"API請求失敗，狀態碼：{response.status_code}"
            
    except requests.exceptions.RequestException as e:
        return f"網路請求錯誤：{e}"
    except Exception as e:
        return f"處理訂單資料時發生錯誤：{e}"

def get_trading_volume_stats():
    """取得交易成交量統計資料，計算各交易對的利潤統計。                
    """
    url = f"https://herry537.sytes.net/max_api/trading/orders?status=done"
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
                return f"目前沒有狀態為 done 的訂單"
            
            # 按交易對分組並計算利潤
            trading_pairs = {}
            total_profit = 0
            total_volume = 0
            
            for order in orders:
                symbol = order.get("symbol", "N/A")
                order_type = order.get("order_type")
                executed_price = float(order.get("executed_price", 0))
                executed_quantity = float(order.get("executed_quantity", 0))
                order_value = executed_price * executed_quantity
                
                if symbol not in trading_pairs:
                    trading_pairs[symbol] = {
                        'buy_orders': [],
                        'sell_orders': [],
                        'total_buy_value': 0,
                        'total_sell_value': 0,
                        'total_buy_quantity': 0,
                        'total_sell_quantity': 0,
                        'profit': 0
                    }
                
                # 累加總交易量
                total_volume += order_value
                
                if order_type == "buy":
                    trading_pairs[symbol]['buy_orders'].append({
                        'price': executed_price,
                        'quantity': executed_quantity,
                        'value': order_value
                    })
                    trading_pairs[symbol]['total_buy_value'] += order_value
                    trading_pairs[symbol]['total_buy_quantity'] += executed_quantity
                    
                elif order_type == "sell":
                    trading_pairs[symbol]['sell_orders'].append({
                        'price': executed_price,
                        'quantity': executed_quantity,
                        'value': order_value
                    })
                    trading_pairs[symbol]['total_sell_value'] += order_value
                    trading_pairs[symbol]['total_sell_quantity'] += executed_quantity
            
            # 計算各交易對的利潤（簡化計算：賣出總價值 - 買入總價值）
            for symbol, data in trading_pairs.items():
                pair_profit = data['total_sell_value'] - data['total_buy_value']
                data['profit'] = pair_profit
                total_profit += pair_profit
            
            # 格式化結果
            result = f"💰 **交易利潤統計** ({count}筆)\n\n"
            result += f"  總交易量：{total_volume:,.2f} \n"
            result += f"總利潤：{total_profit:,.2f} \n\n"
            
            # 按利潤排序顯示各交易對
            sorted_pairs = sorted(trading_pairs.items(), key=lambda x: x[1]['profit'], reverse=True)
            
            for symbol, data in sorted_pairs:
                profit_percentage = (data['profit'] / data['total_buy_value'] * 100) if data['total_buy_value'] > 0 else 0
                result += f"🪙 {symbol}: {data['profit']:+.2f}  ({profit_percentage:+.1f}%)\n"
            
            return result
            
        else:
            return f"API請求失敗，狀態碼：{response.status_code}"
            
    except requests.exceptions.RequestException as e:
        return f"網路請求錯誤：{e}"
    except Exception as e:
        return f"處理訂單資料時發生錯誤：{e}"