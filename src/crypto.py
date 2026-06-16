import requests
import json
import concurrent.futures
from datetime import datetime, timedelta
from .utilities import read_config

_config = read_config('config/config.txt')
MAX_API_KEY = _config.get('MAX_API_KEY', '')
MAX_API_HEADERS = {
    'accept': 'application/json',
    'Authorization': f'Bearer {MAX_API_KEY}'
}

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

def get_trading_volume_stats(symbol="BTCTWD"):
    """取得交易績效統計（已實現 + 未實現損益），改用後端 /trading/performance API。"""
    url = f"https://herry537.sytes.net/max_api/trading/performance?symbol={symbol}"

    try:
        response = requests.get(url, headers=MAX_API_HEADERS, timeout=10)

        if response.status_code != 200:
            return f"API請求失敗，狀態碼：{response.status_code}"

        data = response.json()
        fills = data.get("fills", {})

        if fills.get("buy_count", 0) == 0 and fills.get("sell_count", 0) == 0:
            return data.get("message", f"{symbol} 目前沒有已成交訂單")

        position = data.get("position", {})
        pnl = data.get("pnl", {})
        period = data.get("period", {})

        result = f"💰 **{symbol} 交易績效統計**\n\n"
        result += f"📅 期間：{(period.get('first_fill') or 'N/A')[:16]} ~ {(period.get('last_fill') or 'N/A')[:16]}\n\n"

        result += f"━━━━ **成交統計** ━━━━\n"
        result += f"買入：{fills.get('buy_count', 0)}筆 | {fills.get('buy_qty', 0):.6f} BTC | {fills.get('buy_cost_twd', 0):,.2f} TWD\n"
        result += f"賣出：{fills.get('sell_count', 0)}筆 | {fills.get('sell_qty', 0):.6f} BTC | {fills.get('sell_revenue_twd', 0):,.2f} TWD\n"
        result += f"總交易額：{fills.get('total_turnover_twd', 0):,.2f}\n"
        result += f"預估手續費：-{fills.get('estimated_fees_twd', 0):,.2f}\n\n"

        result += f"━━━━ **持倉** ━━━━\n"
        net_qty = position.get("net_qty_btc", 0)
        if net_qty > 0:
            result += f"📊 持有：{net_qty:.6f} BTC | 均成本：{position.get('avg_cost_twd', 0):,.2f}\n"
        elif net_qty < 0:
            result += f"📊 空倉：{abs(net_qty):.6f} BTC（已超額賣出）\n"
        else:
            result += f"📊 無持有（已全部賣出）\n"
        if position.get("current_price_twd"):
            result += f"現價：{position['current_price_twd']:,.2f}\n"
        result += "\n"

        result += f"━━━━ **損益** ━━━━\n"
        result += f"已實現：{pnl.get('realized_twd', 0):+,.2f}\n"
        unrealized = pnl.get("unrealized_twd")
        result += f"未實現：{unrealized:+,.2f}\n" if unrealized is not None else "未實現：N/A\n"
        result += f"總損益：{pnl.get('total_twd', 0):+,.2f} ({pnl.get('total_pct', 0):+.2f}%)\n"

        return result

    except requests.exceptions.RequestException as e:
        return f"網路請求錯誤：{e}"
    except Exception as e:
        return f"處理績效資料時發生錯誤：{e}"


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

        # 並發請求兩個API
        with concurrent.futures.ThreadPoolExecutor() as executor:
            depth_future = executor.submit(requests.get, depth_url, headers=MAX_API_HEADERS, timeout=10)
            trades_future = executor.submit(requests.get, trades_url, headers=MAX_API_HEADERS, timeout=10)
            
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
