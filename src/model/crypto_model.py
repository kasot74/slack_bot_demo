import re
import random
import json
import requests
from ..crypto import get_crypto_prices, get_pending_orders, get_trading_volume_stats, get_market_analysis
from ..AI_Service.ai_tool import get_maicoin_competition_table
from datetime import datetime, timedelta
from pymongo import MongoClient

class Order:
    """訂單資料模型"""
    
    def __init__(self, data=None):
        """初始化訂單物件"""
        if data is None:
            data = {}
        
        self._id = data.get('_id')
        self.id = data.get('id')
        self.created_at = data.get('created_at')
        self.executed_price = data.get('executed_price', 0)
        self.executed_quantity = data.get('executed_quantity', 0)
        self.max_order_id = data.get('max_order_id')
        self.max_state = data.get('max_state')
        self.order_type = data.get('order_type')  # buy or sell
        self.price = data.get('price', 0)
        self.quantity = data.get('quantity', 0)
        self.saved_at = data.get('saved_at')
        self.status = data.get('status')  # pending, completed, cancelled
        self.symbol = data.get('symbol')
        
        # 額外的使用者相關欄位
        self.user_id = data.get('user_id')
    
    def to_dict(self):
        """轉換為字典格式"""
        return {
            '_id': self._id,
            'id': self.id,
            'created_at': self.created_at,
            'executed_price': self.executed_price,
            'executed_quantity': self.executed_quantity,
            'max_order_id': self.max_order_id,
            'max_state': self.max_state,
            'order_type': self.order_type,
            'price': self.price,
            'quantity': self.quantity,
            'saved_at': self.saved_at,
            'status': self.status,
            'symbol': self.symbol,
            'user_id': self.user_id
        }
    
    def is_pending(self):
        """檢查是否為掛單狀態"""
        return self.status == 'pending'
    
    def is_buy_order(self):
        """檢查是否為買單"""
        return self.order_type == 'buy'
    
    def is_sell_order(self):
        """檢查是否為賣單"""
        return self.order_type == 'sell'
    
    def get_total_value(self):
        """計算訂單總價值"""
        return float(self.price) * float(self.quantity)
    
    def get_executed_value(self):
        """計算已執行價值"""
        return float(self.executed_price) * float(self.executed_quantity)
    
    def format_created_time(self):
        """格式化創建時間"""
        try:
            if isinstance(self.created_at, str):
                dt = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
                # 轉換為 UTC+8 時區
                dt_utc8 = dt + timedelta(hours=8)
                return dt_utc8.strftime("%Y-%m-%d %H:%M:%S")
            return str(self.created_at)
        except:
            return str(self.created_at)
    
    def __str__(self):
        """字串表示"""
        return f"Order(id={self.id}, {self.symbol}, {self.order_type}, {self.price}@{self.quantity}, {self.status})"
    
    def __repr__(self):
        return self.__str__()

COMMANDS_HELP = [    
    ("!order", "查詢目前掛單的訂單"),
    ("!MAX", "MAX 交易所加密貨幣即時價格"),
    ("!me", "查詢使用者的 Slack 資訊"),
    ("!排行榜", "API 交易量排行榜顯示各交易對成交量與利潤統計"),
    ("!市場分析 [symbol]", "綜合市場分析 (訂單深度+成交記錄)"),
    ("!出場價 [進場價]", "計算最低出場價 (含手續費)")
]

def register_crypto_handlers(app, config, db):
    
    # 授權的使用者 ID
    AUTHORIZED_USER_ID = "U09482DTM8F"    
    
    def check_user_permission(user_id):
        """檢查使用者是否有權限使用此模組"""
        return user_id == AUTHORIZED_USER_ID

    # !MAX    
    @app.message(re.compile(r"^!MAX$"))
    def get_max_price(message, say):        
        say(get_crypto_prices())


    # user_info
    @app.message(re.compile(r"!me$"))
    def get_user_info(message, say, client):                
        try:        
            # 獲取發送指令的用戶 ID
            user_id = message['user']
            
            # 檢查使用者權限
            if not check_user_permission(user_id):                
                say("你沒有權限使用此指令")
                return
            
            # 使用 Slack API 獲取用戶信息
            user_info = client.users_info(user=user_id)            
            user_info_str = json.dumps(user_info["user"], indent=4, ensure_ascii=False)
            user_Presence = client.users_getPresence(user=user_id)                        
            say(f"使用者信息:\n```{user_info_str}```\n \n使用者狀態:\n```{user_Presence}```")
        except Exception as e:        
            say(f"非預期性問題 {e}")    


    # !order 查詢掛單
    @app.message(re.compile(r"^!order$"))
    def handle_order_command(message, say):
        try:
            # 檢查使用者權限
            user_id = message['user']
            if not check_user_permission(user_id):                
                say("你沒有權限使用此指令")
                return
                        
            #result = get_pending_orders("wait")
            #result += "\n"            
            result = get_trading_volume_stats()            
            result += "\n"
            say(result)
            
        except Exception as e:
            say(f"查詢掛單時發生錯誤: {e}")


    # !市場分析 綜合市場分析
    @app.message(re.compile(r"^!市場分析(?:\s+(\w+))?$"))
    def handle_analysis_command(message, say):
        try:
            # 檢查使用者權限
            user_id = message['user']
            if not check_user_permission(user_id):                
                say("你沒有權限使用此指令")
                return
                        
            match = re.search(r"^!市場分析(?:\s+(\w+))?$", message['text'])
            symbol = match.group(1).upper() if match and match.group(1) else "BTCTWD"
                        
            result = get_market_analysis(symbol)
            say(result)
            
        except Exception as e:
            say(f"市場分析時發生錯誤: {e}")


    # !排行榜 API 交易量排行榜
    @app.message(re.compile(r"^!排行榜$"))
    def handle_volume_ranking_command(message, say):
        try:
            user_id = message['user']
            if not check_user_permission(user_id):                
                say("你沒有權限使用此指令")
                return
            
            result = get_maicoin_competition_table("all")
            say(result)
            
        except Exception as e:
            say(f"查詢 API 交易量排行榜時發生錯誤: {e}")


    # !出場價 計算最低出場價
    @app.message(re.compile(r"^!出場價\s+([\d.]+)$"))
    def handle_exit_price_command(message, say):
        try:
            user_id = message['user']
            if not check_user_permission(user_id):                
                say("你沒有權限使用此指令")
                return
            
            match = re.search(r"^!出場價\s+([\d.]+)$", message['text'])
            if not match:
                say("請提供進場價格，例如：`!出場價 50000`")
                return
                
            entry_price = float(match.group(1))
            
            # 手續費率
            # Post-only: 0.04% (0.0004)
            # Limit: 0.09% (0.0009)
            # 公式: 最低出場價 = 進場價 * (1 + 買入手續費) / (1 - 賣出手續費)
            
            # 情況 1: 買賣皆為 Post-only (0.04%)
            post_only_exit = entry_price * (1 + 0.0004) / (1 - 0.0004)
            
            # 情況 2: 買賣皆為 Limit (0.09%)
            limit_exit = entry_price * (1 + 0.0009) / (1 - 0.0009)
            
            # 情況 3: 買 Post-only (0.04%), 賣 Limit (0.09%)
            mixed_exit = entry_price * (1 + 0.0004) / (1 - 0.0009)
            
            response = (
                f"📈 *進場價：{entry_price:,.4f}*\n"
                f"━━━━━━━━━━━━━━\n"
                f"💰 *最低保本出場價 (Break-even):*\n"
                f"🔹 雙邊 Post-only (0.04%): *{post_only_exit:,.4f}*\n"
                f"🔸 雙邊 Limit (0.11%): *{limit_exit:,.4f}*\n"
                f"⚖️ 買入 Post / 賣出 Limit: *{mixed_exit:,.4f}*\n"
                f"━━━━━━━━━━━━━━\n"
                f"💡 _公式: 進場價 × (1 + 買入手續費) ÷ (1 - 賣出手續費)_"
            )
            say(response)
            
        except Exception as e:
            say(f"計算出場價時發生錯誤: {e}")

