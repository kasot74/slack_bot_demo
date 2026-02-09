import requests
import json
import re
import time
import random
from bs4 import BeautifulSoup

def read_url_content(url: str) -> str:
    """讀取指定 URL 的內容，並進行初步的 HTML 清理與格式化。
    
    Args:
        url (str): 要讀取的網頁 URL
        
    Returns:
        str: 清理後的網頁內容文字，如果失敗則返回錯誤訊息
    """
    try:
        # 1. 驗證 URL 格式
        if not (url.startswith('http://') or url.startswith('https://')):
            return "錯誤：無效的 URL 格式，必須以 http:// 或 https:// 開頭。"

        # 設定請求標頭        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        
        # 2. 發送請求並設定超時
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # 3. 檢查內容類型，僅處理 HTML 或純文字
        content_type = response.headers.get('Content-Type', '').lower()
        if 'text/html' not in content_type and 'text/plain' not in content_type:
            return f"注意：該 URL 的內容類型為 {content_type}，AI 目前僅支援閱讀網頁或文字。"

        if response.encoding:
            response.encoding = response.apparent_encoding
        
        html_content = response.text
        
        # 4. 使用 BeautifulSoup 提取標題與內容
        soup = BeautifulSoup(html_content, 'html.parser')
        title = soup.title.string.strip() if soup.title else "無標題"
        
        # 5. 精細清理內容
        # 移除不可見的腳本與樣式
        for script_or_style in soup(["script", "style", "header", "footer", "nav"]):
            script_or_style.decompose()
            
        # 取得純文字
        clean_content = soup.get_text(separator='\n')
        
        # 處理 HTML 轉義字元與空白
        clean_content = re.sub(r'\n\s*\n', '\n', clean_content)
        clean_content = clean_content.strip()
        
        # 6. 截錄長度限制，避免超出分析範圍
        max_length = 3500 
        if len(clean_content) > max_length:
            clean_content = clean_content[:max_length] + "\n... (內容過長已截斷)"
        
        return f"--- 網頁分析結果 ---\n【標題】：{title}\n【來源】：{url}\n\n【主要內容】：\n{clean_content}"
        
    except requests.exceptions.Timeout:
        return f"錯誤：連線至 {url} 逾時，請稍後再試。"
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if hasattr(e, 'response') else 'Unknown'
        return f"錯誤：網頁回應錯誤 (HTTP {status_code})，無法獲取內容。"
    except Exception as e:
        return f"錯誤：處理網頁時發生問題: {str(e)}"

def get_technical_indicators(market: str, period: int = 15, limit: int = 500) -> str:
    """
    獲取加密貨幣的技術指標數據 
    
    回傳的 JSON 結構包含：
    1. current_indicators: 最新一筆的技術指標摘要
       - price: current, open, high, low, volume
       - moving_averages: MA_5, MA_10, MA_20, MA_50, EMA_12, EMA_26
       - oscillators: RSI, Stoch_K, Stoch_D, Williams_R
       - macd: MACD, MACD_Signal, MACD_Histogram
       - bollinger_bands: BB_Upper, BB_Middle, BB_Lower
       - volatility: ATR
    2. indicators: 歷史技術指標列表 (包含時間戳與詳細數值)
    
    Args:
        market: 交易對符號 (例如: 'btctwd', 'ethusdt')
        period: 時間週期 (分鐘)，預設為 15
        limit: 返回的歷史數據量，範圍 20-500，預設為 500
    """
    url = "https://herry537.sytes.net/max_api/analysis/indicators"
    params = {
        "market": market,
        "period": period,
        "limit": limit
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # 這裡根據 API 回傳格式進行簡單格式化，或者直接回傳 JSON 字串讓 AI 讀取
        return json.dumps(data, indent=2, ensure_ascii=False)
        
    except Exception as e:
        return f"技術指標獲取失敗: {str(e)}"
