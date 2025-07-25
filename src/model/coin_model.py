import re
import random
from datetime import datetime, timedelta
from pymongo import MongoClient

COMMANDS_HELP = [
    ("!簽到", "每日簽到，獲得 100 幣"),
    ("!金幣排行", "top 3 金幣排行榜"),
    ("!窮鬼排行", "top 3 窮鬼排行榜"),
    ("!查幣", "查詢你目前擁有的幣"),
    ("!給幣 <@user> 數量", "轉帳幣給其他人"),
    ("!窮鬼", "沒錢時可領取 50 幣救急（僅當餘額為0時可領）"),
    ("!轉盤 [金額]", 
     "花費 10 幣以上參加轉盤抽獎，壓越多中大獎機率越高。\n"
     "獎項與機率（下注10時）：\n"
     "再接再厲33.7%、10幣11.2%、20幣16.9%、50幣6.7%、100幣3.4%、1000幣1.1%、謝謝參加22.5%、對折1.1%。\n"
     "下注越多，50幣/100幣/1000幣機率會提升。"),
    ("!抽獎 [金額]", 
     "花費 10 幣以上參加每日獎金池抽獎，花越多中獎機率越高，獎金池每日自動增加500。\n"
     "中獎機率：每 10 幣 1%，最高 30%。"),
    ("!抽獎排行", "top 3 抽中獎金池次數排行榜"),
    ("!獎金池", "查詢今日獎金池目前累積的金額"),
    ("!拉霸 [金額]", "花費 10 幣以上參加拉霸遊戲\n"
       "倍率說明:\n"
       "🍒🍒🍒:  5倍\n"
       "🍋🍋🍋:  8倍\n"
       "🔔🔔🔔:  15倍\n"
       "⭐⭐⭐:  30倍\n"
       "💎💎💎:  100倍\n"
       "7️⃣7️⃣7️⃣:  200倍\n"
    )
]

def record_coin_change(coin_collection, user_id, amount, change_type, related_user=None):
    """
    將每日資料合併處理，若當日同類型紀錄已存在則合併金額，否則新增。
    金額最大上限為 MAX_INT64，超過則只記錄到上限。
    """
    MAX_INT64 = 9_223_372_036_854_775_807
    today = datetime.now().strftime("%Y-%m-%d")
    # 限制單日單類型最大金額
    amount = max(min(amount, MAX_INT64), -MAX_INT64)

    # 查找是否已有同日同類型紀錄
    query = {
        "user_id": user_id,
        "type": change_type,
        "date": today
    }
    if related_user:
        if change_type == "transfer_out":
            query["to_user"] = related_user
        elif change_type == "transfer_in":
            query["from_user"] = related_user

    existing = coin_collection.find_one(query)
    if existing:
        # 合併金額，並限制最大上限
        new_amount = existing["coins"] + amount
        new_amount = max(min(new_amount, MAX_INT64), -MAX_INT64)
        coin_collection.update_one(
            {"_id": existing["_id"]},
            {"$set": {"coins": new_amount, "timestamp": datetime.now()}}
        )
    else:
        record = {
            "user_id": user_id,
            "type": change_type,
            "date": today,
            "coins": amount,
            "timestamp": datetime.now()
        }
        if related_user:
            if change_type == "transfer_out":
                record["to_user"] = related_user
            elif change_type == "transfer_in":
                record["from_user"] = related_user
        coin_collection.insert_one(record)

def merge_old_coin_records(coin_collection):
    """
    將 user_coins 資料表中同一 user、type、date（與相關 user）重複的紀錄合併為一筆，金額相加（有上限），保留最新 timestamp。
    適合資料量大時批次整理舊資料。
    """
    from pymongo import UpdateOne
    MAX_INT64 = 9_223_372_036_854_775_807

    # 聚合找出重複 key
    pipeline = [
        {
            "$group": {
                "_id": {
                    "user_id": "$user_id",
                    "type": "$type",
                    "date": "$date",
                    "to_user": "$to_user",
                    "from_user": "$from_user"
                },
                "ids": {"$push": "$_id"},
                "total": {"$sum": "$coins"},
                "latest": {"$max": "$timestamp"}
            }
        },
        {"$match": {"ids.1": {"$exists": True}}}  # 只找有重複的
    ]
    duplicates = list(coin_collection.aggregate(pipeline))

    requests = []
    for doc in duplicates:
        ids = doc["ids"]
        keep_id = ids[0]
        remove_ids = ids[1:]
        # 合併金額時加上上限限制
        merged_amount = max(min(doc["total"], MAX_INT64), -MAX_INT64)
        requests.append(
            UpdateOne(
                {"_id": keep_id},
                {"$set": {"coins": merged_amount, "timestamp": doc["latest"]}}
            )
        )
        # 刪除多餘的
        coin_collection.delete_many({"_id": {"$in": remove_ids}})
    if requests:
        coin_collection.bulk_write(requests)
    return len(duplicates)

def register_coin_handlers(app, config, db):
    @app.message(re.compile(r"^!coin_delete$"))
    def test_command(message, say):
        coin_collection = db.user_coins
        # 清空 coin_collection 所有資料
        result = coin_collection.delete_many({})
        say(f"已清空所有金幣紀錄，共刪除 {result.deleted_count} 筆資料。")

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

        # 查詢背包是否有有效簽到好寶寶
        shop_items = get_valid_items(user_id, db, effect_key="sign_in_bonus")
        bonus = 1
        if shop_items:
            say(f"<@{user_id}>，你有簽到好寶寶，簽到金額將會倍增！")            
            bonus = 2
        amount = 100 * bonus

        # 新增簽到記錄並加幣
        record_coin_change(coin_collection, user_id, amount, "checkin")
        say(f"<@{user_id}>，簽到成功！獲得 {amount} 烏薩奇幣 🎉")

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

    def get_valid_items(user_id, db, effect_key=None):
        """
        取得使用者背包中尚未過期且未使用的有效物品。
        可選擇只取出含特定效果的物品（effect_key）。
        """
        shop_collection = db.user_shops
        now = datetime.now()
        query = {
            "user_id": user_id,
            "$or": [
                {"expire_at": None},
                {"expire_at": {"$gt": now}}
            ]
        }
        if effect_key:
            query[f"effect.{effect_key}"] = {"$exists": True}
        items = list(shop_collection.find(query))
        return items 

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
        
        # 查詢背包是否有有效黃金口袋
        free_cost_items = get_valid_items(user_id, db, effect_key="free_cost")
        is_free = False
        if free_cost_items:
            # 50% 機率觸發不扣幣
            if random.random() < 0.5:
                say(f"<@{user_id}>，你觸發了黃金口袋，這次不扣除烏薩奇幣！")
                is_free = True
                
        # 查詢背包是否有有效幸運符
        spin_bonus_items = get_valid_items(user_id, db, effect_key="spin_bonus")
        spin_bonus = sum(item["effect"].get("spin_bonus", 0) for item in spin_bonus_items)
        say(f"<@{user_id}>，你有 {len(spin_bonus_items)} 個幸運符，轉盤中大獎機率提升 {spin_bonus * 100}%！") if spin_bonus > 0 else None   
        if not is_free:
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
        idx_1000 = population.index("恭喜獲得 1000 幣")
        if spin_bonus >= 1:
            # 100% 中大獎
            result = "恭喜獲得 1000 幣"
        else:
            weights[idx_1000] = int(weights[idx_1000] * (1 + spin_bonus))
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

    @app.message(re.compile(r"^!抽獎排行$"))
    def lottery_leaderboard(message, say):
        coin_collection = db.user_coins
        # 聚合查詢所有用戶 lottery_win 次數，排序取前三
        leaderboard = coin_collection.aggregate([
            {"$match": {"type": "lottery_win"}},
            {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 3}
        ])
        leaderboard = list(leaderboard)
        if not leaderboard:
            say("目前沒有抽獎中獎紀錄。")
            return
        msg = "*抽獎中獎排行榜（前 3 名，抽中獎金池次數）*\n"
        for idx, entry in enumerate(leaderboard, 1):
            user_id = entry["_id"]
            count = entry["count"]
            msg += f"{idx}. <@{user_id}>：{count} 次\n"
        say(msg)

    @app.message(re.compile(r"^!獎金池$"))
    def show_jackpot(message, say):
        pool_collection = db.lottery_pool
        coin_collection = db.user_coins
        today = datetime.now().strftime("%Y-%m-%d")
        pool = pool_collection.find_one({"date": today})
        # 查詢今日是否已有人中獎
        winner = coin_collection.find_one({"type": "lottery_win", "date": today})
        if winner:
            winner_id = winner["user_id"]
            amount = pool["amount"] if pool else 1000
            say(f"今日獎金池已被 <@{winner_id}> 抽中！目前獎金池重設為 {amount} 枚烏薩奇幣。")
        else:
            amount = pool["amount"] if pool else 1000
            say(f"今日獎金池目前累積：{amount} 枚烏薩奇幣！")

    @app.message(re.compile(r"^!抽獎(?:\s+(\d+))?$"))
    def lottery(message, say):
        coin_collection = db.user_coins
        pool_collection = db.lottery_pool
        user_id = message['user']
        # 取得今日日期
        today = datetime.now().strftime("%Y-%m-%d")
        # 查詢今天是否已有人中獎
        winner = coin_collection.find_one({"type": "lottery_win", "date": today})
        if winner:
            say(f"今日已經有人中獎，中獎人是 <@{winner['user_id']}>，請明天再來挑戰！")
            return

        # 解析下注金額
        match = re.match(r"^!抽獎(?:\s+(\d+))?$", message['text'])
        bet = int(match.group(1)) if match and match.group(1) else 10
        if bet < 10:
            say(f"<@{user_id}>，最低下注 10 枚烏薩奇幣！")
            return
        # 查詢背包是否有有效黃金口袋
        free_cost_items = get_valid_items(user_id, db, effect_key="free_cost")
        is_free = False
        if free_cost_items:
            # 50% 機率觸發不扣幣
            if random.random() < 0.5:
                say(f"<@{user_id}>，你觸發了黃金口袋，這次不扣除烏薩奇幣！")
                is_free = True

        # 查詢背包是否有籤王
        lottery_bonus_items = get_valid_items(user_id, db, effect_key="lottery_bonus")
        lottery_bonus = sum(item["effect"].get("lottery_bonus", 0) for item in lottery_bonus_items)        

        if not is_free:
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
            record_coin_change(coin_collection, user_id, -bet, "lottery", related_user=None)

        # 取得今日獎金池
        pool = pool_collection.find_one({"date": today})
        if not pool:
            # 若今天第一次抽，獎金池設為昨日獎金池+預設每日增加額
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            y_pool = pool_collection.find_one({"date": yesterday})
            base = y_pool["amount"] if y_pool else 1000
            pool_collection.insert_one({"date": today, "amount": base + 500})  # 每日自動增加500
            pool = pool_collection.find_one({"date": today})

        # 把本次下注金額加進獎金池
        pool_collection.update_one({"date": today}, {"$inc": {"amount": bet}})
        pool = pool_collection.find_one({"date": today})
        jackpot = pool["amount"]

        # 計算中獎機率（每10幣1%，最高30%）
        win_rate = min(bet // 10, 30)
        if lottery_bonus > 0:
            win_rate += int(lottery_bonus * 100)
        win_rate = min(win_rate, 100)   
        
        is_win = random.randint(1, 100) <= win_rate

        if is_win:
            # 中獎，發放獎金池
            record_coin_change(coin_collection, user_id, jackpot, "lottery_win")
            say(f"🎉 <@{user_id}> 恭喜你以 {bet} 幣抽中今日獎金池 {jackpot} 幣！")
            # 重設獎金池
            pool_collection.update_one({"date": today}, {"$set": {"amount": 1000}})
        else:
            say(f"<@{user_id}> 很可惜沒中獎，今日獎金池已累積 {jackpot} 幣！\n(你花越多，中獎機率越高，投注300枚 最高30%)")

    @app.message(re.compile(r"^!拉霸(?:\s+(\d+))?$"))
    def slot_machine(message, say):
        coin_collection = db.user_coins
        user_id = message['user']
        # 解析下注金額
        match = re.match(r"^!拉霸(?:\s+(\d+))?$", message['text'])
        bet = int(match.group(1)) if match and match.group(1) else 10
        if bet < 10:
            say(f"<@{user_id}>，最低下注 10 枚烏薩奇幣！")
            return

        # 查詢背包是否有有效黃金口袋
        free_cost_items = get_valid_items(user_id, db, effect_key="free_cost")
        is_free = False
        if free_cost_items:
            # 50% 機率觸發不扣幣
            if random.random() < 0.5:
                say(f"<@{user_id}>，你觸發了黃金口袋，這次不扣除烏薩奇幣！")
                is_free = True

        if not is_free:
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
            record_coin_change(coin_collection, user_id, -bet, "slot_machine", related_user=None)

        # 查詢背包是否有拉霸🍒連鎖或拉霸🍋連鎖
        slot1_items = get_valid_items(user_id, db, effect_key="slot1")
        slot2_items = get_valid_items(user_id, db, effect_key="slot2")
        slot3_items = get_valid_items(user_id, db, effect_key="slot3")
        has_slot1 = bool(slot1_items)
        has_slot2 = bool(slot2_items)
        has_slot3 = bool(slot3_items)

        # 拉霸輪帶設定（每一輪一個順序表）
        reel = [
            ["🍒", "🍋", "🔔", "⭐", "💎", "7️⃣", "🍒", "🍋", "🔔", "⭐", "💎", "7️⃣"],
            ["🍋", "🍒", "🔔", "⭐", "7️⃣", "💎", "🍋", "🍒", "🔔", "⭐", "7️⃣", "💎"],
            ["🔔", "🍋", "🍒", "⭐", "💎", "7️⃣", "🔔", "🍋", "🍒", "⭐", "💎", "7️⃣"]
        ]
        # 物品效果：將🍒改為7️⃣
        if has_slot1:
            for i in range(3):
                reel[i] = ["7️⃣" if s == "🍒" else s for s in reel[i]]
        # 物品效果：將🍋改為7️⃣
        if has_slot2:
            for i in range(3):
                reel[i] = ["7️⃣" if s == "🍋" else s for s in reel[i]]
        # 物品效果：將🔔改為7️⃣
        if has_slot3:
            for i in range(3):
                reel[i] = ["7️⃣" if s == "🔔" else s for s in reel[i]]                

        # 每輪隨機停一格，組成 3x3 結果
        stops = [random.randint(0, len(reel[0]) - 1) for _ in range(3)]
        rows = []
        for row_idx in range(3):
            row = []
            for col in range(3):
                # 輪帶環狀取值
                symbol = reel[col][(stops[col] + row_idx) % len(reel[col])]
                row.append(symbol)
            rows.append(row)

        payout = {
            "🍒🍒🍒": bet * 5,
            "🍋🍋🍋": bet * 8,
            "🔔🔔🔔": bet * 15,
            "⭐⭐⭐": bet * 30,
            "💎💎💎": bet * 100,
            "7️⃣7️⃣7️⃣": bet * 200
        }

        msg = f"<@{user_id}> 🎰 拉霸結果：\n"
        for row in rows:
            msg += " ".join(row) + "\n"

        win_amount = 0
        win_msgs = []

        # 所有橫列
        for i, row in enumerate(rows):
            row_str = "".join(row)
            amount = payout.get(row_str, 0)
            if amount > 0:
                win_amount += amount
                win_msgs.append(f"第{i+1}橫列中獎：{row_str}，獲得 {amount} 幣")

        # 所有直行
        for col in range(3):
            col_str = rows[0][col] + rows[1][col] + rows[2][col]
            amount = payout.get(col_str, 0)
            if amount > 0:
                win_amount += amount
                win_msgs.append(f"第{col+1}直行中獎：{col_str}，獲得 {amount} 幣")

        # 兩條斜線
        diag1 = rows[0][0] + rows[1][1] + rows[2][2]
        amount_diag1 = payout.get(diag1, 0)
        if amount_diag1 > 0:
            win_amount += amount_diag1
            win_msgs.append(f"左上到右下斜線中獎：{diag1}，獲得 {amount_diag1} 幣")

        diag2 = rows[0][2] + rows[1][1] + rows[2][0]
        amount_diag2 = payout.get(diag2, 0)
        if amount_diag2 > 0:
            win_amount += amount_diag2
            win_msgs.append(f"右上到左下斜線中獎：{diag2}，獲得 {amount_diag2} 幣")

        if win_amount > 0:
            record_coin_change(coin_collection, user_id, win_amount, "slot_machine_win")
            msg += "\n" + "\n".join(win_msgs)
            msg += f"\n總共獲得 {win_amount} 枚烏薩奇幣！"
        else:
            msg += "可惜沒中獎，再接再厲！"

        # 查詢最新剩餘金額
        total = coin_collection.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$user_id", "sum": {"$sum": "$coins"}}}
        ])
        total = list(total)
        coins = total[0]["sum"] if total else 0
        msg += f"\n你目前剩餘 {coins} 枚烏薩奇幣。"
        say(msg)