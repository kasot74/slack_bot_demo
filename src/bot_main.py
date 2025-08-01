from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from .handlers import register_handlers
from .model.coin_model import register_coin_handlers
from .model.member_monitor import register_member_handlers
from .model.stock_model import register_stock_handlers
from .model.shop_model import register_shop_handlers
from .model.ai_model import register_handlers as register_ai_handlers
from .model.adventure_model import register_adventure_handlers

from .handlers import COMMANDS_HELP as HANDLER_COMMANDS
from .model.coin_model import COMMANDS_HELP as COIN_COMMANDS
from .model.member_monitor import COMMANDS_HELP as MEMBER_COMMANDS
from .model.stock_model import COMMANDS_HELP as STOCK_COMMANDS
from .model.shop_model import COMMANDS_HELP as SHOP_COMMANDS
from .model.ai_model import COMMANDS_HELP as AI_COMMANDS
from .model.adventure_model import COMMANDS_HELP as ADVENTURE_COMMANDS

from .utilities import read_config
from .database import con_db
import os
import re
import gc
import threading
import time
import sys
import psutil

# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
db = con_db(config)
# 初始化 Slack App
app = App(token=config['SLACK_BOT_TOKEN'], signing_secret=config['SLACK_SIGNING_SECRET'])

ALL_COMMANDS = []

def get_all_commands_text():
    help_text = "*可用指令列表：*\n"
    for cmd, desc in ALL_COMMANDS:
        help_text += f"`{cmd}`：{desc}\n"
    return help_text
@app.message(re.compile(r"^!help$|^!指令$"))
def show_help(message, say):
    say(get_all_commands_text())

# 定期資源清理器
class ResourceCleaner:
    def __init__(self, interval_hours=6, memory_threshold_mb=500):
        self.interval_hours = interval_hours
        self.memory_threshold_mb = memory_threshold_mb
        self.start_time = time.time()
        self.running = True
        
    def get_memory_usage(self):
        """獲取記憶體使用量 (MB)"""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def cleanup_resources(self):
        """清理資源"""
        print("🧹 開始清理資源...")
        
        # 強制垃圾回收
        before_gc = self.get_memory_usage()
        collected = gc.collect()
        after_gc = self.get_memory_usage()
        
        print(f"垃圾回收: 清理前 {before_gc:.2f}MB, 清理後 {after_gc:.2f}MB, 回收 {collected} 個對象")
        
        # 如果記憶體仍然過高，準備重啟
        if after_gc > self.memory_threshold_mb:
            print(f"⚠️ 記憶體使用過高 ({after_gc:.2f}MB), 準備重啟程序...")
            return True
        
        return False
    
    def should_restart(self):
        """檢查是否需要重啟"""
        # 檢查運行時間
        runtime_hours = (time.time() - self.start_time) / 3600
        if runtime_hours >= self.interval_hours:
            print(f"⏰ 程序已運行 {runtime_hours:.1f} 小時，準備重啟...")
            return True
        
        # 檢查記憶體使用
        memory_usage = self.get_memory_usage()
        if memory_usage > self.memory_threshold_mb:
            print(f"🚨 記憶體使用過高 ({memory_usage:.2f}MB)，準備重啟...")
            return True
        
        return False
    
    def restart_program(self):
        """重啟程序"""
        print("🔄 重啟程序中...")
        time.sleep(2)  # 給一點時間讓消息發送完成
        
        # 清理資源
        self.cleanup_resources()
        
        # 重啟程序
        os.execv(sys.executable, ['python'] + sys.argv)
    
    def start_monitoring(self):
        """開始監控"""
        def monitor():
            while self.running:
                try:
                    if self.should_restart():
                        self.restart_program()
                        break
                    
                    # 定期清理
                    if int(time.time()) % 3600 == 0:  # 每小時清理一次
                        self.cleanup_resources()
                    
                    time.sleep(60)  # 每分鐘檢查一次
                    
                except Exception as e:
                    print(f"監控錯誤: {e}")
                    time.sleep(60)
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        print(f"📊 資源監控已啟動 (重啟間隔: {self.interval_hours}小時, 記憶體閾值: {self.memory_threshold_mb}MB)")

# 建立資源清理器
cleaner = ResourceCleaner(interval_hours=6, memory_threshold_mb=400)

@app.message(re.compile(r"^!restart$"))
def manual_restart(message, say):
    """手動重啟指令"""
    say("🔄 程序即將重啟...")
    cleaner.restart_program()

@app.message(re.compile(r"^!status$"))
def show_status(message, say):
    """顯示程序狀態"""
    runtime = (time.time() - cleaner.start_time) / 3600
    memory = cleaner.get_memory_usage()
    
    status = f"""📊 **程序狀態**
⏰ 運行時間: {runtime:.1f} 小時
💾 記憶體使用: {memory:.2f} MB
🔄 下次自動重啟: {cleaner.interval_hours - runtime:.1f} 小時後
⚡ 記憶體閾值: {cleaner.memory_threshold_mb} MB"""
    
    say(status)

@app.message(re.compile(r"^!gc$"))
def manual_gc(message, say):
    """手動垃圾回收"""
    before = cleaner.get_memory_usage()
    collected = gc.collect()
    after = cleaner.get_memory_usage()
    
    say(f"🧹 垃圾回收完成\n清理前: {before:.2f}MB\n清理後: {after:.2f}MB\n回收對象: {collected} 個")    

# 貨幣模組
ALL_COMMANDS += COIN_COMMANDS
register_coin_handlers(app, config, db)

# 註冊成員打招呼模組
#ALL_COMMANDS += MEMBER_COMMANDS
#register_member_handlers(app, config, db)

# 商店模組
ALL_COMMANDS += SHOP_COMMANDS
register_shop_handlers(app, config, db)

# 股票模組
ALL_COMMANDS += STOCK_COMMANDS
register_stock_handlers(app, config, db)

# AI 模組
ALL_COMMANDS += AI_COMMANDS
register_ai_handlers(app, config, db)

# 冒險遊戲模組
ALL_COMMANDS += ADVENTURE_COMMANDS
register_adventure_handlers(app, config, db)

# 註冊其他處理器
ALL_COMMANDS += HANDLER_COMMANDS
register_handlers(app, config, db)

# 啟動 SocketModeHandler
if __name__ == "__main__":    

    # 啟動資源監控
    cleaner.start_monitoring()
    SocketModeHandler(app, config['SLACK_APP_TOKEN']).start()    