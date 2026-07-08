import requests
import threading
import time
from datetime import datetime

# ──────────────────────────────────────────────────────────────────────────────
# 快取設定（避免每次查詢都打 OpenAPI）
# ──────────────────────────────────────────────────────────────────────────────
_snapshot_cache = {
    'tse': {'data': {}, 'ts': 0},
    'otc': {'data': {}, 'ts': 0},
}
_cache_lock = threading.Lock()
CACHE_TTL = 300  # 快照資料快取 5 分鐘

# ──────────────────────────────────────────────────────────────────────────────
# 公用工具
# ──────────────────────────────────────────────────────────────────────────────
def _fmt(v, suffix=''):
    """把 '-' / '--' / None / '' 統一顯示為 ---"""
    if v is None or str(v).strip() in ('-', '--', ''):
        return '---'
    return f"{v}{suffix}"


def _change_str(close_val, change_val):
    """產生『漲跌金額 (漲跌%)』字串與方向 emoji"""
    try:
        c = float(change_val)
        close = float(close_val)
        prev = close - c
        pct = (c / prev * 100) if prev else 0
        arrow = '📈' if c > 0 else ('📉' if c < 0 else '➡️')
        return arrow, f"{c:+.2f} 元 ({pct:+.2f}%)"
    except Exception:
        return '', _fmt(change_val)


# ──────────────────────────────────────────────────────────────────────────────
# 即時報價（mis.twse.com.tw，每 5 秒更新，盤中使用）
# ──────────────────────────────────────────────────────────────────────────────
def _fetch_realtime(code: str, market: str):
    """
    向 mis.twse.com.tw 查詢即時報價。
    market: 'tse'（上市）或 'otc'（上櫃）
    回傳 dict 或 None（查無資料 / 未開盤）
    """
    url = (
        f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
        f"?json=1&delay=0&ex_ch={market}_{code}.tw"
    )
    try:
        resp = requests.get(url, timeout=6, headers={'Referer': 'https://mis.twse.com.tw'})
        data = resp.json()
        arr = data.get('msgArray', [])
        if not arr:
            return None
        s = arr[0]
        # z = 最新成交價；若 z 與 y（昨收）皆為 '-'，視為無效資料
        if s.get('z', '-') in ('-', '--') and s.get('y', '-') in ('-', '--'):
            return None
        return s
    except Exception:
        return None


def _format_realtime(s: dict) -> str:
    """格式化即時報價"""
    market_label = '上市(TSE)' if s.get('ex') == 'tse' else '上櫃(OTC)'
    name = s.get('nf') or s.get('n') or '?'
    code = s.get('ch', '?')

    z = _fmt(s.get('z'))          # 最新成交價
    y = s.get('y', '-')           # 昨收
    arrow, chg = _change_str(z, float(z) - float(y)) if z != '---' and _fmt(y) != '---' else ('', '---')

    bids = _fmt(s.get('b', '-')).replace('_', ' / ')
    asks = _fmt(s.get('a', '-')).replace('_', ' / ')

    lines = [
        f"{arrow} *{name}* ({code}) [{market_label}]",
        f"成交價：*{z}* 元　　漲跌：{chg}",
        f"開盤：{_fmt(s.get('o'))}　最高：{_fmt(s.get('h'))}　最低：{_fmt(s.get('l'))}",
        f"昨收：{_fmt(y)}　漲停：{_fmt(s.get('u'))}　跌停：{_fmt(s.get('w'))}",
        f"成交量：{_fmt(s.get('v'))} 張　　成交時間：{_fmt(s.get('t'))}",
        f"委買(五檔)：{bids}",
        f"委賣(五檔)：{asks}",
        f"_（來源：證交所即時報價）_",
    ]
    return '\n'.join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# 日收盤快照（盤後 / 查無即時資料時的 fallback）
# ──────────────────────────────────────────────────────────────────────────────
def _load_snapshot(market: str) -> dict:
    """
    載入整市場快照並快取。
    TSE → openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL
    OTC → www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes
    回傳 {股票代碼: 原始 dict}
    """
    with _cache_lock:
        cache = _snapshot_cache[market]
        if time.time() - cache['ts'] < CACHE_TTL and cache['data']:
            return cache['data']

    if market == 'tse':
        url = 'https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL'
        code_key = 'Code'
    else:
        url = 'https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes'
        code_key = 'SecuritiesCompanyCode'

    try:
        resp = requests.get(url, timeout=10)
        rows = resp.json()
        data = {str(r.get(code_key, '')).strip(): r for r in rows if r.get(code_key)}
        with _cache_lock:
            _snapshot_cache[market]['data'] = data
            _snapshot_cache[market]['ts'] = time.time()
        return data
    except Exception:
        return {}


def _format_snapshot_tse(code: str, s: dict) -> str:
    """格式化 TSE 日收盤快照"""
    name = s.get('Name', '?')
    close = s.get('ClosingPrice', '-')
    change = s.get('Change', '-')
    arrow, chg = _change_str(close, change)
    date = s.get('Date', '')
    # 民國年 → 西元年（格式 YYMMDD）
    if len(date) == 7:
        year = int(date[:3]) + 1911
        date = f"{year}/{date[3:5]}/{date[5:]}"

    lines = [
        f"{arrow} *{name}* ({code}) [上市(TSE)]",
        f"收盤價：*{_fmt(close)}* 元　　漲跌：{chg}",
        f"開盤：{_fmt(s.get('OpeningPrice'))}　最高：{_fmt(s.get('HighestPrice'))}　最低：{_fmt(s.get('LowestPrice'))}",
        f"成交量：{_fmt(s.get('TradeVolume'))} 股　　成交筆數：{_fmt(s.get('Transaction'))}",
        f"_（資料日期：{date}，非即時報價）_",
    ]
    return '\n'.join(lines)


def _format_snapshot_otc(code: str, s: dict) -> str:
    """格式化 OTC 日收盤快照"""
    name = s.get('CompanyName', '?')
    close = s.get('Close', '-')
    change = s.get('Change', '-')
    arrow, chg = _change_str(close, change)
    date = s.get('Date', '')
    if len(date) == 7:
        year = int(date[:3]) + 1911
        date = f"{year}/{date[3:5]}/{date[5:]}"

    lines = [
        f"{arrow} *{name}* ({code}) [上櫃(OTC)]",
        f"收盤價：*{_fmt(close)}* 元　　漲跌：{chg}",
        f"開盤：{_fmt(s.get('Open'))}　最高：{_fmt(s.get('High'))}　最低：{_fmt(s.get('Low'))}",
        f"成交量：{_fmt(s.get('TradingShares'))} 股",
        f"漲停：{_fmt(s.get('NextLimitUp'))}　跌停：{_fmt(s.get('NextLimitDown'))}",
        f"_（資料日期：{date}，非即時報價）_",
    ]
    return '\n'.join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# 對外主函式
# ──────────────────────────────────────────────────────────────────────────────
def get_stock_info(stock_code: str) -> str:
    """
    查詢台股即時資訊，自動判斷上市 / 上櫃。
    優先使用即時報價；盤後或查無即時資料時改用日收盤快照。
    """
    code = stock_code.strip()

    # 1. 嘗試即時報價（上市 → 上櫃）
    for market in ('tse', 'otc'):
        s = _fetch_realtime(code, market)
        if s:
            return _format_realtime(s)

    # 2. 即時資料不可用 → 改用日收盤快照（上市 → 上櫃）
    tse_snap = _load_snapshot('tse')
    if code in tse_snap:
        return _format_snapshot_tse(code, tse_snap[code])

    otc_snap = _load_snapshot('otc')
    if code in otc_snap:
        return _format_snapshot_otc(code, otc_snap[code])

    return f"❌ 找不到股票代碼 `{code}`，請確認代碼正確（上市股或上櫃股）。"


# ──────────────────────────────────────────────────────────────────────────────
# 歷史資料（TWSE afterTrading API）
# ──────────────────────────────────────────────────────────────────────────────
def get_historical_data(stock_code: str, date: str) -> str:
    """
    查詢 TSE 上市股票月歷史資料。
    Args:
        stock_code: 股票代碼（例如 '2330'）
        date: 年月（格式 'YYYYMM'，例如 '202506'）
    """
    # 補齊為 YYYYMM01
    if len(date) == 6:
        date = date + '01'

    url = (
        f"https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY"
        f"?date={date}&stockNo={stock_code}&response=json"
    )
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
    except Exception as e:
        return f"❌ 查詢失敗：{e}"

    if not data or data.get('stat') not in ('OK', 'ok'):
        stat = data.get('stat', '無回應') if data else '無回應'
        return f"❌ 查無資料（{stat}），請確認股票代碼與日期是否正確。"

    rows = data.get('data', [])
    if not rows:
        return "❌ 該月份無交易資料。"

    title = data.get('title', f'{stock_code} 歷史資料')
    lines = [f"📊 *{title}*"]
    lines.append("日期　　　開盤　最高　最低　收盤　漲跌")
    for r in rows:
        # r = [日期, 成交股數, 成交金額, 開盤, 最高, 最低, 收盤, 漲跌, 筆數]
        lines.append(
            f"{r[0]}　{r[3]:>6}　{r[4]:>6}　{r[5]:>6}　{r[6]:>6}　{r[7]:>7}"
        )
    return '\n'.join(lines)


def get_current_date():
    """取得目前的日期與時間。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
