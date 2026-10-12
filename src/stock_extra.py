"""
!查股 補充資訊：今年漲幅、估值、基本面、三大法人買賣超、基本面判讀。
資料來源皆為證交所 / 櫃買中心公開資料；任何一段抓不到都只略過該段，不影響主報價。
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

TW = timezone(timedelta(hours=8))
HEADERS = {'User-Agent': 'Mozilla/5.0'}

SHORT_DAYS = 5     # 近 5 個交易日
LONG_DAYS = 30     # 近 30 個交易日
LOOKBACK_DAYS = 70  # 往回找 30 個交易日最多看的日曆天數
PE_HIGH = 45       # 本益比高於此值視為估值偏高

_lock = threading.Lock()
_cache = {}  # key -> (timestamp, value)


def _cached(key, ttl, loader):
    """簡單的記憶體快取；ttl=None 代表永久。loader 回傳 None 代表失敗，不快取。"""
    with _lock:
        hit = _cache.get(key)
        if hit and (ttl is None or time.time() - hit[0] < ttl):
            return hit[1]
    value = loader()
    if value is not None:
        with _lock:
            _cache[key] = (time.time(), value)
    return value


def _get_json(url, timeout=20, retries=2):
    for i in range(retries + 1):
        try:
            resp = requests.get(url, timeout=timeout, headers=HEADERS)
            return resp.json()
        except Exception:
            if i < retries:
                time.sleep(1.5)
    return None


def _num(x):
    try:
        return float(str(x).replace(',', '').strip())
    except Exception:
        return None


def _int(x):
    v = _num(x)
    return int(v) if v is not None else 0


# ──────────────────────────────────────────────────────────────────────────────
# 資料載入（整市場一次載入後快取）
# ──────────────────────────────────────────────────────────────────────────────
def _load_pe(market):
    def load():
        if market == 'tse':
            rows = _get_json('https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL')
            if not rows:
                return None
            return {r['Code']: (r.get('PEratio'), r.get('PBratio'), r.get('DividendYield')) for r in rows}
        rows = _get_json('https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis')
        if not rows:
            return None
        return {r['SecuritiesCompanyCode']: (r.get('PriceEarningRatio'), r.get('PriceBookRatio'), r.get('YieldRatio'))
                for r in rows}
    return _cached(('pe', market), 3600, load) or {}


def _load_revenue(market):
    def load():
        url = ('https://openapi.twse.com.tw/v1/opendata/t187ap05_L' if market == 'tse'
               else 'https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap05_O')
        rows = _get_json(url, timeout=40)
        if not rows:
            return None
        return {r['公司代號']: r for r in rows}
    return _cached(('rev', market), 6 * 3600, load) or {}


def _load_income(market):
    def load():
        if market == 'tse':
            rows = _get_json('https://openapi.twse.com.tw/v1/opendata/t187ap06_L_ci', timeout=60)
            key = '公司代號'
        else:
            rows = _get_json('https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap06_O_ci', timeout=60)
            key = 'SecuritiesCompanyCode'
        if not rows:
            return None
        return {r[key]: r for r in rows}
    return _cached(('inc', market), 6 * 3600, load) or {}


def _load_year_end(market, year):
    """去年最後一個交易日的收盤價 {代號: 收盤價}"""
    def load():
        day = datetime(year, 12, 31)
        for _ in range(12):
            if day.weekday() < 5:
                if market == 'tse':
                    d = _get_json('https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX'
                                  f'?date={day:%Y%m%d}&type=ALLBUT0999&response=json', timeout=40)
                    for t in (d or {}).get('tables', []):
                        if '每日收盤行情' in t.get('title', '') and t.get('data'):
                            idx = t['fields'].index('收盤價')
                            return {r[0]: _num(r[idx]) for r in t['data']}
                else:
                    d = _get_json('https://www.tpex.org.tw/www/zh-tw/afterTrading/otc'
                                  f'?date={day:%Y/%m/%d}&type=EW&response=json', timeout=40)
                    tables = (d or {}).get('tables') or []
                    if tables and tables[0].get('data'):
                        return {r[0]: _num(r[2]) for r in tables[0]['data']}
            day -= timedelta(days=1)
        return None
    return _cached(('ye', market, year), None, load) or {}


def _load_inst_day(market, day):
    """單日三大法人買賣超 {代號: (外資, 投信, 自營商, 合計)}，單位：股。休市日回傳 {}。"""
    today = datetime.now(TW).date()

    def load():
        if market == 'tse':
            d = _get_json('https://www.twse.com.tw/rwd/zh/fund/T86'
                          f'?date={day:%Y%m%d}&selectType=ALLBUT0999&response=json', timeout=30)
            if d is None:
                return None
            if d.get('stat') != 'OK':
                return {} if day < today else None
            return {r[0]: (_int(r[4]) + _int(r[7]), _int(r[10]), _int(r[11]), _int(r[18]))
                    for r in d.get('data', []) if len(r) >= 19}
        d = _get_json('https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade'
                      f'?type=Daily&sect=AL&date={day:%Y/%m/%d}&response=json', timeout=30)
        if d is None:
            return None
        tables = d.get('tables') or []
        if str(d.get('stat', '')).lower() != 'ok' or not tables or not tables[0].get('data'):
            return {} if day < today else None
        return {r[0]: (_int(r[10]), _int(r[13]), _int(r[22]), _int(r[23]))
                for r in tables[0]['data'] if len(r) >= 24}
    # 今天的資料盤後才會公布，過去的日子結果不會再變
    return _cached(('inst', market, day), None if day < today else 600, load)


def _inst_history(market, code):
    """回傳最近 LONG_DAYS 個交易日的 [(日期, (外資, 投信, 自營商, 合計))]，新到舊。"""
    today = datetime.now(TW).date()
    days = [today - timedelta(days=i) for i in range(LOOKBACK_DAYS)
            if (today - timedelta(days=i)).weekday() < 5]
    # 先確保最近的日子載入（分批並行，避免一次打太多請求被限流）
    out = []
    i = 0
    while len(out) < LONG_DAYS and i < len(days):
        batch = days[i:i + 6]
        i += 6
        with ThreadPoolExecutor(max_workers=3) as ex:
            results = list(ex.map(lambda d: _load_inst_day(market, d), batch))
        for d, res in zip(batch, results):
            if res and len(out) < LONG_DAYS:
                out.append((d, res.get(code, (0, 0, 0, 0))))
    return out


# ──────────────────────────────────────────────────────────────────────────────
# 區塊組裝
# ──────────────────────────────────────────────────────────────────────────────
def _signed(n_shares):
    n = round(n_shares / 1000)
    return f"{n:+,}" if n else '0'


def _season_label(season):
    return {'1': '第一季', '2': '上半年累計', '3': '前三季累計', '4': '全年'}.get(str(season), f'第{season}季')


def _judge(eps, op_margin, rev_yoy, cum_yoy, pe):
    """回傳 (標籤, 原因) 或 None（資料不足不判讀）"""
    if eps is None or op_margin is None:
        return None
    reasons = []
    if eps <= 0:
        reasons.append('虧損')
    if op_margin < 0:
        reasons.append('本業虧損')
    if rev_yoy is not None and rev_yoy < 0:
        reasons.append('單月營收年減')
    if cum_yoy is not None and cum_yoy < 0:
        reasons.append('累計營收年減')
    if reasons:
        return '⚠️ 有疑慮', '、'.join(reasons)
    if pe is not None and pe > PE_HIGH:
        return '💰 估值偏高', f'本益比 {pe:g} > {PE_HIGH}'
    return '✅ 基本面扎實', ''


def build_extra(code, market, price):
    """
    產生補充資訊文字。market: 'tse' / 'otc'；price: 目前價（或收盤價），可為 None。
    任何錯誤都回傳空字串，不影響主報價。
    """
    try:
        return _build_extra(code, market, price)
    except Exception:
        return ''


def _build_extra(code, market, price):
    now = datetime.now(TW)
    with ThreadPoolExecutor(max_workers=5) as ex:
        f_pe = ex.submit(_load_pe, market)
        f_rev = ex.submit(_load_revenue, market)
        f_inc = ex.submit(_load_income, market)
        f_ye = ex.submit(_load_year_end, market, now.year - 1)
        f_inst = ex.submit(_inst_history, market, code)
        pe_map, rev_map, inc_map, ye_map = f_pe.result(), f_rev.result(), f_inc.result(), f_ye.result()
        try:
            inst = f_inst.result()
        except Exception:
            inst = []

    lines = ['', '━━ 📌 補充資訊 ━━']

    # 今年漲幅
    base = ye_map.get(code)
    if base and price:
        lines.append(f"今年漲幅：*{(price / base - 1) * 100:+.0f}%*（去年底收盤 {base:g} → 現價 {price:g}）")

    # 估值
    pe = pb = dy = None
    if code in pe_map:
        pe_raw, pb_raw, dy_raw = pe_map[code]
        pe, pb, dy = _num(pe_raw), _num(pb_raw), _num(dy_raw)
        pe_txt = f"{pe:g}" if pe else '---（虧損或無資料）'
        pb_txt = f"{pb:g}" if pb else '---'
        dy_txt = f"{dy:g}%" if dy is not None else '---'
        lines += ['', '*估值*', f"本益比：{pe_txt}　　股價淨值比：{pb_txt}　　殖利率：{dy_txt}"]

    # 基本面
    inc = inc_map.get(code)
    rev = rev_map.get(code)
    eps = op_margin = rev_yoy = cum_yoy = None
    if inc or rev:
        lines += ['']
    if inc:
        year = inc.get('年度') or inc.get('Year')
        season = inc.get('季別') or inc.get('Season')
        revenue = _num(inc.get('營業收入'))
        gross = _num(inc.get('營業毛利（毛損）淨額'))
        op = _num(inc.get('營業利益（損失）'))
        eps = _num(inc.get('基本每股盈餘（元）'))
        gm = gross / revenue * 100 if revenue and gross is not None else None
        op_margin = op / revenue * 100 if revenue and op is not None else None
        title = f"*基本面*（{int(year) + 1911} {_season_label(season)}）"
        lines.append(title)
        lines.append(
            f"毛利率：{f'{gm:.1f}%' if gm is not None else '---'}　　"
            f"營益率：{f'{op_margin:.1f}%' if op_margin is not None else '---'}　　"
            f"EPS：{f'{eps:g} 元' if eps is not None else '---'}")
    elif rev:
        lines.append('*基本面*（此標的無一般財報資料，僅列營收）')
    if rev:
        rev_yoy = _num(rev.get('營業收入-去年同月增減(%)'))
        cum_yoy = _num(rev.get('累計營業收入-前期比較增減(%)'))
        ym = str(rev.get('資料年月', ''))
        month = int(ym[-2:]) if len(ym) >= 3 and ym[-2:].isdigit() else None
        lines.append(
            f"{f'{month} 月' if month else '當月'}營收年增："
            f"{f'{rev_yoy:+.1f}%' if rev_yoy is not None else '---'}　　"
            f"累計營收年增：{f'{cum_yoy:+.1f}%' if cum_yoy is not None else '---'}")

    # 三大法人
    if inst:
        def total(n):
            part = inst[:n]
            return tuple(sum(x[1][i] for x in part) for i in range(4))
        d0, v0 = inst[0]
        lines += ['', '*三大法人買賣超*（單位：張）',
                  f"{d0.month}/{d0.day}：外資 {_signed(v0[0])}　投信 {_signed(v0[1])}　"
                  f"自營商 {_signed(v0[2])}　合計 {_signed(v0[3])}"]
        for n in (SHORT_DAYS, LONG_DAYS):
            t = total(n)
            label = f"近 {n} 個交易日" if len(inst) >= n else f"近 {len(inst)} 個交易日"
            lines.append(f"{label}：外資 {_signed(t[0])}　投信 {_signed(t[1])}　"
                         f"自營商 {_signed(t[2])}　合計 {_signed(t[3])}")

    # 判讀
    verdict = _judge(eps, op_margin, rev_yoy, cum_yoy, pe)
    if verdict:
        label, why = verdict
        lines += ['', f"*基本面判讀*：{label}" + (f"（{why}）" if why else '')]

    if len(lines) <= 2:
        return ''
    lines.append('_（資料：證交所／櫃買中心公開資料，財報與營收為最新一期，僅供參考，非投資建議）_')
    return '\n' + '\n'.join(lines)


def warm_up():
    """啟動時在背景預載兩個市場的資料，避免第一次查詢要等很久。"""
    now = datetime.now(TW)
    for market in ('tse', 'otc'):
        try:
            _load_pe(market)
            _load_revenue(market)
            _load_income(market)
            _load_year_end(market, now.year - 1)
            _inst_history(market, '')
        except Exception:
            pass
