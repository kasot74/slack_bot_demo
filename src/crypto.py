import requests
import json
import concurrent.futures
from datetime import datetime, timedelta

def get_crypto_prices():
    """取得 MAX 交易所的加密貨幣即時價格。"""
    url = "https://max-api.maicoin.com/api/v3/tickers?markets[]=btcusdt&markets[]=btctwd&markets[]=maxtwd&markets[]=usdttwd"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        
        # 初始化價格變數
        btc_usdt = btc_twd = max_twd = usdt_twd = None
        
        # 從陣列中提取各市場價格
        for market_data in data:
            market = market_data.get("market")
            last_price = market_data.get("last")
            buy_price = market_data.get("buy") 
            sell_price = market_data.get("sell")
            vol = market_data.get("vol")
            
            if market == "btcusdt":
                btc_usdt = f"{float(last_price):,.2f} (買：{float(buy_price):,.2f} 賣：{float(sell_price):,.2f})"
            elif market == "btctwd":
                btc_twd = f"{float(last_price):,.0f} (買：{float(buy_price):,.0f} 賣：{float(sell_price):,.0f})"
            elif market == "maxtwd":
                max_twd = f"{float(last_price):,.4f} (買：{float(buy_price):,.4f} 賣：{float(sell_price):,.4f})"
            elif market == "usdttwd":
                usdt_twd = f"{float(last_price):,.3f} (買：{float(buy_price):,.3f} 賣：{float(sell_price):,.3f})"

        # 組成易懂字串
        result = f"MAX 交易所 幣價資訊：\n"
        if btc_usdt:
            result += f"BTC/USDT：{btc_usdt}\n"
        if btc_twd:
            result += f"BTC/TWD：{btc_twd}\n"
        if max_twd:
            result += f"MAX/TWD：{max_twd}\n"
        if usdt_twd:
            result += f"USDT/TWD：{usdt_twd}\n"
            
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
                symbol = order.get("symbol", "N/A").upper()  # 統一轉為大寫
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
                
                result += (f"幣種:{symbol}|{order_type}|價格:{price:,.2f}|數量:{quantity}|時間:{formatted_time}\n")
            
            return result
            
        else:
            return f"API請求失敗，狀態碼：{response.status_code}"
            
    except requests.exceptions.RequestException as e:
        return f"網路請求錯誤：{e}"
    except Exception as e:
        return f"處理訂單資料時發生錯誤：{e}"

def get_trading_volume_stats():
    """取得交易成交量統計資料，計算各交易對的利潤統計，並包含待成交訂單的假設利潤。                
    """
    headers = {
        'accept': 'application/json'
    }
    
    try:
        # 並發請求 done 和 wait 訂單
        done_url = f"https://herry537.sytes.net/max_api/trading/orders?status=done"
        wait_url = f"https://herry537.sytes.net/max_api/trading/orders?status=wait"
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            done_future = executor.submit(requests.get, done_url, headers=headers, timeout=10)
            wait_future = executor.submit(requests.get, wait_url, headers=headers, timeout=10)
            
            done_response = done_future.result(timeout=15)
            wait_response = wait_future.result(timeout=15)
        
        if done_response.status_code != 200:
            return f"API請求失敗，狀態碼：{done_response.status_code}"
            
        done_data = done_response.json()
        done_orders = done_data.get("orders", [])
        done_count = done_data.get("count", 0)
        
        if not done_orders:
            return f"目前沒有狀態為 done 的訂單"
        
        FEE_RATE = 0.0004  # 每次交易手續費 0.04%
        
        # ===== 第一部分：已成交訂單分析 =====
        trading_pairs = {}
        total_profit = 0
        total_volume = 0
        total_fee = 0
        
        for order in done_orders:
            symbol = order.get("symbol", "N/A").upper()
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
                    'profit': 0,
                    'total_fee': 0,
                    'hypothetical_profit': 0,
                    'hypothetical_fee': 0,
                    'wait_buy_count': 0,
                    'wait_sell_count': 0
                }
            
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
        
        # 計算已成交訂單的利潤
        for symbol, data in trading_pairs.items():
            pair_fee = (data['total_buy_value'] + data['total_sell_value']) * FEE_RATE
            pair_profit = data['total_sell_value'] - data['total_buy_value'] - pair_fee
            data['profit'] = pair_profit
            data['total_fee'] = pair_fee
            total_profit += pair_profit
            total_fee += pair_fee
        
        # ===== 第二部分：待成交訂單假設分析 =====
        wait_orders = []
        wait_count = 0
        hypothetical_total_profit = 0
        hypothetical_total_fee = 0
        
        if wait_response.status_code == 200:
            wait_data = wait_response.json()
            wait_orders = wait_data.get("orders", [])
            wait_count = wait_data.get("count", 0)
            
            # 按交易對分組 wait 訂單
            wait_pairs = {}
            for order in wait_orders:
                symbol = order.get("symbol", "N/A").upper()
                order_type = order.get("order_type")
                price = float(order.get("price", 0))
                quantity = float(order.get("quantity", 0))
                created_at = order.get("created_at", "")
                
                if symbol not in wait_pairs:
                    wait_pairs[symbol] = {
                        'buy_orders': [],
                        'sell_orders': []
                    }
                
                if order_type == "buy":
                    wait_pairs[symbol]['buy_orders'].append({
                        'price': price,
                        'quantity': quantity,
                        'created_at': created_at
                    })
                elif order_type == "sell":
                    wait_pairs[symbol]['sell_orders'].append({
                        'price': price,
                        'quantity': quantity,
                        'created_at': created_at
                    })
            
            # 計算假設 wait 訂單成交後的利潤
            for symbol, wait_data_pair in wait_pairs.items():
                # 如果交易對不在 trading_pairs 中，則創建新條目
                if symbol not in trading_pairs:
                    trading_pairs[symbol] = {
                        'buy_orders': [],
                        'sell_orders': [],
                        'total_buy_value': 0,
                        'total_sell_value': 0,
                        'total_buy_quantity': 0,
                        'total_sell_quantity': 0,
                        'profit': 0,
                        'total_fee': 0,
                        'hypothetical_profit': 0,
                        'hypothetical_fee': 0,
                        'wait_buy_count': 0,
                        'wait_sell_count': 0
                    }
                
                buy_orders = sorted(wait_data_pair['buy_orders'], key=lambda x: x['created_at'])
                sell_orders = sorted(wait_data_pair['sell_orders'], key=lambda x: x['created_at'])
                
                # 配對 wait 訂單
                buy_idx = 0
                sell_idx = 0
                pair_profit = 0
                pair_fee = 0
                matched_count = 0
                
                while buy_idx < len(buy_orders) and sell_idx < len(sell_orders):
                    buy_order = buy_orders[buy_idx]
                    sell_order = sell_orders[sell_idx]
                    
                    match_qty = min(buy_order['quantity'], sell_order['quantity'])
                    buy_cost = buy_order['price'] * match_qty
                    sell_revenue = sell_order['price'] * match_qty
                    match_fee = (buy_cost + sell_revenue) * FEE_RATE
                    match_profit = sell_revenue - buy_cost - match_fee
                    
                    pair_profit += match_profit
                    pair_fee += match_fee
                    matched_count += 1
                    
                    buy_order['quantity'] -= match_qty
                    sell_order['quantity'] -= match_qty
                    
                    if buy_order['quantity'] == 0:
                        buy_idx += 1
                    if sell_order['quantity'] == 0:
                        sell_idx += 1
                
                trading_pairs[symbol]['hypothetical_profit'] = pair_profit
                trading_pairs[symbol]['hypothetical_fee'] = pair_fee
                trading_pairs[symbol]['wait_buy_count'] = len(wait_data_pair['buy_orders'])
                trading_pairs[symbol]['wait_sell_count'] = len(wait_data_pair['sell_orders'])
                hypothetical_total_profit += pair_profit
                hypothetical_total_fee += pair_fee
        
        # 格式化結果
        result = f"💰 **交易利潤統計** (已成交:{done_count}筆 | 待成交:{wait_count}筆)\n\n"
        result += f"━━━━ **已成交訂單** ━━━━\n"
        result += f"  總交易量：{total_volume:,.2f} \n"
        result += f"總手續費：-{total_fee:,.2f} (0.04%/次)\n"
        result += f"總利潤：{total_profit:,.2f} \n\n"
        
        # 按利潤排序顯示各交易對的已成交利潤
        sorted_pairs = sorted(trading_pairs.items(), key=lambda x: x[1]['profit'], reverse=True)
        
        for symbol, data in sorted_pairs:
            profit_percentage = (data['profit'] / data['total_buy_value'] * 100) if data['total_buy_value'] > 0 else 0
            wait_info = ""
            if data['wait_buy_count'] > 0 or data['wait_sell_count'] > 0:
                wait_info = f" [待:{data['wait_buy_count']}買|{data['wait_sell_count']}賣]"
            result += f"🪙 {symbol}: {data['profit']:+.2f} ({profit_percentage:+.1f}%){wait_info}\n"
        
        # 假設利潤統計
        if wait_count > 0:
            result += f"\n━━━━ **假設待成交訂單成交後** ━━━━\n"
            result += f"假設手續費：-{hypothetical_total_fee:,.2f}\n"
            result += f"假設額外利潤：{hypothetical_total_profit:+,.2f}\n"
            result += f"總計潛在利潤：{total_profit + hypothetical_total_profit:+,.2f}\n\n"
            
            # 顯示有待成交訂單的交易對
            for symbol, data in sorted_pairs:
                if data['wait_buy_count'] > 0 or data['wait_sell_count'] > 0:
                    if data['hypothetical_profit'] != 0:
                        hypo_percentage = (data['hypothetical_profit'] / max(data['total_buy_value'], 1) * 100)
                        result += f"🪙 {symbol}: +{data['hypothetical_profit']:,.2f} ({hypo_percentage:+.1f}%)\n"
        
        return result
        
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
    symbol = symbol.upper()  # 統一轉為大寫
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
            total_ask_depth = sum([qty for _, qty in asks_data])
            total_bid_depth = sum([qty for _, qty in bids_data])
            
            # 尋找大單 (數量 > 平均值的 2.5倍)
            avg_ask_qty = sum([qty for _, qty in asks_data]) / len(asks_data) if len(asks_data) > 0 else 0
            avg_bid_qty = sum([qty for _, qty in bids_data]) / len(bids_data) if len(bids_data) > 0 else 0
            
            large_asks = [(price, qty) for price, qty in asks_data if qty > avg_ask_qty * 2.5]
            large_bids = [(price, qty) for price, qty in bids_data if qty > avg_bid_qty * 2.5]
            
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
            result += f"總深度(全部)：賣{total_ask_depth:,.0f} | 買{total_bid_depth:,.0f}\n"
            result += f"流動性比率：{liquidity_ratio:.3f}\n\n"
            
            # 大單分析
            if large_asks or large_bids:
                result += f"🎯 **掛單大單警報** (平均量2.5倍)\n"
                if large_asks:
                    result += f"💸 **大賣單** ({len(large_asks)}筆):\n"
                    for price, qty in large_asks[:5]:  # 顯示前5筆
                        result += f"  {price:,.4f} @ {qty:,.2f} = {price*qty:,.0f}\n"
                if large_bids:
                    result += f"🔥 **大買單** ({len(large_bids)}筆):\n"
                    for price, qty in large_bids[:5]:  # 顯示前5筆
                        result += f"  {price:,.4f} @ {qty:,.2f} = {price*qty:,.0f}\n"
                result += "\n"
            else:
                result += f"🟢 **掛單狀況**: 無大單異常\n\n"
            
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


def get_recent_trades(symbol="BTCTWD", limit=15):
    """取得指定交易對的近期成交記錄。
    
    Args:
        symbol (str): 交易對符號，如 BTCTWD
        limit (int): 顯示的交易記錄數量，預設15筆
        
    Returns:
        str: 格式化的近期成交報告
    """
    symbol = symbol.upper()  # 統一轉為大寫
    url = f"https://herry537.sytes.net/max_api/trading/ordertrades/{symbol}"
    headers = {
        'accept': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if not data.get("success"):
                return f"API回傳錯誤：無法獲取 {symbol} 的成交數據"
            
            trades = data.get("order_trades", [])
            
            if not trades:
                return f"{symbol} 目前沒有近期成交記錄"
            
            # 計算統計數據
            total_volume = 0
            total_funds = 0
            buy_trades = []
            sell_trades = []
            price_list = []
            
            for trade in trades[:limit]:
                price = float(trade.get("price", 0))
                volume = float(trade.get("volume", 0))
                funds = float(trade.get("funds", 0))
                side = trade.get("side")
                
                total_volume += volume
                total_funds += funds
                price_list.append(price)
                
                if side == "bid":  # 買單
                    buy_trades.append(trade)
                else:  # ask - 賣單
                    sell_trades.append(trade)
            
            # 計算價格統計
            if price_list:
                avg_price = sum(price_list) / len(price_list)
                max_price = max(price_list)
                min_price = min(price_list)
                price_range = max_price - min_price
                price_range_percent = (price_range / min_price) * 100 if min_price > 0 else 0
            else:
                avg_price = max_price = min_price = 0
                price_range_percent = 0
            
            # 格式化結果
            result = f"🔄 **{symbol} 近期成交記錄** (最新{limit}筆)\n\n"
            result += f"📊 **成交統計：**\n"
            result += f"總成交量：{total_volume:.6f}\n"
            result += f"總成交額：{total_funds:,.0f}\n"
            result += f"平均價格：{avg_price:,.2f}\n"
            result += f"價格區間：{min_price:,.2f} ~ {max_price:,.2f}\n"
            result += f"波動幅度：{price_range_percent:.2f}%\n\n"
            
            result += f"📈 **買賣分析：**\n"
            result += f"買單數量：{len(buy_trades)}筆\n"
            result += f"賣單數量：{len(sell_trades)}筆\n"
            
            # 買賣力道分析
            if buy_trades and sell_trades:
                buy_ratio = len(buy_trades) / len(trades[:limit]) * 100
                result += f"買氣強度：{buy_ratio:.1f}%\n\n"
            else:
                result += "\n"
            
            # 趨勢分析 - 比較最近5筆交易的價格趨勢
            trend_analysis = ""
            if len(trades) >= 5:
                recent_prices = [float(trade.get("price", 0)) for trade in trades[:5]]
                first_price = recent_prices[-1]  # 最早的價格
                last_price = recent_prices[0]    # 最新的價格
                
                price_change = last_price - first_price
                price_change_percent = (price_change / first_price) * 100 if first_price > 0 else 0
                
                # 計算連續上升/下降的數量
                up_count = 0
                down_count = 0
                for i in range(len(recent_prices)-1):
                    if recent_prices[i] > recent_prices[i+1]:
                        up_count += 1
                    elif recent_prices[i] < recent_prices[i+1]:
                        down_count += 1
                
                # 判斷趨勢
                if price_change_percent > 0.1:
                    trend = "🔥 上升趨勢"
                    trend_emoji = "📈"
                elif price_change_percent < -0.1:
                    trend = "❄️ 下跌趨勢"
                    trend_emoji = "📉"
                else:
                    trend = "📊 盤整趨勢"
                    trend_emoji = "🔄"
                
                result += f"🎯 **趨勢分析：**\n"
                result += f"{trend_emoji} {trend}\n"
                result += f"價格變化：{price_change:+,.1f} ({price_change_percent:+.2f}%)\n"
                result += f"最新價格：{last_price:,.2f}\n\n"
            
            # 顯示簡化的成交記錄 (只顯示最新5筆)
            display_limit = min(5, len(trades))
            result += f"📋 **最新{display_limit}筆成交：**\n"
            
            for i, trade in enumerate(trades[:display_limit]):
                try:
                    # 轉換時間戳
                    timestamp = int(trade.get("created_at", 0))
                    dt = datetime.fromtimestamp(timestamp / 1000)  # 毫秒轉秒                    
                    formatted_time = dt.strftime("%H:%M")
                except:
                    formatted_time = "N/A"
                
                price = float(trade.get("price", 0))
                volume = float(trade.get("volume", 0))
                funds = float(trade.get("funds", 0))
                side = "買" if trade.get("side") == "bid" else "賣"
                side_emoji = "🟢" if side == "買" else "🔴"
                
                result += f"{formatted_time} {side_emoji}{side} {price:,.1f} @ {volume:.4f} = {funds:,.0f}\n"
            
            return result
            
        else:
            return f"近期成交API請求失敗，狀態碼：{response.status_code}"
            
    except requests.exceptions.RequestException as e:
        return f"網路請求錯誤：{e}"
    except Exception as e:
        return f"處理成交數據時發生錯誤：{e}"


def get_market_analysis(symbol="BTCTWD"):
    """綜合分析訂單深度與成交記錄，提供全面的市場分析。
    
    Args:
        symbol (str): 交易對符號，如 BTCTWD
        
    Returns:
        str: 格式化的綜合市場分析報告
    """
    try:
        symbol = symbol.upper()  # 統一轉為大寫
        # 同時獲取訂單深度和成交記錄數據
        depth_url = f"https://herry537.sytes.net/max_api/trading/orderdepth/{symbol}"
        trades_url = f"https://herry537.sytes.net/max_api/trading/ordertrades/{symbol}"
        headers = {'accept': 'application/json'}
        
        # 並發請求兩個API
        with concurrent.futures.ThreadPoolExecutor() as executor:
            depth_future = executor.submit(requests.get, depth_url, headers=headers, timeout=10)
            trades_future = executor.submit(requests.get, trades_url, headers=headers, timeout=10)
            
            try:
                depth_response = depth_future.result(timeout=15)
                trades_response = trades_future.result(timeout=15)
            except concurrent.futures.TimeoutError:
                return f"{symbol} API請求超時，請稍後再試"
            except Exception as e:
                return f"{symbol} API請求發生錯誤：{e}"
        
        if depth_response.status_code != 200 or trades_response.status_code != 200:
            return f"API請求失敗，深度:{depth_response.status_code}, 成交:{trades_response.status_code}"
        
        depth_data = depth_response.json()
        trades_data = trades_response.json()
        
        if not depth_data.get("success") or not trades_data.get("success"):
            return f"無法獲取 {symbol} 的完整市場數據"
        
        # 解析訂單深度數據
        order_depth = depth_data.get("order_depth", {})
        asks = order_depth.get("asks", [])
        bids = order_depth.get("bids", [])
        
        if not asks or not bids:
            return f"{symbol} 訂單簿數據不完整"
        
        # 安全地轉換訂單數據
        asks_data = []
        for price, qty in asks:
            try:
                asks_data.append([float(price), float(qty)])
            except (ValueError, TypeError):
                continue
                
        bids_data = []
        for price, qty in bids:
            try:
                bids_data.append([float(price), float(qty)])
            except (ValueError, TypeError):
                continue
                
        if not asks_data or not bids_data:
            return f"{symbol} 訂單數據格式錯誤"
        
        best_ask = asks_data[0][0]
        best_bid = bids_data[0][0]
        spread = best_ask - best_bid
        
        # 解析成交記錄數據
        trades = trades_data.get("order_trades", [])
        if not trades:
            return f"{symbol} 成交記錄數據不完整"
                        
        # === 綜合分析 ===                
                                
        #買賣力道分析
        buy_trades = [t for t in trades if t.get("side") == "bid"]
        sell_trades = [t for t in trades if t.get("side") == "ask"]
        
        # 安全地處理數據轉換
        buy_volume = 0
        for t in buy_trades:
            vol = t.get("volume")
            if vol is not None:
                try:
                    buy_volume += float(vol)
                except (ValueError, TypeError):
                    continue
                    
        sell_volume = 0
        for t in sell_trades:
            vol = t.get("volume")
            if vol is not None:
                try:
                    sell_volume += float(vol)
                except (ValueError, TypeError):
                    continue
                                
        #關鍵價位分析
        resistance_levels = []
        support_levels = []
        
        # 計算全部訂單的平均掛單量
        avg_ask_all = sum([qty for _, qty in asks_data]) / len(asks_data) if len(asks_data) > 0 else 0
        avg_bid_all = sum([qty for _, qty in bids_data]) / len(bids_data) if len(bids_data) > 0 else 0
        
        for price, qty in asks_data:  
            if qty > avg_ask_all * 2:  # 大於全部平均掛單量的2倍
                resistance_levels.append((price, qty))
        
        for price, qty in bids_data:  
            if qty > avg_bid_all * 2:  # 大於全部平均掛單量的2倍
                support_levels.append((price, qty))
        
        # === 格式化結果 ===
        result = f"🎯 **{symbol} 綜合市場分析**\n\n"
        
        # 市場概況
        result += f"💎 **市場概況：**\n"        
        result += f"最佳買價：{best_bid:,.4f} | 最佳賣價：{best_ask:,.4f} | 價差：{spread:,.4f}\n\n"        
        # 買賣力道對比
        if buy_volume + sell_volume > 0:
            buy_pressure = buy_volume / (buy_volume + sell_volume) * 100
            pressure_status = "買盤強勢" if buy_pressure > 60 else "賣盤強勢" if buy_pressure < 40 else "買賣均衡"
            result += f"買賣力道：{pressure_status} ({buy_pressure:.1f}%)\n\n"
        else:
            result += "\n"
                
        # 關鍵價位
        if resistance_levels or support_levels:
            result += f"🎯 **關鍵價位：**\n"
            if resistance_levels:
                result += f"阻力位：{resistance_levels[0][0]:,.2f} (掛量:{resistance_levels[0][1]:.2f})\n"
            if support_levels:
                result += f"支撐位：{support_levels[0][0]:,.2f} (掛量:{support_levels[0][1]:.2f})\n"
            result += "\n"
                        
        return result
        
    except Exception as e:
        return f"綜合市場分析時發生錯誤：{e}"
