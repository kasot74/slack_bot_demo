from datetime import datetime
from pymongo import MongoClient


def register_coin_handlers(app,db):
    coin_collection = db.user_coins

    @app.message(re.compile(r"^!簽到$"))
    def checkin(message, say):
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

    @app.message(re.compile(r"^!我的幣$"))
    def check_coins(message, say):
        user_id = message['user']
        total = coin_collection.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$user_id", "sum": {"$sum": "$coins"}}}
        ])
        total = list(total)
        coins = total[0]["sum"] if total else 0
        say(f"<@{user_id}>，你目前擁有 {coins} 烏薩奇幣！")