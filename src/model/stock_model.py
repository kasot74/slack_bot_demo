import re
from ..stock import get_stock_info, get_historical_data

COMMANDS_HELP = [
    ("!查股 股票代碼", "查詢指定股票即時資訊（支援上市/上櫃，盤後自動改用收盤快照）"),
    ("!查股歷史 股票代碼 年月", "查詢上市股月歷史資料，年月格式 YYYYMM（例：!查股歷史 2330 202506）"),
]


def register_stock_handlers(app, config, db):

    # !查股 <代碼>
    @app.message(re.compile(r"^!查股\s+(\S+)$"))
    def search_stock(message, say):
        code = re.match(r"^!查股\s+(\S+)$", message['text']).group(1).strip()
        say(get_stock_info(code))

    # !查股歷史 <代碼> [年月]
    # 年月可省略，省略時使用當月
    @app.message(re.compile(r"^!查股歷史\s+(\S+)(?:\s+(\d{6}))?$"))
    def search_stock_history(message, say):
        m = re.match(r"^!查股歷史\s+(\S+)(?:\s+(\d{6}))?$", message['text'])
        code = m.group(1).strip()
        from datetime import datetime
        date = m.group(2) or datetime.now().strftime('%Y%m')
        say(get_historical_data(code, date))
