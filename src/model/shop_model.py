import re
from datetime import datetime, timedelta
from pymongo import MongoClient
from .coin_model import record_coin_change
# 商品清單，可依需求擴充
SHOP_ITEMS = [
    {
        "id": 1,
        "name": "幸運符",
        "price": 5000,
        "desc": "增加轉盤中大獎率5% 可疊加",
        "expire_days": 1,
        "effect": {"spin_bonus": 0.05}
    },
    {
        "id": 2,
        "name": "有錢人勳章",
        "price": 100000000,
        "desc": "擁有它證明你是有錢人，無任何效果",
        "expire_days": None,
        "effect": {}
    },
    {
        "id": 3,
        "name": "籤王",
        "price": 10000,
        "desc": "增加抽獎中獎率5% 可疊加",
        "expire_days": 7,
        "effect": {"lottery_bonus": 0.05}
    },
    {
        "id": 4,
        "name": "黃金口袋",
        "price": 50000,
        "desc": "持有時消耗烏薩奇幣的動作時有50%的機率不會消耗(商店購買不適用)",
        "expire_days": 3,
        "effect": {"free_cost": True}
    },
    {
        "id": 5,
        "name": "簽到好寶寶",
        "price": 50,
        "desc": "持有時簽到金額倍增",
        "expire_days": 3,
        "effect": {"sign_in_bonus": 2}  # 2倍
    },
    {
        "id": 6,
        "name": "拉霸🍒連鎖",
        "price": 200,
        "desc": "將拉霸中的🍒改為7️⃣",
        "expire_days": 3,
        "effect": {"slot1": True}  
    },
    {
        "id": 7,
        "name": "拉霸🍋連鎖",
        "price": 200,
        "desc": "將拉霸中的🍋改為7️⃣",
        "expire_days": 3,
        "effect": {"slot2": True}  
    },
    {
        "id": 8,
        "name": "拉霸🔔連鎖",
        "price": 200,
        "desc": "將拉霸中的🔔改為7️⃣",
        "expire_days": 3,
        "effect": {"slot3": True}  
    }
]

COMMANDS_HELP = [
    ("!商店", "查看商店商品列表"),
    ("!購買 商品編號", "購買指定商品"),
    ("!背包", "查看自己的購買背包")
]


def get_shop_item(item_id):
    return next((i for i in SHOP_ITEMS if i["id"] == item_id), None)

def get_expire_at(item):
    if item.get("expire_days"):
        return datetime.now() + timedelta(days=item["expire_days"])
    return None

def shop_list_handler(message, say):
    msg = "*商店商品列表：*\n"
    for item in SHOP_ITEMS:
        expire_str = f"（效期{item['expire_days']}天）" if item.get("expire_days") else ""
        msg += f"{item['id']}. {item['name']} - {item['price']} 幣：{item['desc']}{expire_str}\n"
    msg += "購買請輸入：!購買 商品編號"
    say(msg)

def shop_buy_handler(message, say, db):
    coin_collection = db.user_coins
    shop_collection = db.user_shops
    user_id = message['user']
    match = re.match(r"^!購買\s+(\d+)$", message['text'])
    if not match:
        say("請輸入正確格式：!購買 商品編號")
        return
    item_id = int(match.group(1))
    item = get_shop_item(item_id)
    if not item:
        say("查無此商品，請輸入正確的商品編號。")
        return
    # 查詢用戶現有幣
    total = coin_collection.aggregate([
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$user_id", "sum": {"$sum": "$coins"}}}
    ])
    total = list(total)
    coins = total[0]["sum"] if total else 0
    if coins < item["price"]:
        say(f"<@{user_id}>，你的烏薩奇幣不足，無法購買 {item['name']}！")
        return
    # 扣款
    record_coin_change(coin_collection, user_id, -item["price"], "shop_buy", related_user=None)
    # 記錄購買，含效期
    expire_at = get_expire_at(item)
    shop_collection.insert_one({
        "user_id": user_id,
        "item_id": item["id"],
        "item_name": item["name"],
        "price": item["price"],
        "timestamp": datetime.now(),
        "expire_at": expire_at,
        "effect": item["effect"]
    })
    msg = f"<@{user_id}>，成功購買 {item['name']}！"
    if expire_at:
        msg += f" 效期至 {expire_at.strftime('%Y-%m-%d %H:%M:%S')}"
    say(msg)

def shop_bag_handler(message, say, db):
    shop_collection = db.user_shops
    user_id = message['user']
    now = datetime.now()
    items = list(shop_collection.find({"user_id": user_id}))
    if not items:
        say(f"<@{user_id}>，你的背包是空的，快去 !商店 買東西吧！")
        return
    msg = f"<@{user_id}> 你的背包：\n"
    for i, item in enumerate(items, 1):
        expire_str = ""
        if item.get("expire_at"):
            expire_at = item["expire_at"]
            if isinstance(expire_at, str):
                expire_at = datetime.fromisoformat(expire_at)
            if expire_at < now:
                expire_str = "（已過期）"
            else:
                expire_str = f"（效期至 {expire_at.strftime('%Y-%m-%d %H:%M:%S')}）"
        msg += f"{i}. {item['item_name']}（{item['price']} 幣）{expire_str}\n"
    say(msg)

# 綁定到 app
def register_shop_handlers(app, config, db):
    @app.message(re.compile(r"^!商店$"))
    def _(message, say):
        shop_list_handler(message, say)

    @app.message(re.compile(r"^!購買\s+(\d+)$"))
    def _(message, say):
        shop_buy_handler(message, say, db)

    @app.message(re.compile(r"^!背包$"))
    def _(message, say):
        shop_bag_handler(message, say, db)