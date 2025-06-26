import re
import random
from datetime import datetime
from pymongo import MongoClient

COMMANDS_HELP = [
    ("!簽到", "每日簽到，獲得 100 幣"),
    ("!金幣排行", "top 3 金幣排行榜"),
    ("!查幣", "查詢你目前擁有的幣"),
    ("!給幣 <@user> 數量", "轉帳幣給其他人"),
    ("!轉盤 [金額]", 
     "花費 10 幣以上參加轉盤抽獎，壓越多中大獎機率越高。\n"
     "獎項與機率（下注10時）：\n"
     "再接再厲33.7%、10幣11.2%、20幣16.9%、50幣6.7%、100幣3.4%、1000幣1.1%、謝謝參加22.5%、對折1.1%。\n"
     "下注越多，50幣/100幣/1000幣機率會提升。"),
    ("!窮鬼", "沒錢時可領取 50 幣救急（僅當餘額為0時可領）")    
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


    def weighted_wheel_options(bet):
        # 基本獎項與權重
        options = [
            ("再接再厲", 30),
            ("恭喜獲得 10 幣", 10),
            ("恭喜獲得 20 幣", 15),
            ("恭喜獲得 50 幣", 5 + bet // 10),   # 壓越多，機率越高
            ("恭喜獲得 100 幣", 2 + bet // 5),  # 壓越多，機率越高
            ("恭喜獲得 1000 幣", 1 + bet // 10),  # 壓越多，機率越高
            ("謝謝參加", 20),
            (" :pepe_cry: 烏薩奇幣已對折", 1)
        ]
        population = [item[0] for item in options]
        weights = [item[1] for item in options]
        return population, weights

    @app.message(re.compile(r"^!轉盤(?:\s+(\d+))?$"))
    def spin_wheel(message, say):
        coin_collection = db.user_coins
        user_id = message['user']
        # 解析下注金額
        match = re.match(r"^!轉盤(?:\s+(\d+))?$", message['text'])
        bet = int(match.group(1)) if match and match.group(1) else 10
        if bet < 10:
            say(f"<@{user_id}>，最低下注 10 枚烏薩奇幣！")
            return
        # 查詢用戶現有幣
        total = coin_collection.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$user_id", "sum": {"$sum": "$coins"}}}
        ])
        total = list(total)
        coins = total[0]["sum"] if total else 0
        if coins < bet:
            say(f"<@{user_id}>，你的烏薩奇幣不足，無法下注 {bet} 枚！")
            return
        # 扣除下注金額
        record_coin_change(coin_collection, user_id, -bet, "spin_wheel", related_user=None)
        # 動態設定機率
        population, weights = weighted_wheel_options(bet)
        result = random.choices(population, weights=weights, k=1)[0]        
        # 發獎
        if "1000 幣" in result:
            record_coin_change(coin_collection, user_id, 1000, "spin_wheel_reward")
        elif "10 幣" in result:
            record_coin_change(coin_collection, user_id, 10, "spin_wheel_reward")
        elif "20 幣" in result:
            record_coin_change(coin_collection, user_id, 20, "spin_wheel_reward")
        elif "50 幣" in result:
            record_coin_change(coin_collection, user_id, 50, "spin_wheel_reward")
        elif "100 幣" in result:
            record_coin_change(coin_collection, user_id, 100, "spin_wheel_reward")
        elif "對折" in result:
            # 對折
            total = coin_collection.aggregate([
                {"$match": {"user_id": user_id}},
                {"$group": {"_id": "$user_id", "sum": {"$sum": "$coins"}}}
            ])
            total = list(total)
            coins = total[0]["sum"] if total else 0
            if coins > 0:
                half = coins // 2
                record_coin_change(coin_collection, user_id, -half, "spin_wheel_half")
        # 查詢最新剩餘金額
        total = coin_collection.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$user_id", "sum": {"$sum": "$coins"}}}
        ])
        total = list(total)
        coins = total[0]["sum"] if total else 0
        say(f"<@{user_id}> 轉盤結果：{result}\n你目前剩餘 {coins} 枚烏薩奇幣。")


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
        # 查詢已用幾次窮鬼
        used_count = coin_collection.count_documents({"user_id": user_id, "type": "poor_bonus"})
        if coins == 0:
            record_coin_change(coin_collection, user_id, 50, "poor_bonus")
            used_count += 1
            say(f"<@{user_id}>，你太窮了，發給你 50 枚烏薩奇幣救急！你已經使用 !窮鬼 {used_count} 次。")
        else:
            say(f"<@{user_id}>，你還有 {coins} 枚烏薩奇幣，暫時不能領救濟金喔！")

    @app.message(re.compile(r"^!金幣排行$"))
    def coin_leaderboard(message, say):
        coin_collection = db.user_coins
        # 聚合查詢所有用戶總金幣，排序取前三
        leaderboard = coin_collection.aggregate([
            {"$group": {"_id": "$user_id", "sum": {"$sum": "$coins"}}},
            {"$sort": {"sum": -1}},
            {"$limit": 3}
        ])
        leaderboard = list(leaderboard)
        if not leaderboard:
            say("目前沒有金幣紀錄。")
            return
        msg = "*烏薩奇幣排行榜（前 3 名）*\n"
        for idx, entry in enumerate(leaderboard, 1):
            user_id = entry["_id"]
            coins = entry["sum"]
            msg += f"{idx}. <@{user_id}>：{coins} 枚\n"
        say(msg)

    @app.message(re.compile(r"^!窮鬼排行$"))
    def poor_leaderboard(message, say):
        coin_collection = db.user_coins
        # 聚合查詢所有用戶 poor_bonus 次數，排序取前三
        leaderboard = coin_collection.aggregate([
            {"$match": {"type": "poor_bonus"}},
            {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 3}
        ])
        leaderboard = list(leaderboard)
        if not leaderboard:
            say("目前沒有窮鬼紀錄。")
            return
        msg = "*窮鬼排行榜（前 3 名，使用 !窮鬼 救濟次數）*\n"
        for idx, entry in enumerate(leaderboard, 1):
            user_id = entry["_id"]
            count = entry["count"]
            msg += f"{idx}. <@{user_id}>：{count} 次\n"
        say(msg)        