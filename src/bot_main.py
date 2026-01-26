from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from .model.handlers_model import register_handlers as base_register_handlers
from .model.coin_model import register_coin_handlers
from .model.stock_model import register_stock_handlers
from .model.shop_model import register_shop_handlers
from .model.ai_model import register_handlers as register_ai_handlers


from .model.handlers_model import COMMANDS_HELP as HANDLER_COMMANDS
from .model.coin_model import COMMANDS_HELP as COIN_COMMANDS
from .model.stock_model import COMMANDS_HELP as STOCK_COMMANDS
from .model.shop_model import COMMANDS_HELP as SHOP_COMMANDS
from .model.ai_model import COMMANDS_HELP as AI_COMMANDS


from .utilities import read_config
from .database import con_db
from .log_analyzer import AccessLogAnalyzer
from .log_analyzer import AccessLogEntry
from .model.resource_monitor import ResourceCleaner, register_resource_commands
import os
import re

# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
db = con_db(config)
# 初始化 Slack App
app = App(token=config['SLACK_BOT_TOKEN'], signing_secret=config['SLACK_SIGNING_SECRET'])

ALL_COMMANDS = [
    ("!help 或 !指令", "顯示所有可用指令"),
    ("!cleanup 或 !清理資料庫", "檢查並清理空的資料庫Collection"),
    ("!importlog 或 !匯入日誌", "分批匯入整個access.log到資料庫")
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

#這裡需要增加一個指令來 把 access.log 裡面的資料存到資料庫裡面

@app.message(re.compile(r"^!importlog$|^!匯入日誌$"))
def handle_import_access_log(message, say):
    """處理access.log匯入資料庫指令"""
    say("📥 開始分批匯入 access.log 到資料庫...")
    try:
                
        log_file = "access.log"
        if not os.path.exists(log_file):
            say("❌ 找不到 access.log 檔案")
            return
        
        # 建立日誌分析器
        analyzer = AccessLogAnalyzer(log_file, use_database=True)
        
        if not analyzer.use_database:
            say("❌ 資料庫連線失敗，無法匯入日誌")
            return
        
        # 分批處理設定
        batch_size = 5000  # 每批處理5000行
        total_processed = 0
        total_saved = 0
        batch_count = 0
        
        # 取得檔案總行數
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                total_lines = sum(1 for _ in f)
            say(f"📊 檔案總行數: {total_lines:,}，開始分批處理...")
        except:
            total_lines = 0
            say("📊 開始分批處理...")
        
        # 分批處理檔案
        with open(log_file, 'r', encoding='utf-8') as file:
            while True:
                batch_count += 1
                lines_batch = []
                if batch_count <= 8:
                    continue 
                # 讀取一批資料
                for i in range(batch_size):
                    line = file.readline()
                    if not line:  # 檔案結束
                        break
                    lines_batch.append(line)
                
                if not lines_batch:  # 沒有更多資料
                    break
                
                # 處理當前批次
                batch_analyzer = AccessLogAnalyzer(log_file, use_database=True)
                batch_entries = []
                
                for line in lines_batch:                    
                    entry = AccessLogEntry(line)
                    if entry.is_valid():
                        batch_entries.append(entry)
                
                # 將批次資料存入資料庫
                if batch_entries:
                    batch_analyzer.entries = batch_entries
                    saved_count = batch_analyzer.save_all_entries_to_db()
                    total_saved += saved_count
                
                total_processed += len(lines_batch)
                
                # 每5批或處理完成時回報進度
                if batch_count % 5 == 0 or len(lines_batch) < batch_size:
                    progress = (total_processed / total_lines * 100) if total_lines > 0 else 0
                    say(f"⏳ 進度: 批次 {batch_count}, 已處理 {total_processed:,} 行 ({progress:.1f}%), 已儲存 {total_saved:,} 筆")
        
        # 建立索引提升查詢效能
        say("🔧 建立資料庫索引...")
        analyzer.create_database_indexes()
        
        # 最終統計
        final_db_count = len(analyzer.get_entries_from_db(limit=10000))
        
        response = f"""✅ access.log 分批匯入完成！
                    📊 最終結果:
                    • 總處理行數: {total_processed:,}
                    • 新儲存記錄: {total_saved:,}
                    • 資料庫總記錄: {final_db_count:,}
                    • 處理批次數: {batch_count}
                    • Collection: access_logs"""
        
        say(response)
        
    except Exception as e:
        say(f"❌ 匯入access.log時發生錯誤: {str(e)}")


# 建立資源清理器
# cleaner = ResourceCleaner(interval_hours=6, memory_threshold_mb=400)

# 註冊資源管理命令
# RESOURCE_COMMANDS = register_resource_commands(app, cleaner)
# ALL_COMMANDS += RESOURCE_COMMANDS

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

# 註冊其他處理器
ALL_COMMANDS += HANDLER_COMMANDS
base_register_handlers(app, config, db)

# 啟動 SocketModeHandler
if __name__ == "__main__":    
    # 啟動資源監控
    # cleaner.start_monitoring()
    SocketModeHandler(app, config['SLACK_APP_TOKEN']).start()    