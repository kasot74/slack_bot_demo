import re
import random
import json
import requests
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
    ("!me", "查詢使用者的 Slack 資訊")
]

def register_crypto_handlers(app, config, db):
    
    # 授權的使用者 ID
    AUTHORIZED_USER_ID = "123456789"
    #AUTHORIZED_USER_ID = "U09482DTM8F"
    
    def check_user_permission(user_id):
        """檢查使用者是否有權限使用此模組"""
        return user_id == AUTHORIZED_USER_ID

    def sync_orders_from_api():
        """同步API資料到DB"""
        sync_message = ""
        try:
            orders_collection = db.orders
            
            # 取得所有wait狀態的訂單
            wait_orders = list(orders_collection.find({
                "max_state": "wait"
            }))
            
            if not wait_orders:
                return "無待同步的訂單"
            
            # 按交易對分組處理
            markets = {}
            for order in wait_orders:
                market = order.get('symbol', '').lower()
                if market not in markets:
                    markets[market] = []
                markets[market].append(order)
            
            # 逐個交易對查詢API
            for market, orders in markets.items():
                try:                    
                    
                    # 取得該市場的order IDs - 可能需要用max_order_id
                    order_ids = []
                    for order in orders:
                        if order.get('max_order_id'):
                            order_ids.append(str(order.get('max_order_id')))
                        elif order.get('id'):
                            order_ids.append(str(order.get('id')))
                    
                    if not order_ids:
                        sync_message += "沒有找到有效的訂單ID\n"
                        continue                                        
                    
                    # 檢查DB中實際存在的記錄 - 嘗試不同的ID字段
                    existing_ids = []
                    for order_id in order_ids:
                        # 嘗試用id字段查詢
                        existing_order_by_id = orders_collection.find_one({'id': int(order_id)})
                        # 嘗試用max_order_id字段查詢  
                        existing_order_by_max_id = orders_collection.find_one({'max_order_id': int(order_id)})
                        
                        if existing_order_by_id:
                            existing_ids.append(f"{order_id}(用id字段找到)")
                        elif existing_order_by_max_id:
                            existing_ids.append(f"{order_id}(用max_order_id字段找到)")
                        else:
                            sync_message += f"❌ DB中用兩種ID字段都找不到 {order_id}\n"                                        
                    
                    # 找到該交易對的最小訂單ID作為from_id參數
                    min_order_id = min([int(order.get('id', 0)) for order in orders if order.get('id')])                    
                    # 調用API查詢訂單狀態
                    api_url = f"https://herry537.sytes.net/max_api/orders/history"
                    params = {
                        'wallet_type': 'spot',
                        'market': market,
                        'from_id': min_order_id,
                        'limit': 100  # 增加限制以確保涵蓋所有訂單
                    }
                    
                    response = requests.get(api_url, params=params, timeout=10)
                    
                    if response.status_code == 200:
                        api_orders = response.json()
                        
                        # 如果回傳是單個物件，轉換為列表
                        if isinstance(api_orders, dict):
                            api_orders = [api_orders]
                                                    
                        # 更新DB中的訂單
                        for api_order in api_orders:
                            api_order_id = str(api_order.get('id', ''))                            
                            if api_order_id in order_ids:                                                                
                                                                                                                                                                
                                # 更新DB中的訂單資料
                                update_data = {
                                    'max_state': api_order.get('state', 'wait'),
                                    'status': api_order.get('state', 'pending'),
                                    'executed_price': float(api_order.get('avg_price', 0)),
                                    'executed_quantity': float(api_order.get('executed_volume', 0)),
                                    'saved_at': datetime.now().isoformat() + 'Z'
                                }
                                
                                # 如果有新的價格或數量資訊，也更新
                                if api_order.get('price'):
                                    update_data['price'] = float(api_order.get('price'))
                                if api_order.get('volume'):
                                    update_data['quantity'] = float(api_order.get('volume'))                                                                
                                
                                # 更新DB - 使用正確的查詢字段
                                update_query = {'max_order_id': int(api_order_id)}
                                result = orders_collection.update_one(
                                    update_query,
                                    {'$set': update_data}
                                )                                                                                                
                                
                except Exception as e:
                    sync_message += f"同步市場 {market} 時發生錯誤: {e}\n"
                    continue
            sync_message += "訂單資料同步完成！"
            return sync_message 
        except Exception as e:
            return f"同步API資料時發生錯誤: {e}"
            

    # user_info
    @app.message(re.compile(r"!me$"))
    def get_user_info(message, say, client):                
        try:        
            # 獲取發送指令的用戶 ID
            user_id = message['user']
            
            # 檢查使用者權限
            if not check_user_permission(user_id):                
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
                return
                
            orders_collection = db.orders
            
            # 先同步API資料
            sync_message = sync_orders_from_api()
            say(sync_message)
            # 查詢目前Wait狀態的掛單
            pending_orders_data = list(orders_collection.find({
                "max_state": "wait"
            }).sort("created_at", -1).limit(20))
            
            if not pending_orders_data:
                say("目前沒有掛單")
                return
            
            # 轉換為Order物件
            pending_orders = [Order(order_data) for order_data in pending_orders_data]
            
            # 格式化訂單資訊 - 表格格式
            response = "📋 **目前掛單**\n"
            response += "```\n"
            
            for order in pending_orders:
                symbol = order.symbol or ''
                quantity = str(order.quantity) if order.quantity else "0"
                price = f"{order.price:.2f}" if order.price else "0.00"
                
                # 判斷買單或賣單
                order_type = "買" if order.is_buy_order() else "賣" if order.is_sell_order() else "?"
                
                # 格式化創建時間
                try:
                    if order.created_at:
                        if isinstance(order.created_at, str):
                            dt = datetime.fromisoformat(order.created_at.replace('Z', '+00:00'))
                            # 轉換為 UTC+8 時區
                            dt_utc8 = dt + timedelta(hours=8)
                            created_str = dt_utc8.strftime("%m-%d %H:%M")
                        else:
                            created_str = str(order.created_at)[:16]
                    else:
                        created_str = "N/A"
                except:
                    created_str = "N/A"
                    
                response += f"{symbol:<10} {order_type:<4} {quantity:<10} {price:<12} {created_str}\n"
            
            response += "```\n"
            
            # 添加統計資訊
            total_orders = len(pending_orders)
            buy_orders = len([o for o in pending_orders if o.is_buy_order()])
            sell_orders = len([o for o in pending_orders if o.is_sell_order()])
            total_value = sum([o.get_total_value() for o in pending_orders])
            
            response += f"\n📊 **統計**: 總計 {total_orders} 筆 | 買單 {buy_orders} 筆 | 賣單 {sell_orders} 筆 | 總價值 {total_value:.2f}"
            
            say(response)
            
        except Exception as e:
            say(f"查詢掛單時發生錯誤: {e}")
