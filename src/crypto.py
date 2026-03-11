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


def get_order_depth_analysis(symbol="BTCTWD"):
    """分析指定交易對的訂單簿深度圖。
    
    Args:
        symbol (str): 交易對符號，如 BTCTWD
        
    Returns:
        str: 格式化的深度分析報告
    """
    url = f"https://herry537.sytes.net/max_api/trading/orderdepth/{symbol}"
    headers = {
        'accept': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if not data.get("success"):
                return f"API回傳錯誤：無法獲取 {symbol} 的訂單簿數據"
            
            order_depth = data.get("order_depth", {})
            asks = order_depth.get("asks", [])
            bids = order_depth.get("bids", [])
            
            if not asks or not bids:
                return f"{symbol} 訂單簿數據不完整"
            
            # 轉換數據格式
            asks_data = [[float(price), float(qty)] for price, qty in asks]
            bids_data = [[float(price), float(qty)] for price, qty in bids]
            
            # 基本價格資訊
            best_ask = asks_data[0][0]  # 最佳賣價
            best_bid = bids_data[0][0]  # 最佳買價
            spread = best_ask - best_bid
            spread_percentage = (spread / best_bid) * 100 if best_bid > 0 else 0
            
            # 計算深度統計
            def calculate_depth_stats(orders, levels=10):
                total_qty = 0
                total_value = 0
                for i, (price, qty) in enumerate(orders[:levels]):
                    total_qty += qty
                    total_value += price * qty
                avg_price = total_value / total_qty if total_qty > 0 else 0
                return total_qty, total_value, avg_price
            
            # 買賣單深度統計
            ask_qty_10, ask_value_10, ask_avg_10 = calculate_depth_stats(asks_data, 10)
            bid_qty_10, bid_value_10, bid_avg_10 = calculate_depth_stats(bids_data, 10)
            
            ask_qty_20, ask_value_20, ask_avg_20 = calculate_depth_stats(asks_data, 20)
            bid_qty_20, bid_value_20, bid_avg_20 = calculate_depth_stats(bids_data, 20)
            
            # 計算流動性指標
            total_ask_depth = sum([qty for _, qty in asks_data[:50]])
            total_bid_depth = sum([qty for _, qty in bids_data[:50]])
            
            # 尋找大單 (數量 > 平均值的 3倍)
            avg_ask_qty = sum([qty for _, qty in asks_data[:20]]) / 20
            avg_bid_qty = sum([qty for _, qty in bids_data[:20]]) / 20
            
            large_asks = [(price, qty) for price, qty in asks_data[:20] if qty > avg_ask_qty * 3]
            large_bids = [(price, qty) for price, qty in bids_data[:20] if qty > avg_bid_qty * 3]
            
            # 格式化結果
            result = f"📊 **{symbol} 訂單簿深度分析**\n\n"
            result += f"💰 **價格資訊：**\n"
            result += f"最佳買價：{best_bid:,.4f}\n"
            result += f"最佳賣價：{best_ask:,.4f}\n"
            result += f"價差：{spread:,.4f} ({spread_percentage:.3f}%)\n\n"
            
            result += f"📈 **深度統計 (前10檔)：**\n"
            result += f"賣單量：{ask_qty_10:,.2f} | 平均:{ask_avg_10:,.4f}\n"
            result += f"買單量：{bid_qty_10:,.2f} | 平均:{bid_avg_10:,.4f}\n"
            result += f"買賣比：{(bid_qty_10/ask_qty_10):,.2f}\n\n"
            
            result += f"📊 **深度統計 (前20檔)：**\n"
            result += f"賣單量：{ask_qty_20:,.2f} | 價值:{ask_value_20:,.0f}\n"
            result += f"買單量：{bid_qty_20:,.2f} | 價值:{bid_value_20:,.0f}\n\n"
            
            # 流動性分析
            liquidity_ratio = bid_value_20 / ask_value_20 if ask_value_20 > 0 else 0
            result += f"🌊 **流動性分析：**\n"
            result += f"總深度(50檔)：賣{total_ask_depth:,.0f} | 買{total_bid_depth:,.0f}\n"
            result += f"流動性比率：{liquidity_ratio:.3f}\n\n"
            
            # 大單分析
            if large_asks or large_bids:
                result += f"🎯 **大單警報：**\n"
                if large_asks:
                    result += f"大賣單：\n"
                    for price, qty in large_asks[:3]:
                        result += f"  {price:,.4f} @ {qty:,.1f}\n"
                if large_bids:
                    result += f"大買單：\n"
                    for price, qty in large_bids[:3]:
                        result += f"  {price:,.4f} @ {qty:,.1f}\n"
                result += "\n"
            
            # 支撐阻力分析
            price_range = best_ask - best_bid
            support_level = best_bid - (price_range * 2)
            resistance_level = best_ask + (price_range * 2)
            
            result += f"📍 **技術分析：**\n"
            result += f"支撐位：{support_level:,.4f}\n"
            result += f"阻力位：{resistance_level:,.4f}\n"
            
            return result
            
        else:
            return f"訂單簿API請求失敗，狀態碼：{response.status_code}"
            
    except requests.exceptions.RequestException as e:
        return f"網路請求錯誤：{e}"
    except Exception as e:
        return f"處理訂單簿數據時發生錯誤：{e}"