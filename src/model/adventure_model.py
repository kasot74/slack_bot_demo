import re
import ast
from slack_bolt import App
from ..AI_Service.xai import generate_summary

COMMANDS_HELP = [
    ("!冒險", "開始文字遊戲"),
    ("!重新生成冒險 [主題]", "用 AI 生成全新冒險劇情，預設主題為「工程師社畜冒險」"),
    ("!重來", "重新開始遊戲"),
    ("!選 A/B/C", "做出你的選擇，繼續劇情"),
]

# #格式範例
SCENES = {
    "scene1": {
        "text": (
            "🧑‍💼 你是一名工程師，剛吃完早餐腸胃微妙。\n"
            "老闆突然傳訊：「10點要報告喔🥰」\n"
            "你該怎麼辦？\n👉 A. 裝死滑手機\n👉 B. 亂做 KPI\n👉 C. 傳訊 GPT"
        ),
        "choices": {
            "A": {"next": "scene_ig", "score": 2, "text": "你瘋狂滑貓貓影片…結果被老闆 tag 進會議"},
            "B": {"next": "scene_kpi", "score": 1, "text": "你開 Excel 假資料全開，還加圖表裝專業"},
            "C": {"next": "scene_gpt", "score": 0, "text": "GPT 說：『你也該學會獨立了』"}
        }
    },
    "scene_kpi": {
        "text": (
            "老闆對 KPI 滿意，隔壁資安部卻來盯你電腦。\n"
            "你要：\n👉 A. 請病假潛逃\n👉 B. 寫 3000 字檢討文\n👉 C. 說報告是 GPT 寫的"
        ),
        "choices": {
            "A": {"next": "scene_sick", "score": 1, "text": "你傳簡訊：『我發燒38.7°C』——老闆立刻來家訪"},
            "B": {"next": "scene_report", "score": 2, "text": "你寫到凌晨三點，老闆留言『寫得像小說👍』"},
            "C": {"next": "scene_bot", "score": 3, "text": "GPT 被你拉下水，它升職，你自動離職"}
        }
    },
    "scene_gpt": {
        "text": (
            "GPT 把你推給 Copilot。\n你現在要：\n👉 A. 寫報告靠意志力\n👉 B. 泡咖啡當沒看到訊息\n👉 C. 開始訓練自己的 AI 替身"
        ),
        "choices": {
            "A": {"next": "ending_ok", "score": 1, "text": "你寫出一份『中庸之道的報告』，被稱為穩健派"},
            "B": {"next": "ending_cafe", "score": 0, "text": "老闆來泡咖啡，順便叫你開會 ☕"},
            "C": {"next": "ending_clone", "score": 3, "text": "你完成一個自動回 Slack 的機器人，自此沒人再找你開會…"}
        }
    },
    "scene_ig": {
        "text": (
            "你被螢幕投影在會議大螢幕，畫面是你看『貓咪撞電風扇』。\n\n👉 A. 說是朋友帳號\n👉 B. 拔網路裝斷線\n👉 C. 微笑揮手：Hi 👋"
        ),
        "choices": {
            "A": {"next": "scene_punish", "score": 2, "text": "老闆直接拿你照片做成週會海報"},
            "B": {"next": "scene_punish", "score": 1, "text": "你斷網成功，但 Slack 自動請假信寄出"},
            "C": {"next": "scene_punish", "score": 0, "text": "你表情包化，全公司都在用你頭像"}
        }
    },
    "scene_punish": {
        "text": (
            "你現在已是 Slack 表情界的紅人。\n老闆邀你主持下週的部門全體會議。\n\n你要：\n👉 A. 認真準備簡報\n👉 B. 找 intern 頂替你\n👉 C. 開始訓練 GPT 模擬你上台"
        ),
        "choices": {
            "A": {"next": "ending_star", "score": 2, "text": "會議主持超順，你成為部門團建負責人。Good Luck."},
            "B": {"next": "ending_fired", "score": 3, "text": "實習生直接爆料你薪資＋迷因圖，全公司都知道"},
            "C": {"next": "ending_ghost", "score": 4, "text": "你從此隱居 Slack 頻道，只剩 emoji 回覆 👻"}
        }
    },
    "scene_report": {
        "text": (
            "老闆對你的檢討文滿意，給你新任務：再寫 10 份部門 KPI 提案 😵\n\n你要：\n👉 A. 把老闆也拉進共筆\n👉 B. 複製貼上舊的騙過去\n👉 C. 靜靜開啟 Copilot"
        ),
        "choices": {
            "A": {"next": "ending_fusion", "score": 2, "text": "老闆開始修改你的文件，意外做出部門新 Slogan：『工作無限，人類無眠』"},
            "B": {"next": "ending_loop", "score": 3, "text": "你在回圈中活了三週，開始分不清第幾版"},
            "C": {"next": "ending_ghost", "score": 4, "text": "你從此只用 Copilot 工作，自身化為 Slack 雲端幽靈 👻"}
        }
    }
}
#格式範例
ENDING = {
    "free": {
        "score_range": (None, 1),
        "text": "🕊️【自由人】你悟了！隔天辭職改行當塔羅師。"
    },
    "normal": {
        "score_range": (2, 3),
        "text": "😐【穩健社畜】你撐住了，也失去了甚麼。"
    },
    "senior": {
        "score_range": (4, 5),
        "text": "🥵【高階社畜】你的靈魂與工時等價交換，進入資深圈。"
    },
    "ghost": {
        "score_range": (6, None),
        "text": "👻【會議幽靈】你已被公司吸收成 Slack 精靈的一部分。"
    }
}



def get_ending(score):
    for ending in ENDING.values():
        min_score, max_score = ending["score_range"]
        if (min_score is None or score >= min_score) and (max_score is None or score <= max_score):
            return ending["text"]
    return "開放結局"

user_game_state = {}

def register_adventure_handlers(app: App, config, db):

    def get_scenes_and_ending_by_ai(say,custom_topic="工程師社畜冒險"):
        
        say(f"正在用 AI 生成全新冒險劇情（主題：{custom_topic}），請稍候...")

        # 動態生成 prompt
        scenes_prompt = (
            f"請幫我生成一個{custom_topic}的文字遊戲場景資料，"
            "格式為 Python 字典，key 為場景(請用 scene1,scene2 依序當場景的KEY) id，value 為 dict，"
            "範例格式  scene1: : {'text': '劇情描述並提供 A/B/C選項', 'choices': {'A': {'next': 'scene2', 'score': 10, 'text': '選項描述'}, 'B': {'next': 'scene3', 'score': 5, 'text': '選項描述'}, ...}}。"   
            "每個場景包含 'text'（劇情描述並 提供 A/B/C選項） 與 'choices'（A/B/C 選項結果，"
            "每個選項有 next、score、text）。請給 12 個場景，且非必要不要讓場景透過選擇重複。如果選擇會導致結局，請在 'choices' 中包含 'next' 指向結局場景 end"
            "我會將你的輸出直接用於 Python 程式中，請確保格式正確 ast.literal_eval() 可以解析，內容與選項請適當使用換行符號換行 "
        )
        ending_prompt = (
            f"請幫我生成 4 種{custom_topic}結局，格式為 Python 字典，"
            "每個結局包含 'score_range'（tuple，最低分數, 最高分數），"
            "與 'text'（格式是 [結局名稱] [結局描述] 有趣一點）。"            
            "我會將你的輸出直接用於 Python 程式中，請確保格式正確 ast.literal_eval() 可以解析，內容請適當使用換行符號換行"
        )

        # 取得 XAI 回覆
        scenes_code = generate_summary(scenes_prompt)
        ending_code = generate_summary(ending_prompt)
        
        try:
            new_scenes = ast.literal_eval(scenes_code)
        except Exception:
            say("❌ 劇情生成失敗，請稍後再試或換個主題。")
            return
        try:
            new_ending = ast.literal_eval(ending_code)
        except Exception:
            say("❌ 結局生成失敗，請稍後再試或換個主題。")
            return

        global SCENES, ENDING
        SCENES = new_scenes
        ENDING = new_ending
        say("✅ 已用 AI 生成全新冒險劇情！輸入 `!冒險` 開始你的新旅程吧！")

    @app.message(re.compile(r"^!重新生成冒險\s*(.*)$"))
    def scenes_game(message, say, context):
        # 取得使用者輸入的自訂主題（如有）
        get_scenes_and_ending_by_ai(say,context["matches"][0].strip() if context["matches"] else "工程師社畜冒險")
        
    @app.message("!冒險")
    def start_game(message, say):        

        user_id = message["user"]
        user_game_state[user_id] = {
            "scene": "scene1",
            "score": 0,
            "log": []
        }
        say(SCENES["scene1"]["text"])

    @app.message("!重來")
    def restart_game(message, say):
        user_id = message["user"]
        user_game_state[user_id] = {
            "scene": "scene1",
            "score": 0,
            "log": []
        }
        say("🔁 時間回朔！遊戲重置囉～輸入 `!冒險` 再試一次！")

    @app.message(re.compile(r"^!選\s+([ABCabc])$"))
    def choose_option(message, say, context):
        user_id = message["user"]
        choice = context["matches"][0].upper()
        state = user_game_state.get(user_id)

        if not state:
            say("請先輸入 `!冒險` 開始遊戲～")
            return

        scene_id = state["scene"]
        scene = SCENES.get(scene_id)
        if not scene or choice not in scene["choices"]:
            say("請輸入正確選項（A/B/C）")
            return

        # 處理選擇
        selected = scene["choices"][choice]
        response = selected["text"]
        next_scene = selected["next"]
        add_score = selected["score"]

        state["score"] += add_score
        state["log"].append((scene_id, choice))
        state["scene"] = next_scene

        # 是否為結局場景
        if not SCENES.get(next_scene):
            ending_text = get_ending(state["score"])
            say(f"{response}\n\n🏁 遊戲結局：\n{ending_text}\n\n輸入 `!重來` 再體驗不同冒險！")
            return

        # 下一關劇情
        next_text = SCENES[next_scene]["text"]
        say(f"{response}\n\n📘 接下來...\n{next_text}")
