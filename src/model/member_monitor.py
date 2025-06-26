import re
import time
import json
import threading
from datetime import datetime
from pymongo import MongoClient
from slack_sdk import WebClient
from .AI_Service.xai import create_greet as xai_create_greet  # 根據你的專案結構調整

class MemberMonitor:
    def __init__(self, bot_token,channel_id):
        self.client = WebClient(token=bot_token)        
        self.user_status = {}  # 用於記錄用戶的狀態                
        self.channel_id = channel_id
        self.stop_event = threading.Event()  # 用於停止線程的事件
        self.monitor_thread = None  # 用於存儲線程對象
        self.admin_list = self.get_admin_members()  # 用於存儲管理員列表

    def get_all_members(self):
        try:
            result = self.client.users_list()
            return result["members"]
        except Exception as e:
            print(f"Error getting members: {e}")
            return []

    def get_admin_members(self):
        try:
            # 調用 Slack API 的 users_list 方法
            result = self.client.users_list()
            
            # 提取 members 資料
            members = result.get("members", [])
            
            # 篩選出具有管理員權限的成員
            admin_members = [member for member in members if member.get("is_admin", False) ]
            
            # 打印管理員資訊
            for admin in admin_members:
                user_id = admin.get("id", "未知ID")
                display_name = admin.get("profile", {}).get("display_name", "未知顯示名稱")
                real_name = admin.get("profile", {}).get("real_name", "未知真實名稱")
                print(f"管理員ID: {user_id}, 顯示名稱: {display_name}, 真實名稱: {real_name}")
            
            return admin_members
        except Exception as e:
            self.client.chat_postMessage(
                channel=self.channel_id,
                text=f"get_admin_error: {e}",
            )
            return []

    def check_and_greet_members(self):
        members = self.get_all_members()
        
        for member in members:
            # 排除機器人和應用用戶
            if not (member.get("is_bot") or member.get("is_app_user")):
                try:
                    presence = self.client.users_getPresence(user=member["id"])
                    user_id = member["id"]
                    # 獲取用戶名稱
                    user_name = member.get("profile", {}).get("display_name", "")
                    if(user_name == ""):
                        user_name = member.get("real_name", "")
                    current_presence = presence["presence"] #presence["online"]
                    # 檢查狀態是否變化
                    if user_id in self.user_status:
                        previous_presence = self.user_status[user_id]
                        if previous_presence != current_presence:
                            if current_presence == "active":                                                            
                                greet_message = xai_create_greet(user_name,"上線")
                                self.client.chat_postMessage(
                                    channel=self.channel_id,  
                                    text=greet_message,
                                )
                            if current_presence != "active":                                                                                        
                                greet_message = xai_create_greet(user_name,"下線")
                                self.client.chat_postMessage(
                                    channel=self.channel_id,
                                    text=greet_message,
                                )
                    else:
                        # 首次檢查時初始化狀態
                        print(f"用戶 {user_name}狀態初始化為")

                    # 更新用戶狀態
                    self.user_status[user_id] = current_presence
                except Exception as e:
                    print(f"Error processing member {member['id']}: {e}")
        

    def start_monitoring(self, interval=30):
        def monitor():
            while not self.stop_event.is_set():
                self.check_and_greet_members()
                time.sleep(interval)

        if self.monitor_thread and self.monitor_thread.is_alive():
            print("Monitoring is already running.")
            return

        self.stop_event.clear()
        self.monitor_thread = threading.Thread(target=monitor, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.stop_event.set()
            self.monitor_thread.join()
            print("Monitoring has been stopped.")
        else:
            print("No monitoring thread is running.")    


def register_member_handlers(app, config, db):
    
    # 初始化 MemberMonitor 並傳入 say 方法
    monitor = MemberMonitor(bot_token=config["SLACK_BOT_TOKEN"],channel_id =config["SLACK_CHANNEL_ID"])
    # 啟動定時檢查
    monitor.start_monitoring(interval=30)     
    monitor.stop_event.set()
    @app.message(re.compile(r"^!問候開啟$"))
    def enable_greet(message, say):
        try:
            if monitor.monitor_thread and monitor.monitor_thread.is_alive():
                say("問候功能已經啟用！")
                return

            monitor.stop_event.clear()  # 清除停止標誌
            monitor.start_monitoring(interval=30)  # 重新啟動線程
            say("問候功能已啟用！")
        except Exception as e:
            say(f"啟用問候功能時發生錯誤：{e}")

    @app.message(re.compile(r"^!問候關閉$"))
    def disable_greet(message, say):
        monitor.stop_event.set()
        say("問候功能已關閉！")    
 
    # user_info
    @app.message(re.compile(r"!me$"))
    def get_user_info(message, say, client):                
        try:        
            # 獲取發送指令的用戶 ID
            user_id = message['user']
            
            # 使用 Slack API 獲取用戶信息
            user_info = client.users_info(user=user_id)            
            user_info_str = json.dumps(user_info["user"], indent=4, ensure_ascii=False)
            user_Presence = client.users_getPresence(user=user_id)            
            #user_Presence_str = json.dumps(user_Presence, indent=4, ensure_ascii=False)
            say(f"使用者信息:\n```{user_info_str}```\n \n使用者狀態:\n```{user_Presence}```")
        except Exception as e:        
            say(f"非預期性問題 {e}")       
    #admin_info
    @app.message(re.compile(r"!admin$"))
    def get_admin_info(message, say, client):                
        try:        
            admin_list = monitor.admin_list
            m = "管理員列表:\n"            
            for admin in admin_list:
                m += f"顯示名稱: {admin.get('profile', {}).get('display_name', '')}, 真實名稱: {admin.get('profile', {}).get('real_name', '')}\n"                
            say(m)
        except Exception as e:        
            say(f"非預期性問題 {e}")    

