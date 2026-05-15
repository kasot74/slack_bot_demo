from pymongo import MongoClient

#創建連線
def con_db(config):        
    user=config['MONGO_USER']
    pas=config['MONGO_PASSWORD']
    host=config['MONGO_HOST']
    port=config['MONGO_PORT']
    con_str=f"mongodb://{user}:{pas}@{host}:{port}/?authMechanism=SCRAM-SHA-1&authSource=admin"
    # MongoDB 連線
    client = MongoClient(con_str)
    db = client.myDatabase
    return db

# AI 模型預設設定
_DEFAULT_AI_MODEL_CONFIGS = [
    {"service": "claude",  "model": "claude-haiku-4-5-20251001"},
    {"service": "openai",  "model": "gpt-5.4",            "image_model": "gpt-image-2"},
    {"service": "xai",     "model": "grok-4.3-latest"},
    {"service": "dzmm",    "model": "nalang-xl-10"},
    {"service": "gemini",  "model": "gemini-2.5-flash",   "image_model": "gemini-3.1-flash-image-preview"},
]

def init_ai_model_configs(db):
    """初始化 ai_model_config 集合；若文件已存在則以預設值覆蓋。"""
    col = db.ai_model_config
    for cfg in _DEFAULT_AI_MODEL_CONFIGS:
        col.update_one(
            {"service": cfg["service"]},
            {"$set": cfg},
            upsert=True
        )

def get_ai_model_config(db, service_name: str) -> dict:
    """從 MongoDB ai_model_config 取得指定服務的模型設定，找不到時回傳預設值。"""
    col = db.ai_model_config
    doc = col.find_one({"service": service_name}, {"_id": 0})
    if doc:
        return doc
    # fallback：回傳硬編碼預設值
    defaults = {c["service"]: c for c in _DEFAULT_AI_MODEL_CONFIGS}
    return defaults.get(service_name, {})