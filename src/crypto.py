import requests
import json
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
            
            # 尋找大單 (數量 > 平均值的 2.5倍)
            avg_ask_qty = sum([qty for _, qty in asks_data[:20]]) / 20
            avg_bid_qty = sum([qty for _, qty in bids_data[:20]]) / 20
            
            large_asks = [(price, qty) for price, qty in asks_data[:20] if qty > avg_ask_qty * 2.5]
            large_bids = [(price, qty) for price, qty in bids_data[:20] if qty > avg_bid_qty * 2.5]
            
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
        # 同時獲取訂單深度和成交記錄數據
        depth_url = f"https://herry537.sytes.net/max_api/trading/orderdepth/{symbol}"
        trades_url = f"https://herry537.sytes.net/max_api/trading/ordertrades/{symbol}"
        headers = {'accept': 'application/json'}
        
        # 並發請求兩個API
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            depth_future = executor.submit(requests.get, depth_url, headers=headers, timeout=10)
            trades_future = executor.submit(requests.get, trades_url, headers=headers, timeout=10)
            
            depth_response = depth_future.result()
            trades_response = trades_future.result()
        
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
        
        asks_data = [[float(price), float(qty)] for price, qty in asks[:20]]
        bids_data = [[float(price), float(qty)] for price, qty in bids[:20]]
        
        best_ask = asks_data[0][0]
        best_bid = bids_data[0][0]
        spread = best_ask - best_bid
        
        # 解析成交記錄數據
        trades = trades_data.get("order_trades", [])
        if not trades:
            return f"{symbol} 成交記錄數據不完整"
        
        recent_trades = trades[:20]
        
        # === 綜合分析 ===
        
        # 1. 成交價格vs訂單簿價格分析
        recent_prices = [float(trade.get("price", 0)) for trade in recent_trades[:5]]
        latest_price = recent_prices[0] if recent_prices else 0
        
        price_position = ""
        if latest_price > best_ask:
            price_position = "突破賣壓"
        elif latest_price < best_bid:
            price_position = "跌破支撐" 
        else:
            price_position = "區間整理"
        
        # 2. 流動性分析
        ask_liquidity = sum([qty for _, qty in asks_data[:10]])
        bid_liquidity = sum([qty for _, qty in bids_data[:10]])
        liquidity_ratio = bid_liquidity / ask_liquidity if ask_liquidity > 0 else 0
        
        # 3. 成交量vs深度對比
        recent_volume = sum([float(trade.get("volume", 0)) for trade in recent_trades[:10]])
        
        # 4. 買賣力道分析
        buy_trades = [t for t in recent_trades[:15] if t.get("side") == "bid"]
        sell_trades = [t for t in recent_trades[:15] if t.get("side") == "ask"]
        buy_volume = sum([float(t.get("volume", 0)) for t in buy_trades])
        sell_volume = sum([float(t.get("volume", 0)) for t in sell_trades])
        
        # 5. 大單檢測
        avg_trade_size = recent_volume / len(recent_trades[:10]) if recent_trades else 0
        large_trades = [t for t in recent_trades[:10] if float(t.get("volume", 0)) > avg_trade_size * 2.5]
        
        # 6. 趨勢分析
        if len(recent_prices) >= 5:
            price_trend = recent_prices[0] - recent_prices[4]
            trend_strength = abs(price_trend / recent_prices[4] * 100) if recent_prices[4] > 0 else 0
        else:
            price_trend = 0
            trend_strength = 0
        
        # 7. 關鍵價位分析
        resistance_levels = []
        support_levels = []
        
        for price, qty in asks_data[:5]:
            if qty > ask_liquidity / 20:  # 大於平均掛單量
                resistance_levels.append((price, qty))
        
        for price, qty in bids_data[:5]:
            if qty > bid_liquidity / 20:
                support_levels.append((price, qty))
        
        # === 格式化結果 ===
        result = f"🎯 **{symbol} 綜合市場分析**\n\n"
        
        # 市場概況
        result += f"💎 **市場概況：**\n"
        result += f"最新成交：{latest_price:,.2f}\n"
        result += f"價格位置：{price_position}\n"
        result += f"買賣價差：{spread:,.2f} ({spread/best_bid*100:.3f}%)\n\n"
        
        # 流動性分析
        liquidity_status = "充足" if liquidity_ratio > 0.8 else "偏緊" if liquidity_ratio > 0.5 else "緊張"
        result += f"💧 **流動性分析：**\n"
        result += f"買盤深度：{bid_liquidity:,.2f}\n"
        result += f"賣盤深度：{ask_liquidity:,.2f}\n"
        result += f"流動性狀況：{liquidity_status} ({liquidity_ratio:.2f})\n\n"
        
        # 交易活躍度
        current_time = datetime.now()
        five_minutes_ago = current_time - timedelta(minutes=5)
        
        # 計算5分鐘內的交易數量
        recent_5min_trades = 0
        analysis_trades = trades
        five_min_trade_details = []  # 儲存5分鐘內的交易詳情
        
        for trade in analysis_trades:
            try:
                timestamp = int(trade.get("created_at", 0))
                trade_time = datetime.fromtimestamp(timestamp / 1000)  # 毫秒轉秒                
                
                if trade_time >= five_minutes_ago:
                    recent_5min_trades += 1
                    # 收集交易詳情
                    five_min_trade_details.append({
                        'time': trade_time,
                        'price': float(trade.get("price", 0)),
                        'volume': float(trade.get("volume", 0)),
                        'side': trade.get("side")
                    })
            except:
                continue
        
        # 計算活躍度比重
        activity_ratio = recent_5min_trades / len(analysis_trades) if len(analysis_trades) > 0 else 0
        
        # 根據比重判斷活躍度等級
        if activity_ratio >= 0.7:  # 70%以上的交易在5分鐘內
            activity_level = "高"
            activity_desc = "🔥 市場非常活躍"
        elif activity_ratio >= 0.4:  # 40-70%的交易在5分鐘內  
            activity_level = "中"
            activity_desc = "📈 市場適度活躍"
        elif activity_ratio >= 0.2:  # 20-40%的交易在5分鐘內
            activity_level = "低"
            activity_desc = "📊 市場活躍度偏低"
        else:  # 少於20%的交易在5分鐘內
            activity_level = "極低"
            activity_desc = "💤 市場交易冷清"
        
        result += f"⚡ **交易活躍度：{activity_level}**\n"
        result += f"{activity_desc}\n"        
                
        time_range = f"{five_minutes_ago.strftime('%m-%d %H:%M:%S')} ~ {current_time.strftime('%m-%d %H:%M:%S')}"
        
        result += f"時間範圍：{time_range}\n"
        result += f"5分鐘內：{recent_5min_trades}筆 ({activity_ratio*100:.1f}%)\n"
        result += f"總成交量：{recent_volume:.6f}\n"
        
        # 顯示5分鐘內的交易詳情
        if five_min_trade_details:
            result += f"\n📋 **5分鐘內成交詳情** (共 {len(five_min_trade_details)} 筆)：\n"
            # 按時間排序 (最新的在前)
            five_min_trade_details.sort(key=lambda x: x['time'], reverse=True)
            
            for trade_detail in five_min_trade_details[:10]:  # 只顯示最新10筆
                trade_time_str = trade_detail['time'].strftime("%H:%M:%S")
                price = trade_detail['price']
                volume = trade_detail['volume']
                side = "🟢買" if trade_detail['side'] == "bid" else "🔴賣"
                
                result += f"{trade_time_str} {side} {price:,.1f} @ {volume:.6f} = {price*volume:,.0f}\n"
            
            if len(five_min_trade_details) > 10:
                result += f"... 另有 {len(five_min_trade_details)-10} 筆交易\n"
            
            result += "\n"
        
        # 買賣力道對比
        if buy_volume + sell_volume > 0:
            buy_pressure = buy_volume / (buy_volume + sell_volume) * 100
            pressure_status = "買盤強勢" if buy_pressure > 60 else "賣盤強勢" if buy_pressure < 40 else "買賣均衡"
            result += f"買賣力道：{pressure_status} ({buy_pressure:.1f}%)\n\n"
        else:
            result += "\n"
        
        # 趨勢分析
        if trend_strength > 0.2:
            trend_desc = "🔥強勢上漲" if price_trend > 0 else "❄️強勢下跌"
        elif trend_strength > 0.05:
            trend_desc = "📈溫和上漲" if price_trend > 0 else "📉溫和下跌"
        else:
            trend_desc = "📊震盪整理"
        
        result += f"📊 **趨勢判斷：{trend_desc}**\n"
        result += f"趨勢強度：{trend_strength:.2f}%\n\n"
        
        # 關鍵價位
        if resistance_levels or support_levels:
            result += f"🎯 **關鍵價位：**\n"
            if resistance_levels:
                result += f"阻力位：{resistance_levels[0][0]:,.2f} (掛量:{resistance_levels[0][1]:.2f})\n"
            if support_levels:
                result += f"支撐位：{support_levels[0][0]:,.2f} (掛量:{support_levels[0][1]:.2f})\n"
            result += "\n"
        
        # 交易建議
        if price_position == "突破賣壓" and buy_pressure > 55:
            advice = "🚀 考慮追漲，注意風控"
        elif price_position == "跌破支撐" and buy_pressure < 45:
            advice = "⚠️ 謹慎操作，關注支撐"
        elif liquidity_status == "緊張":
            advice = "🔍 流動性不足，小心滑價"
        elif trend_desc.__contains__("震盪"):
            advice = "⏳ 震盪整理，等待方向"
        else:
            advice = "📖 持續觀察，順勢而為"
        
        result += f"💡 **交易建議：{advice}**\n"
        
        # 大單提醒
        if large_trades:
            result += f"\n🚨 **成交大單詳情** ( {len(large_trades)} 筆)\n"
            for trade in large_trades:
                try:
                    timestamp = int(trade.get("created_at", 0))
                    dt = datetime.fromtimestamp(timestamp / 1000)                    
                    formatted_time = dt.strftime("%H:%M:%S")
                except:
                    formatted_time = "N/A"
                
                price = float(trade.get("price", 0))
                volume = float(trade.get("volume", 0))
                funds = float(trade.get("funds", 0))
                side = "🔥買" if trade.get("side") == "bid" else "💸賣"
                
                result += f"{formatted_time} {side} {volume:.6f} @ {price:,.1f} = {funds:,.0f}\n"
        
        return result
        
    except Exception as e:
        return f"綜合市場分析時發生錯誤：{e}"