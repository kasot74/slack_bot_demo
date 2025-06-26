import re
import random
from datetime import datetime
from pymongo import MongoClient

COMMANDS_HELP = [
    ("!簽到", "每日簽到，獲得 100 幣"),
    ("!查幣", "查詢你目前擁有的幣"),
    ("!給幣 <@user> 數量", "轉帳幣給其他人"),
    ("!轉盤", "花費 10 幣參加轉盤抽獎"),
    ("!窮鬼", "沒錢時可領取 10 幣救急"),
]

def record_coin_change(coin_collection, user_id, amount, change_type, related_user=None):
    """紀錄幣更動，方便其他功能呼叫"""
    record = {
        "user_id": user_id,
        "type": change_type,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "coins": amount,
        "timestamp": datetime.now()
    }
    if related_user:
        # 轉帳時記錄對方
        if change_type == "transfer_out":
            record["to_user"] = related_user
        elif change_type == "transfer_in":
            record["from_user"] = related_user
    coin_collection.insert_one(record)

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
        record_coin_change(coin_collection, user_id, 100, "checkin")
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
        record_coin_change(coin_collection, from_user, -amount, "transfer_out", related_user=to_user)
        # 增加 to_user
        record_coin_change(coin_collection, to_user, amount, "transfer_in", related_user=from_user)
        say(f"<@{from_user}> 已成功轉帳 {amount} 幣給 <@{to_user}>！")


    wheel_options = [
        "再接再厲", "恭喜獲得 10 幣", "恭喜獲得 20 幣", "恭喜獲得 50 幣", "恭喜獲得 100 幣", "謝謝參加"
    ]

    @app.message(re.compile(r"^!轉盤$"))
    def spin_wheel(message, say):
        coin_collection = db.user_coins
        user_id = message['user']
        # 查詢用戶現有幣
        total = coin_collection.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$user_id", "sum": {"$sum": "$coins"}}}
        ])
        total = list(total)
        coins = total[0]["sum"] if total else 0
        if coins < 10:
            say(f"<@{user_id}>，需10枚烏薩奇幣，不足無法參加轉盤！")
            return
        # 扣除 10 幣
        record_coin_change(coin_collection, user_id, -10, "spin_wheel")
        # 抽獎
        result = random.choice(wheel_options)
        say(f"<@{user_id}> 轉盤結果：{result}")
        # 若抽到加幣獎項，發放獎勵
        if "10 幣" in result:
            record_coin_change(coin_collection, user_id, 10, "spin_wheel_reward")
        elif "20 幣" in result:
            record_coin_change(coin_collection, user_id, 20, "spin_wheel_reward")
        elif "50 幣" in result:
            record_coin_change(coin_collection, user_id, 50, "spin_wheel_reward")
        elif "100 幣" in result:
            record_coin_change(coin_collection, user_id, 100, "spin_wheel_reward")
        elif "失敗你的烏薩奇幣已歸零QQ" in result:
            # 查詢目前剩餘幣
            total = coin_collection.aggregate([
                {"$match": {"user_id": user_id}},
                {"$group": {"_id": "$user_id", "sum": {"$sum": "$coins"}}}
            ])
            total = list(total)
            coins = total[0]["sum"] if total else 0
            if coins > 0:
                record_coin_change(coin_collection, user_id, -coins, "spin_wheel_zero")


    @app.message(re.compile(r"^!窮鬼$"))
    def poor_user(message, say):
        coin_collection = db.user_coins
        user_id = message['user']
        # 查詢用戶現有幣
        total = coin_collection.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$user_id", "sum": {"$sum": "$coins"}}}
        ])
        total = list(total)
        coins = total[0]["sum"] if total else 0
        if coins == 0:
            record_coin_change(coin_collection, user_id, 10, "poor_bonus")
            say(f"<@{user_id}>，你太窮了，發給你 10 枚烏薩奇幣救急！")
        else:
            say(f"<@{user_id}>，你還有 {coins} 枚烏薩奇幣，暫時不能領救濟金喔！")
