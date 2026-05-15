from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from .model.handlers_model import register_handlers as base_register_handlers
from .model.coin_model import register_coin_handlers
from .model.stock_model import register_stock_handlers
from .model.shop_model import register_shop_handlers
from .model.ai_model import register_handlers as register_ai_handlers
from .model.crypto_model import register_crypto_handlers

from .model.handlers_model import COMMANDS_HELP as HANDLER_COMMANDS
from .model.coin_model import COMMANDS_HELP as COIN_COMMANDS
from .model.stock_model import COMMANDS_HELP as STOCK_COMMANDS
from .model.shop_model import COMMANDS_HELP as SHOP_COMMANDS
from .model.ai_model import COMMANDS_HELP as AI_COMMANDS
from .model.crypto_model import COMMANDS_HELP as CRYPTO_COMMANDS

from .utilities import read_config
from .database import con_db, init_ai_model_configs
from .log_analyzer import AccessLogAnalyzer
from .log_analyzer import AccessLogEntry
from .model.resource_monitor import ResourceCleaner, register_resource_commands
from .AI_Service.ai_tool import  read_url_content
from datetime import datetime, timedelta
import os
import re

# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
db = con_db(config)
init_ai_model_configs(db)  # 確保 AI 模型設定已初始化至 MongoDB
# 初始化 Slack App
app = App(token=config['SLACK_BOT_TOKEN'], signing_secret=config['SLACK_SIGNING_SECRET'])

ALL_COMMANDS = [
    ("!help 或 !指令", "顯示所有可用指令"),
    ("!cleanup 或 !清理資料庫", "檢查並清理空的資料庫Collection"),
    ("!importlog 或 !匯入日誌", "分批匯入整個昨日access.log到資料庫")    
]

def get_all_commands_text():
    help_text = "*可用指令列表：*\n"
    for cmd, desc in ALL_COMMANDS:
        help_text += f"`{cmd}`：{desc}\n"
    return help_text
@app.message(re.compile(r"^!help$|^!指令$"))
def show_help(message, say):
    say(get_all_commands_text())

@app.message(re.compile(r"^!cleanup$|^!清理資料庫$"))
def handle_database_cleanup(message, say):
    """處理資料庫清理指令"""
    try:
        say("🔍 開始檢查資料庫...")
        
        # 檢查並清理空的Collection
        result = check_and_cleanup_empty_collections(db)
        
        if result:
            response = f""" 資料庫清理完成！
                        檢查結果:
                        • 總Collection數: {result['total_collections']}
                        • 空Collection數: {len(result['empty_collections'])}
                        • 已刪除Collection數: {len(result['deleted_collections'])}"""
            
            if result['deleted_collections']:
                response += f"\n 已刪除: {', '.join(result['deleted_collections'])}"
        else:
            response = "❌ 資料庫清理失敗，請檢查連線狀態"
            
        say(response)
        
    except Exception as e:
        say(f"❌ 執行資料庫清理時發生錯誤: {str(e)}")

def check_and_cleanup_empty_collections(db):
    """檢查並刪除空的Collection"""
    try:
        collection_names = db.list_collection_names()
        empty_collections = []
        deleted_collections = []                        
        
        for collection_name in collection_names:
            collection = db[collection_name]
            doc_count = collection.count_documents({})                                    
            if doc_count == 0:
                empty_collections.append(collection_name)
        
        if empty_collections:                        
            for coll_name in empty_collections:
                try:
                    db.drop_collection(coll_name)
                    deleted_collections.append(coll_name)
                    print(f"✅ 已刪除空Collection: {coll_name}")
                except Exception as e:
                    print(f"❌ 刪除 {coll_name} 失敗: {e}")
                    # 重新拋出異常，讓上層處理
                    raise Exception(f"刪除Collection '{coll_name}' 失敗: {e}")
        else:
            print("✅ 沒有發現空的Collection")
        
        return {
            'total_collections': len(collection_names),
            'empty_collections': empty_collections,
            'deleted_collections': deleted_collections
        }
        
    except Exception as e:
        print(f"❌ 檢查Collection失敗: {e}")
        raise

@app.message(re.compile(r"^!importlog$|^!匯入日誌$"))
def handle_import_access_log(message, say):
    """處理 access.log-* 檔案匯入並於完成後刪除"""
    log_dir = "nginx_logs"
    if not os.path.exists(log_dir):
        say(f"📁 找不到日誌目錄: {log_dir}")
        return

    # 取得所有以 access.log- 開頭的檔案
    log_files = [f for f in os.listdir(log_dir) if f.startswith("access.log-")]
    
    if not log_files:
        say("✅ 沒有發現待處理的 access.log- 檔案")
        return

    say(f"📥 發現 {len(log_files)} 個檔案，開始分批處理...")
    
    try:
        for filename in log_files:
            log_file_path = os.path.join(log_dir, filename)
            say(f"📄 正在處理: {filename}...")
            
            # 建立日誌分析器
            analyzer = AccessLogAnalyzer(log_file_path, use_database=True)
            if not analyzer.use_database:
                say(f"❌ {filename}: 資料庫連線失敗，跳過")
                continue
            
            # 分批處理設定
            batch_size = 5000
            total_processed = 0
            total_saved = 0
            
            with open(log_file_path, 'r', encoding='utf-8') as file:
                while True:
                    lines_batch = []                
                    for _ in range(batch_size):
                        line = file.readline()
                        if not line: break
                        lines_batch.append(line)
                    
                    if not lines_batch: break
                    
                    batch_entries = []
                    for line in lines_batch:                    
                        entry = AccessLogEntry(line)
                        if entry.is_valid():
                            batch_entries.append(entry)
                    
                    if batch_entries:
                        # 使用臨時分析器存入當前批次
                        batch_analyzer = AccessLogAnalyzer(log_file_path, use_database=True)
                        batch_analyzer.entries = batch_entries
                        saved_count = batch_analyzer.save_all_entries_to_db()
                        total_saved += saved_count
                    
                    total_processed += len(lines_batch)
            
            # 建立索引
            analyzer.create_database_indexes()
            
            # 處理成功後刪除檔案
            os.remove(log_file_path)
            say(f"✅ {filename} 處理完成 (儲存 {total_saved:,} 筆) 且已刪除檔案")

        say("🏁 所有日誌檔案處理完畢！")
        
    except Exception as e:
        say(f"❌ 執行過程中發生錯誤: {str(e)}")


# 貨幣模組
ALL_COMMANDS += COIN_COMMANDS
register_coin_handlers(app, config, db)

# 商店模組
ALL_COMMANDS += SHOP_COMMANDS
register_shop_handlers(app, config, db)

# 股票模組
ALL_COMMANDS += STOCK_COMMANDS
register_stock_handlers(app, config, db)

# AI 模組
ALL_COMMANDS += AI_COMMANDS
register_ai_handlers(app, config, db)

# 加密貨幣模組
ALL_COMMANDS += CRYPTO_COMMANDS
register_crypto_handlers(app, config, db)

# 註冊其他處理器
ALL_COMMANDS += HANDLER_COMMANDS
base_register_handlers(app, config, db)

# 啟動 SocketModeHandler
if __name__ == "__main__":        
    SocketModeHandler(app, config['SLACK_APP_TOKEN']).start()    