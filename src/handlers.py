import re
import random
import os
from math import comb
from datetime import datetime, timedelta
# openai imports
from .AI_Service.openai import generate_summary as generate_summary_openai
from .AI_Service.openai import clear_conversation_history as openai_clear_conversation_history
from .AI_Service.openai import look_conversation_history as openai_look_conversation_history

# claude imports
from .AI_Service.claude import generate_summary as generate_summary_claude
from .AI_Service.claude import role_generate_response as role_generate_summary_claude

# xai imports
from .AI_Service.xai import generate_summary as generate_summary_xai
from .AI_Service.xai import analyze_sentiment as analyze_sentiment_xai 
from .AI_Service.xai import role_generate_response as role_generate_summary_xai
from .AI_Service.xai import analyze_stock as analyze_stock_xai
from .AI_Service.xai import analyze_stock_inoutpoint as analyze_stock_inoutpoint_xai


from .stability_model import get_image,get_image2
from .stock import get_stock_info
from .stock import get_historical_data


def register_handlers(app, config, db):
    
    # Call OpenAI
    @app.message(re.compile(r"!openai\s+(.+)"))
    def handle_summary_command(message, say):
        user_input = message['text'].replace('!openai', '').strip()    
        # 調用 OpenAI API
        try:        
            summary = generate_summary_openai(user_input)
            say(f"{summary}")            
        except Exception as e:        
            say(f"非預期性問題 {e}")

    # Call Claude
    @app.message(re.compile(r"!claude\s+(.+)"))
    def handle_summary_command(message, say):
        user_input = message['text'].replace('!claude', '').strip()    
        # 調用 Claude API
        try:        
            summary = generate_summary_claude(user_input)
            say(f"{summary}")            
        except Exception as e:        
            say(f"非預期性問題 {e}")        

    # Call XAI
    @app.message(re.compile(r"!xai\s+(.+)"))
    def handle_summary_command(message, say):
        user_input = message['text'].replace('!xai', '').strip()    
        # 調用 xai API
        try:        
            summary = generate_summary_xai(user_input)
            say(f"{summary}")            
        except Exception as e:        
            say(f"非預期性問題 {e}")                

    # !pk role1 role2
    @app.message(re.compile(r"^!pk\s+(\S+)\s+(\S+)", re.DOTALL))
    def handle_aipk_messages(message, say):
        match = re.match(r"^!pk\s+(\S+)\s+(\S+)", message['text'], re.DOTALL)
        if match:
            role1 = match.group(1).strip()
            role2 = match.group(2).strip()
            thread_ts = message['ts']                        
            answer = "請開始"
            # 使用不同 AI 模型生成問答內容
            for i in range(3):                
                answer = role_generate_summary_claude(role2,role1,answer ,thread_ts)
                say(text=f"*{role2}:* {answer}", thread_ts=thread_ts)
                
                answer = role_generate_summary_xai(role1,role2,answer ,thread_ts)
                say(text=f"*{role1}:* {answer}", thread_ts=thread_ts)                

    # !查股    
    @app.message(re.compile(r"^!查股\s+(.+)$"))
    def search_slock(message, say):
        msg_text = re.match(r"^!查股\s+(.+)$", message['text']).group(1).strip()
        say(get_stock_info(msg_text))

    # !技術分析    
    @app.message(re.compile(r"^!技術分析\s+(.+)$"))
    def analyze_slock(message, say):
        msg_text = re.match(r"^!技術分析\s+(.+)$", message['text']).group(1).strip()
        now_data = get_stock_info(msg_text)
        his_data = []        
        today = datetime.now()        
        for i in range(6):
            first_day_of_month = (today.replace(day=1) - timedelta(days=i*30)).strftime('%Y%m01')
            his_data.append(get_historical_data(msg_text,first_day_of_month))        
        say(analyze_stock_xai(his_data,now_data), thread_ts=message['ts'])

    # !買賣建議    
    @app.message(re.compile(r"^!買賣建議\s+(.+)$"))
    def analyze_slock_point(message, say):
        msg_text = re.match(r"^!買賣建議\s+(.+)$", message['text']).group(1).strip()
        now_data = get_stock_info(msg_text)
        his_data = []        
        today = datetime.now()        
        for i in range(3):
            first_day_of_month = (today.replace(day=1) - timedelta(days=i*30)).strftime('%Y%m01')
            his_data.append(get_historical_data(msg_text,first_day_of_month))        
        say(analyze_stock_inoutpoint_xai(his_data,now_data), thread_ts=message['ts'])

    # !熬雞湯    
    @app.message(re.compile(r"^!熬雞湯\s+(.+)$"))
    def new_philosophy_quotes(message, say):
        collection = db.philosophy_quotes
        msg_text = re.match(r"^!熬雞湯\s+(.+)$", message['text']).group(1).strip()
        existing_message = collection.find_one({"quote": msg_text})
        
        if existing_message:
            say("失敗! 已有此雞湯!")
        else:
            sentiment_result = analyze_sentiment_xai(msg_text)
            if "正能量" in sentiment_result:
                collection.insert_one({"quote": msg_text})
                say("雞湯熬煮成功!")
            else:
                say("這雞湯有毒!")

    # !喝雞湯
    @app.message(re.compile(r"^!喝雞湯$"))
    def get_philosophy_quotes(message, say):
        collection = db.philosophy_quotes
        quotes = list(collection.find())    
        # 檢查是否有可用的語錄
        if quotes:
            # 隨機選擇一條語錄
            selected_quote = random.choice(quotes)                        
            quote_text = selected_quote.get("quote", "沒有找到雞湯語錄")
            # 回應用戶
            say(quote_text)
        else:
            say("目前沒有雞湯語錄可用，請稍後再試。")

    # !雞湯菜單
    @app.message(re.compile(r"^!雞湯菜單$"))
    def get_all_philosophy_quotes(message, say):
        collection = db.philosophy_quotes
        quotes = list(collection.find())    
        # 檢查是否有可用的語錄
        if quotes:
            # 建立一個包含所有雞湯語錄的列表
            all_quotes = [f"{idx + 1}. {quote.get('quote', '沒有找到雞湯語錄')}" for idx, quote in enumerate(quotes)]
            # 將列表轉換為單一字串，換行分隔
            quotes_text = "\n".join(all_quotes)
            # 回應用戶
            say(f"以下是所有雞湯語錄:\n{quotes_text}")
        else:
            say("目前沒有雞湯語錄可用，請稍後再試。")

    # !釣魚
    @app.message(re.compile(r"^!釣魚$"))
    def get_fish(message, say):        
        folder_path=os.path.join('images','fishpond')
        channel = message['channel']
        try:
            # 獲取資料夾中的所有檔案名稱
            quotes = os.listdir(folder_path)            
            # 檢查是否有可用的檔案
            if quotes:
                if random.random() < 0.7:  # 70%的機率釣到檔案
                    # 隨機選取一個或多個檔案                    
                    selected_quote = random.choice(quotes)           
                    message = " :fishing_pole_and_fish: 你釣到了!"
                    file_path = os.path.join(folder_path, selected_quote)                                         
                    response = app.client.files_upload_v2(
                        channel=channel,
                        file=file_path,
                        initial_comment=message
                    )    
                else:
                    # 30%的機率沒釣到
                    say(" :sob: 很遺憾，你什麼也沒釣到！")
            else:
                say("資料夾是空的，沒有檔案可釣取。")
        except Exception as e:
            say(f"發生錯誤：{e}")

    # !曬卡
    @app.message(re.compile(r"^!曬卡.*"))
    def show_card(message, say):
        channel = message['channel']
        try:            
            # 1%
            if random.random() < 0.01:
                say("💔💔💔💔💔💔💔💔💔💔")
                return
            # 5%
            if random.random() < 0.05:
                # 隨機生成 1 到 8 個 :fish_body:
                num_fish_body = random.randint(0, 8)  
                fish_body = ":fish_body:" * num_fish_body
                fish = f":fish_head:{fish_body}:fish_tail:"
                say(fish + "機率:5%")
                return
            # quotes 中的可選元素
            quotes = [":rainbow:", ":poop:"]
            
            # 設置每次選擇 :rainbow: 的機率為 20%
            weights = [0.2, 0.8]
            
            # 抽選 10 次 quotes 的元素
            selected_quotes = random.choices(quotes, weights=weights, k=10)
            # 統計 :rainbow: 的出現次數
            rainbow_count = selected_quotes.count(":rainbow:")
            
            # 計算該情況的機率
            n = 10  # 總抽選次數
            p = 0.2  # 每次選擇 :rainbow: 的機率
            probability = comb(n, rainbow_count) * (p ** rainbow_count) * ((1 - p) ** (n - rainbow_count))
            
            hide_message = f"機率:{probability:.1%}"
            if rainbow_count == 10:
                hide_message = "全是 :rainbow:！你今天是🌈神！" + hide_message
            if rainbow_count == 0:
                hide_message = "全是 :poop:！你今天是💩神!" + hide_message
            # 傳送結果和機率
            say(f"{' '.join(selected_quotes)}\n {hide_message} ")
            

        except Exception as e:
            # 當發生錯誤時傳送錯誤訊息
            say(f"發生錯誤：{e}")

    # 定義一副撲克牌
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    suits = ['♣️', '♠️', '♥️', '♦️']
    deck = [f"{suit}{rank}" for rank in ranks for suit in suits]        
    # 儲存每位使用者的牌組
    user_cards = {}
    
    # 定義牌型的大小和對應的中文名稱
    hand_rankings = {
        "high_card": ("高牌", 1),
        "pair": ("一對", 2),
        "two_pair": ("兩對", 3),
        "three_of_a_kind": ("三條", 4),
        "straight": ("順子", 5),
        "flush": ("同花", 6),
        "full_house": ("葫蘆", 7),
        "four_of_a_kind": ("四條", 8),
        "straight_flush": ("同花順", 9),
        "royal_flush": ("皇家同花順", 10)
    }


    @app.message(re.compile(r"^!抽牌(?:\s*(\d+))?$"))
    def draw_cards(message, say):
        user_id = message['user']  # 獲取使用者的 ID
        # 判斷數量，若無指定則預設為 1
        match = re.search(r"^!抽牌(?:\s*(\d+))?$", message['text'])
        num_cards = int(match.group(2)) if match and match.group(2) else 1  # 預設抽 1 張牌

        # 初始化使用者的牌組
        if user_id not in user_cards:
            user_cards[user_id] = []

        # 檢查是否還有剩餘的牌
        available_cards = list(set(deck) - set(user_cards[user_id]))
        if num_cards > len(available_cards):
            say(f"剩餘牌數不足，你只能抽 {len(available_cards)} 張！", channel=channel)
            return

        # 隨機選擇多張牌
        drawn_cards = random.sample(available_cards, num_cards)
        user_cards[user_id].extend(drawn_cards)  # 記錄使用者的牌

        # 回應結果
        say(f"<@{user_id}> 抽到的是：{', '.join(drawn_cards)}", channel=channel)

    @app.message(re.compile(r"^!我的牌"))
    def show_user_cards(message, say):
        user_id = message['user']  # 獲取使用者的 ID
        channel = message['channel']

        if user_id in user_cards and user_cards[user_id]:
            cards = ", ".join(user_cards[user_id])
            say(f"<@{user_id}> 你擁有的牌是：{cards}", channel=channel)
        else:
            say(f"<@{user_id}> 你還沒有抽過任何牌！", channel=channel)

    @app.message(re.compile(r"^!我的牌型$"))
    def show_best_hand(message, say):
        user_id = message['user']  # 獲取使用者的 ID
        channel = message['channel']

        if user_id in user_cards and user_cards[user_id]:
            # 判斷使用者目前的最佳牌型
            cards = user_cards[user_id]
            hand_type, best_cards = evaluate_hand(cards)
            best_cards_display = ", ".join(best_cards)
            say(f"<@{user_id}> 最大牌型是：{hand_type}, {best_cards_display}！", channel=channel)
        else:
            say(f"<@{user_id}> 你還沒有抽過任何牌，無法判斷最大牌型！", channel=channel)      
    
    def evaluate_hand(cards):
        ranks_only = [card[:-1] for card in cards]
        suits_only = [card[-1] for card in cards]
        
        # 判斷是否為同花
        is_flush = len(set(suits_only)) == 1
        
        # 判斷是否為順子
        sorted_ranks = sorted(ranks_only, key=lambda x: ranks.index(x))
        is_straight = all(ranks.index(sorted_ranks[i]) + 1 == ranks.index(sorted_ranks[i + 1]) for i in range(len(sorted_ranks) - 1))
        
        # 判斷各種牌型 (改進處理)
        rank_counts = {rank: ranks_only.count(rank) for rank in ranks_only}
        
        if is_flush and is_straight:
            # 皇家同花順或普通同花順
            if sorted_ranks[-1] == 'A' and sorted_ranks[0] == '10':
                return hand_rankings["royal_flush"], cards
            return hand_rankings["straight_flush"], cards
        elif 4 in rank_counts.values():
            # 四條
            quad_rank = [rank for rank, count in rank_counts.items() if count == 4][0]
            best_cards = [card for card in cards if card[:-1] == quad_rank]
            return hand_rankings["four_of_a_kind"], best_cards
        elif 3 in rank_counts.values() and 2 in rank_counts.values():
            # 葫蘆
            triple_rank = [rank for rank, count in rank_counts.items() if count == 3][0]
            pair_rank = [rank for rank, count in rank_counts.items() if count == 2][0]
            best_cards = [card for card in cards if card[:-1] in [triple_rank, pair_rank]]
            return hand_rankings["full_house"], best_cards
        elif is_flush:
            # 同花
            return hand_rankings["flush"], cards
        elif is_straight:
            # 順子
            return hand_rankings["straight"], cards
        elif 3 in rank_counts.values():
            # 三條
            triple_rank = [rank for rank, count in rank_counts.items() if count == 3][0]
            best_cards = [card for card in cards if card[:-1] == triple_rank]
            return hand_rankings["three_of_a_kind"], best_cards
        elif list(rank_counts.values()).count(2) == 2:
            # 兩對
            pair_ranks = [rank for rank, count in rank_counts.items() if count == 2]
            best_cards = [card for card in cards if card[:-1] in pair_ranks]
            return hand_rankings["two_pair"], best_cards
        elif 2 in rank_counts.values():
            # 一對
            pair_rank = [rank for rank, count in rank_counts.items() if count == 2][0]
            best_cards = [card for card in cards if card[:-1] == pair_rank]
            return hand_rankings["pair"], best_cards
        else:
            # 高牌
            highest_card = max(cards, key=lambda card: ranks.index(card[:-1]))
            return hand_rankings["high_card"], [highest_card]


    # !add 指令
    @app.message(re.compile(r"^!add\s+(.+)\s+([\s\S]+)", re.DOTALL))
    def handle_add_message(message, say):
        match = re.match(r"^!add\s+(.+)\s+([\s\S]+)", message['text'], re.DOTALL)
        if match:
            msg_text = match.group(1).strip()  
            # 保留response_text中的原始格式，包括換行符
            response_text = match.group(2)  
            add_commit(msg_text, response_text, say)

    # !show 指令
    @app.message(re.compile(r"^!show$"))
    def handle_show(message, say):        
        collection = db.slock_bot_commit
        messages = collection.find({"is_sys": "N" })
        commit = "自訂指令:\n"
        for msg in messages:        
            commit += f"{msg['message']} => {msg['say']}\n"

        #messages = collection.find({"is_sys": "Y" })
        #commit += "管理員指令:\n"
        #for msg in messages:        
            #commit += f"{msg['message']} => {msg['say']}\n"
        say(commit)         

    # !remove 指令
    @app.message(re.compile(r"^!remove\s+(.+)$"))
    def handle_remove_message(message, say):
        match = re.match(r"^!remove\s+(.+)$", message['text'])
        if match:
            msg_text = match.group(1).strip()
            remove_commit(msg_text, say)        

    # Bot被提及回 "蛤?"
    @app.event("app_mention")
    def handle_app_mention_events(body, say):
        say(f"蛤?")    
    
    # 抽選人員Tag" 
    @app.message(re.compile(r"^誰.*"))
    def rand_tag_user(message, say, client):
        # 取當前用戶列表
        channel_id = message['channel']
        result = client.conversations_members(channel=channel_id)
        members = result['members']    

        # 隨機抽選用户
        if members:
            random_user = random.choice(members)
            user_info = client.users_info(user=random_user)
            user_name = user_info['user']['real_name'] 
            # 解析 "誰" 後面的所有字串 
            text = message['text']
            additional_text = text[text.index("誰") + 1:].strip() 
            # 顯示用戶名稱和附加字串 
            say(f" {user_name} {additional_text} !")                        
    
    #!畫
    @app.message(re.compile(r"^!畫\s+(.+)$"))
    def create_image(message, say):        
        channel = message['channel']
        msg_text = re.match(r"^!畫\s+(.+)$", message['text']).group(1).strip()
        say_text, file_name = get_image(msg_text)                
        #say_text, file_name = get_image2(msg_text)                
        send_image(channel, say_text, say, file_name)

    #!clearai
    @app.message(re.compile(r"^!clearai$"))
    def clearai(message, say):        
        try:
            openai_clear_conversation_history()
            say("AI聊天紀錄清除成功!")
        except Exception as e:
            say(f"AI聊天紀錄清除錯誤!{e}")
    #!lookai        
    @app.message(re.compile(r"^!lookai$"))
    def lookai(message, say):        
        try:
            his = openai_look_conversation_history()
            say(his)
        except Exception as e:
            say(f"AI聊天紀錄查看錯誤!{e}")

    # DB 新增處理    
    def add_commit(message_text, response_text, say):
        try:        
            collection = db.slock_bot_commit   
            if re.search(r"!.*", message_text):
                say("[!開頭] 保留字不可使用!")
                return  
            # 檢查是否已有相同的 message
            existing_message = collection.find_one({"message": message_text, "is_sys": "N" })
            
            if existing_message:
                # 更新現有指令            
                say("已有相關指令!")
            else:
                # 新增指令
                collection.insert_one({"message": message_text, "say": response_text, "is_sys": "N"})
                say("指令已新增!")            
        except Exception as e:
            # 異常處理
            print(f"Error inserting/updating document: {e}")
            # 發生例外錯誤!
            say("發生例外錯誤!")

    # DB 刪除處理
    def remove_commit(message_text, say):
        try:
            collection = db.slock_bot_commit
            # 刪除指令
            result = collection.delete_many({"message": message_text, "is_sys": "N"})
            if result.deleted_count > 0:
                say("指令已刪除!")                        
            else:
                say("未找到相關指令!")
        except Exception as e:
            # 異常處理
            print(f"Error deleting document: {e}")
            say("發生例外錯誤!")

    # 發送圖片函數
    def send_image(channel_id, message, say, file_path=None):        
        if not file_path:  # 检查 file_path 是否为空或 None
            say(message)
            return
        try:
            imagefile = os.path.join('images',file_path)
            if os.path.isfile(imagefile):                
                response = app.client.files_upload_v2(
                    channel=channel_id,
                    file=os.path.join('images',file_path),
                    initial_comment=message
                )                
            else:
                say(f"{message} \n找不到{file_path}" )                
        except Exception as e:
            print(f"Error send_image uploading file ")     
        
    #關鍵字
    @app.message(re.compile("(.*)"))
    def handle_message(message,say):        
        text = message['text']
        if re.search(r"^!.*", text):
            say("目前無此指令功能!")            
            return        
        channel = message['channel']        
        collection = db.slock_bot_commit
        keyword_all = collection.find()        
        # 遍歷每條資料
        for doc in keyword_all:            
            message = doc.get('message')
            if re.search(re.escape(message), text):                            
                file_path = doc.get('file')
                send_image(channel, doc['say'],say, file_path)            
                return

