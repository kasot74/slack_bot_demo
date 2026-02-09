import requests
import json
import re
import time
import random
from playwright.sync_api import sync_playwright

def read_url_content(url: str) -> str:
    """使用 Playwright 讀取指定 URL 的內容，並進行清理與格式化。
    
    Args:
        url (str): 要讀取的網頁 URL
        
    Returns:
        str: 清理後的網頁內容文字，如果失敗則返回錯誤訊息
    """
    try:
        # 1. 驗證 URL 格式
        if not (url.startswith('http://') or url.startswith('https://')):
            return "錯誤：無效的 URL 格式，必須以 http:// 或 https:// 開頭。"

        with sync_playwright() as p:
            # 2. 啟動無頭瀏覽器 (Chrome)
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-gpu',
                    '--no-sandbox', 
                    '--disable-dev-shm-usage',                                        
                    
                    # 功能禁用
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-images',                # 不載入圖片
                    '--disable-background-networking',
                    
                    # 快取限制
                    '--disk-cache-size=10485760',      # 10MB 磁碟快取
                    '--media-cache-size=5242880',      # 5MB 媒體快取
                ]
            )
            
            # 3. 建立新頁面並設定視窗大小與User-Agent
            page = browser.new_page(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            
            # 4. 設定頁面超時與攔截不必要的資源（提高載入速度）
            page.set_default_timeout(8000)  # 8 秒超時
            
            page.route("**/*.{png,jpg,gif,css,js,mp4,ads,analytics}", lambda route: route.abort())
            # 5. 導航至目標 URL 並等待頁面載入完成
            response = page.goto(url, wait_until='domcontentloaded', timeout=15000)


            # 6. 檢查回應狀態
            if response and response.status >= 400:
                browser.close()
                return f"錯誤：網頁回應錯誤 (HTTP {response.status})，無法獲取內容。"
                                    
            page.wait_for_timeout(3000)  # 等待 3 秒讓 JavaScript 執行
            
            # 7. 獲取頁面標題
            title = page.title() or "無標題"
            
            # 8. 移除不需要的元素並獲取文字內容
            page.evaluate("""() => {
                const unwantedElements = document.querySelectorAll('script, style, header, footer, nav, .advertisement, .ads, .popup');
                unwantedElements.forEach(el => el.remove());
                
                const hiddenElements = document.querySelectorAll('[style*="display: none"], [style*="visibility: hidden"]');
                hiddenElements.forEach(el => el.remove());
            }""")
            
            # 9. 提取主要內容文字
            main_content = page.evaluate("""() => {
                const mainSelectors = ['main', 'article', '.content', '#content', '.post', '.entry', 'body'];
                let content = '';
                
                for (const selector of mainSelectors) {
                    const element = document.querySelector(selector);
                    if (element) {
                        content = element.innerText;
                        break;
                    }
                }
                
                if (!content) {
                    content = document.body.innerText || document.body.textContent || '';
                }
                
                return content;
            }""")
            
            browser.close()
            
            # 11. 清理文字內容
            if not main_content:
                return f"警告：無法從 {url} 獲取有效內容。"
                
            # 處理空白字元與換行
            clean_content = re.sub(r'\n\s*\n', '\n', main_content)
            clean_content = re.sub(r'[ \t]+', ' ', clean_content)  # 壓縮空白
            clean_content = clean_content.strip()
            
            # 12. 長度限制處理
            max_length = 1500
            if len(clean_content) > max_length:
                clean_content = clean_content[:max_length] + "\n... (內容過長已截斷)"
            
            return f"--- 網頁分析結果 ---\n【標題】：{title}\n【來源】：{url}\n\n【主要內容】：\n{clean_content}"
            
    except Exception as e:
        error_message = str(e)
        return f"錯誤：無法讀取 {url} 的內容，原因: {error_message}"        

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
