import gc
import threading
import time
import sys
import os
import psutil
import re


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


def register_resource_commands(app, cleaner):
    """註冊資源管理相關的 Slack 命令"""
    
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

    return [
        ("!restart", "手動重啟程序"),
        ("!status", "顯示程序運行狀態"),
        ("!gc", "手動執行垃圾回收")
    ]