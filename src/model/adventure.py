from slack_bolt import App
import re

COMMANDS_HELP = [
    ("!冒險", "開始文字遊戲"),
    ("!重來", "重新開始遊戲"),
    ("!選 A/B/C", "做出你的選擇，繼續劇情"),
]

# 全部場景定義
SCENES = {
    "start": {
        "text": (
            "🧑‍💼 你是阿明，工程師一枚，剛吃完早餐腸胃微妙。\n"
            "Slack 上老闆傳來訊息：「10點要報告喔 🥰」\n"
            "你現在該怎麼辦？\n"
            "👉 A. 繼續裝死滑手機\n"
            "👉 B. 開始亂做 KPI 報告\n"
            "👉 C. 傳訊息求救 GPT"
        ),
        "choices": {
            "A": {"next": "scene_ig", "score": 2, "text": "你看了一輪貓貓影片，老闆悄悄把你拖進會議…"},
            "B": {"next": "scene_kpi", "score": 1, "text": "你用 Excel 隨機數字唬了一頁 KPI，還加了彩色圖表。"},
            "C": {"next": "scene_gpt", "score": 0, "text": "GPT 說它太累，請你打給 Copilot 換個支援（真實）"}
        }
    },
    "scene_kpi": {
        "text": (
            "你交出 KPI 報告，老闆竟然滿意，但資安部的眼神不太對勁…\n"
            "接下來你要怎麼做？\n"
            "👉 A. 裝病請假\n"
            "👉 B. 承認錯誤主動檢討\n"
            "👉 C. 把鍋甩給 AI"
        ),
        "choices": {
            "A": {"next": "ending_sick", "score": 1, "text": "你傳訊說你得了 Slack 過敏症，老闆親自敲門來看你…"},
            "B": {"next": "ending_report", "score": 2, "text": "你寫了三千字檢討文，老闆要求你每天寫一篇…"},
            "C": {"next": "ending_bot", "score": 3, "text": "你說報告是 GPT 寫的，結果它被升職，你原地失業。"}
        }
    },
    "scene_ig": {
        "text": (
            "你刷 IG 被老闆發現，會議現場你正被全螢幕放映。\n"
            "你要怎麼挽救？\n"
            "👉 A. 假裝那是你同學的帳號\n"
            "👉 B. 快速退出 Slack 並拔網路\n"
            "👉 C. 微笑揮手說 Hi 👋"
        ),
        "choices": {
            "A": {"next": "ending_shame", "score": 2, "text": "沒人相信你，還被截圖做成週會教材。"},
            "B": {"next": "ending_offline", "score": 1, "text": "你斷網後 Slack 自動幫你請假一天，但也自動寄信給老闆…"},
            "C": {"next": "ending_meme", "score": 0, "text": "你的微笑成為 Slack 表情貼圖，意外爆紅 🎉"}
        }
    },
    "scene_gpt": {
        "text": (
            "GPT 說它不想上班，要你自己解決。\n"
            "那你現在…？\n"
            "👉 A. 開始寫報告（誠心）\n"
            "👉 B. 把責任推回老闆（大膽）\n"
            "👉 C. 去泡咖啡當沒事"
        ),
        "choices": {
            "A": {"next": "ending_ok", "score": 1, "text": "你邊聽 ASMR 邊做報告，效率意外不錯。"},
            "B": {"next": "ending_fired", "score": 3, "text": "你直接 @ 老闆說：『你也沒交代清楚吧？』 你獲得自由。"},
            "C": {"next": "ending_cafe", "score": 0, "text": "你轉身泡咖啡，老闆進來問你也給他一杯 ☕"}
        }
    },
}

# 結局文字依照社畜值
def get_ending(score):
    if score <= 1:
        return "🕊️【自由人】你悟了！隔天辭職改行當塔羅師。"
    elif score <= 3:
        return "😐【穩健社畜】你撐住了，也失去了甚麼。"
    elif score <= 5:
        return "🥵【高階社畜】你的靈魂與工時等價交換，進入資深圈。"
    else:
        return "👻【會議幽靈】你已被公司吸收成 Slack 精靈的一部分。"

user_game_state = {}

def register_adventure_handlers(app: App, config, db):
    @app.message("!冒險")
    def start_game(message, say):
        user_id = message["user"]
        user_game_state[user_id] = {
            "scene": "start",
            "score": 0,
            "log": []
        }
        say(SCENES["start"]["text"])

    @app.message("!重來")
    def restart_game(message, say):
        user_id = message["user"]
        user_game_state[user_id] = {
            "scene": "start",
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
            say(f"{response}\n\n🏁 遊戲結局：\n{ending_text}\n\n輸入 `!重來` 再體驗不同人生！")
            return

        # 下一關劇情
        next_text = SCENES[next_scene]["text"]
        say(f"{response}\n\n📘 接下來...\n{next_text}")
