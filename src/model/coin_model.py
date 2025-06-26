import re
from datetime import datetime
from pymongo import MongoClient

def register_coin_handlers(app, config, db):
    @app.message(re.compile(r"^!簽到$"))
    def checkin(message, say):
        coin_collection = db.user_coins   
        user_id = message['user']
        today = datetime.now().strftime("%Y-%m-%d")                
        # 查詢今天是否已簽到
        record = coin_collection.find_one({"user_id": user_id,"type": "checkin", "date": today})
        if record:
            say(f"<@{user_id}>，你今天已經簽到過囉！")
            return

        # 新增簽到記錄並加幣
        coin_collection.insert_one({
            "user_id": user_id,
            "type": "checkin",
            "date": today,
            "coins": 100,
            "timestamp": datetime.now()
        })
        say(f"<@{user_id}>，簽到成功！獲得 100 烏薩奇幣 🎉")

    @app.message(re.compile(r"^!查幣$"))
    def check_coins(message, say):
        coin_collection = db.user_coins   
        user_id = message['user']
        total = coin_collection.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$user_id", "sum": {"$sum": "$coins"}}}
        ])
        total = list(total)
        coins = total[0]["sum"] if total else 0
        say(f"<@{user_id}>，你目前擁有 {coins} 烏薩奇幣！")   

    @app.message(re.compile(r"^!給幣\s+<@(\w+)>\s+(\d+)$"))
    def give_coins(message, say):
        coin_collection = db.user_coins
        from_user = message['user']
        match = re.match(r"^!給幣\s+<@(\w+)>\s+(\d+)$", message['text'])
        if not match:
            say("格式錯誤，請使用：!給幣 @tag 數量")
            return
        to_user = match.group(1)
        amount = int(match.group(2))
        if amount <= 0:
            say("轉帳金額必須大於0")
            return
        # 計算 from_user 的總幣
        total = coin_collection.aggregate([
            {"$match": {"user_id": from_user}},
            {"$group": {"_id": "$user_id", "sum": {"$sum": "$coins"}}}
        ])
        total = list(total)
        coins = total[0]["sum"] if total else 0
        if coins < amount:
            say(f"<@{from_user}>，你的餘額不足，無法轉帳！")
            return
        # 扣除 from_user
        coin_collection.insert_one({
            "user_id": from_user,
            "type": "transfer_out",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "coins": -amount,
            "timestamp": datetime.now(),
            "to_user": to_user
        })
        # 增加 to_user
        coin_collection.insert_one({
            "user_id": to_user,
            "type": "transfer_in",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "coins": amount,
            "timestamp": datetime.now(),
            "from_user": from_user
        })
        say(f"<@{from_user}> 已成功轉帳 {amount} 幣給 <@{to_user}>！")