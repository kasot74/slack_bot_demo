import requests
import json
import re
import time
import random
from playwright.sync_api import sync_playwright

def read_url_content(url: str) -> str:
    """使用 Playwright 隱蔽模式讀取指定 URL 的內容，並進行清理與格式化。
    
    隱蔽模式特點：
    - 隱藏自動化標識，避免被反爬蟲檢測
    - 模擬真實用戶瀏覽行為（隨機延遲、滑鼠移動、滾動）
    - 偽造瀏覽器指紋（plugins、languages、deviceMemory 等）
    
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
            # 2. 啟動無頭瀏覽器 (Chrome) - 隱蔽模式
            browser = p.chromium.launch(
                headless=True,
                args=[
                    # 基礎參數
                    '--disable-gpu',
                    '--no-sandbox', 
                    '--disable-dev-shm-usage',
                    
                    # 隱蔽模式核心參數
                    '--disable-blink-features=AutomationControlled',  # 隱藏自動化標識
                    '--no-first-run',
                    '--disable-default-apps',
                    '--disable-extensions-file-access-check',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    
                    # 功能禁用
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-images',                # 不載入圖片
                    '--disable-background-networking',
                    '--disable-features=TranslateUI,BlinkGenPropertyTrees',
                    '--disable-logging',
                    '--disable-gpu-logging',
                    
                    # 快取限制
                    '--disk-cache-size=10485760',      # 10MB 磁碟快取
                    '--media-cache-size=5242880',      # 5MB 媒體快取
                ]
            )
            
            # 3. 建立新頁面並設定真實瀏覽器特徵
            page = browser.new_page(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                viewport={'width': 1366, 'height': 768},  # 常見解析度
                locale='zh-TW',
                timezone_id='Asia/Taipei'
            )
            
            # 4. 隱蔽模式 JavaScript 偽裝
            page.add_init_script("""
                // 隱藏 webdriver 屬性
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // 偽造 Chrome 對象
                window.chrome = {
                    runtime: {},
                    app: {
                        isInstalled: false,
                    }
                };
                
                // 偽造 plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                // 偽造 languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-TW', 'zh', 'en'],
                });
                
                // 偽造 deviceMemory 和 hardwareConcurrency
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8
                });
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 4
                });
            """)
            
            # 5. 設定頁面超時與攔截不必要的資源
            page.set_default_timeout(8000)  # 8 秒超時
            
            page.route("**/*.{png,jpg,gif,css,js,mp4,ads,analytics,woff,woff2,ttf}", lambda route: route.abort())
            
            # 6. 模擬真實用戶行為 - 隨機延遲
            time.sleep(random.uniform(0.5, 2.0))
            
            # 7. 導航至目標 URL 並等待頁面載入完成
            response = page.goto(url, wait_until='domcontentloaded', timeout=15000)


            # 8. 檢查回應狀態
            if response and response.status >= 400:
                browser.close()
                return f"錯誤：網頁回應錯誤 (HTTP {response.status})，無法獲取內容。"
            
            # 9. 模擬人類瀏覽行為
            # 隨機滑鼠移動
            page.mouse.move(
                random.randint(100, 600), 
                random.randint(100, 400)
            )
            
            # 隨機滾動頁面
            for _ in range(random.randint(1, 3)):
                scroll_amount = random.randint(100, 400)
                page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                time.sleep(random.uniform(0.3, 0.8))
            
            # 等待內容載入（模擬人類閱讀時間）
            page.wait_for_timeout(random.randint(1500, 3500))
            
            # 10. 獲取頁面標題
            title = page.title() or "無標題"
            
            # 11. 移除不需要的元素並獲取文字內容
            page.evaluate("""() => {
                const unwantedElements = document.querySelectorAll('script, style, header, footer, nav, .advertisement, .ads, .popup');
                unwantedElements.forEach(el => el.remove());
                
                const hiddenElements = document.querySelectorAll('[style*="display: none"], [style*="visibility: hidden"]');
                hiddenElements.forEach(el => el.remove());
            }""")
            
            # 12. 提取主要內容文字
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
            
            # 13. 清理文字內容
            if not main_content:
                return f"警告：無法從 {url} 獲取有效內容。"
                
            # 處理空白字元與換行
            clean_content = re.sub(r'\n\s*\n', '\n', main_content)
            clean_content = re.sub(r'[ \t]+', ' ', clean_content)  # 壓縮空白
            clean_content = clean_content.strip()
            
            # 14. 長度限制處理
            max_length = 1500
            if len(clean_content) > max_length:
                clean_content = clean_content[:max_length] + "\n... (內容過長已截斷)"
            
            return f"--- 網頁分析結果 (隱蔽模式) ---\n【標題】：{title}\n【來源】：{url}\n\n【主要內容】：\n{clean_content}"
            
    except Exception as e:
        error_message = str(e)
        return f"錯誤：無法讀取 {url} 的內容，原因: {error_message}"        

def search_threads(keyword: str, max_results: int = 10) -> str:
    """使用 Playwright 隱蔽模式搜索 Meta Threads 平台上的關鍵字內容。
    
    隱蔽模式特點：
    - 隱藏自動化標識，避免被反爬蟲檢測
    - 模擬真實用戶瀏覽行為（隨機延遲、滑鼠移動、滾動）
    - 偽造瀏覽器指紋（plugins、languages、deviceMemory 等）
    
    Args:
        keyword (str): 要搜索的關鍵字
        max_results (int): 最大返回結果數量，預設為 10
        
    Returns:
        str: 格式化的 Threads 搜索結果，包含貼文內容、作者、時間等資訊
    """
    try:
        # 1. 驗證關鍵字
        if not keyword or not keyword.strip():
            return "錯誤：搜索關鍵字不能為空。"
            
        keyword = keyword.strip()
        search_url = f"https://www.threads.net/search?q={requests.utils.quote(keyword)}"

        with sync_playwright() as p:
            # 2. 啟動無頭瀏覽器 (Chrome) - 隱蔽模式
            browser = p.chromium.launch(
                headless=True,
                args=[
                    # 基礎參數
                    '--disable-gpu',
                    '--no-sandbox', 
                    '--disable-dev-shm-usage',
                    
                    # 隱蔽模式核心參數
                    '--disable-blink-features=AutomationControlled',
                    '--no-first-run',
                    '--disable-default-apps',
                    '--disable-extensions-file-access-check',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    
                    # 功能禁用
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-background-networking',
                    '--disable-features=TranslateUI,BlinkGenPropertyTrees',
                    '--disable-logging',
                    '--disable-gpu-logging',
                    
                    # 快取限制
                    '--disk-cache-size=10485760',
                    '--media-cache-size=5242880',
                ]
            )
            
            # 3. 建立新頁面並設定真實瀏覽器特徵
            page = browser.new_page(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                viewport={'width': 1366, 'height': 768},
                locale='zh-TW',
                timezone_id='Asia/Taipei'
            )
            
            # 4. 隱蔽模式 JavaScript 偽裝
            page.add_init_script("""
                // 隱藏 webdriver 屬性
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // 偽造 Chrome 對象
                window.chrome = {
                    runtime: {},
                    app: {
                        isInstalled: false,
                    }
                };
                
                // 偽造 plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                // 偽造 languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-TW', 'zh', 'en'],
                });
                
                // 偽造 deviceMemory 和 hardwareConcurrency
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8
                });
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 4
                });
            """)
            
            # 5. 設定頁面超時與攔截不必要的資源
            page.set_default_timeout(10000)
            
            # 攔截不必要的資源以提高載入速度
            page.route("**/*.{png,jpg,gif,mp4,WebM,woff,woff2,ttf}", lambda route: route.abort())
            
            # 6. 模擬真實用戶行為 - 隨機延遲
            time.sleep(random.uniform(1.0, 2.5))
            
            # 7. 導航至 Threads 搜索頁面
            response = page.goto(search_url, wait_until='domcontentloaded', timeout=20000)
            
            # 8. 檢查回應狀態
            if response and response.status >= 400:
                browser.close()
                return f"錯誤：無法存取 Threads 搜索頁面 (HTTP {response.status})。"
            
            # 9. 等待內容載入並模擬人類瀏覽行為
            page.wait_for_timeout(random.randint(2000, 4000))
            
            # 隨機滑鼠移動
            page.mouse.move(
                random.randint(200, 800), 
                random.randint(200, 500)
            )
            
            # 模擬滾動載入更多內容
            for i in range(3):
                scroll_amount = random.randint(300, 600)
                page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                time.sleep(random.uniform(1.0, 2.0))
            
            # 10. 提取 Threads 貼文資料
            threads_data = page.evaluate(f"""() => {{
                const posts = [];
                const maxResults = {max_results};
                
                // Threads 貼文的常見選擇器模式
                const postSelectors = [
                    '[role="article"]',
                    '[data-testid="thread"]',
                    '.thread-post',
                    'article',
                    '[aria-label*="post"]'
                ];
                
                let foundPosts = [];
                
                // 嘗試不同的選擇器找到貼文
                for (const selector of postSelectors) {{
                    const elements = document.querySelectorAll(selector);
                    if (elements.length > 0) {{
                        foundPosts = Array.from(elements);
                        break;
                    }}
                }}
                
                // 如果沒找到特定選擇器，使用通用方法
                if (foundPosts.length === 0) {{
                    foundPosts = Array.from(document.querySelectorAll('div')).filter(div => {{
                        const text = div.textContent || '';
                        return text.length > 50 && text.length < 1000;
                    }});
                }}
                
                for (let i = 0; i < Math.min(foundPosts.length, maxResults); i++) {{
                    const post = foundPosts[i];
                    
                    try {{
                        // 提取貼文文字內容
                        let postText = post.textContent || post.innerText || '';
                        
                        // 清理文字
                        postText = postText.trim();
                        
                        // 過濾太短或太長的內容
                        if (postText.length < 20 || postText.length > 2000) {{
                            continue;
                        }}
                        
                        // 嘗試找到作者資訊
                        const authorElement = post.querySelector('a[href*="@"]') || 
                                            post.querySelector('[data-testid="username"]') ||
                                            post.querySelector('span:contains("@")');
                        
                        const author = authorElement ? 
                                     (authorElement.textContent || authorElement.title || '未知用戶') : 
                                     '未知用戶';
                        
                        // 嘗試找到時間資訊
                        const timeElement = post.querySelector('time') || 
                                          post.querySelector('[datetime]') ||
                                          post.querySelector('span:contains("分鐘")') ||
                                          post.querySelector('span:contains("小時")') ||
                                          post.querySelector('span:contains("天")');
                        
                        const postTime = timeElement ? 
                                       (timeElement.textContent || timeElement.getAttribute('datetime') || '未知時間') :
                                       '未知時間';
                        
                        posts.push({{
                            author: author,
                            content: postText,
                            time: postTime,
                            index: i + 1
                        }});
                        
                    }} catch (e) {{
                        console.log('Error processing post:', e);
                        continue;
                    }}
                }}
                
                return posts;
            }}""")
            
            browser.close()
            
            # 11. 格式化搜索結果
            if not threads_data or len(threads_data) == 0:
                return f"搜索關鍵字「{keyword}」在 Threads 上沒有找到相關結果。"
            
            # 建立結果字符串
            result_text = f"--- Threads 搜索結果 ---\n"
            result_text += f"【搜索關鍵字】：{keyword}\n"
            result_text += f"【找到結果】：{len(threads_data)} 筆\n"
            result_text += f"【搜索來源】：{search_url}\n\n"
            
            for post in threads_data:
                result_text += f"▶ 貼文 {post['index']}:\n"
                result_text += f"   作者：{post['author']}\n"
                result_text += f"   時間：{post['time']}\n"
                result_text += f"   內容：{post['content'][:300]}{'...' if len(post['content']) > 300 else ''}\n"
                result_text += f"   {'-' * 50}\n\n"
            
            return result_text
            
    except Exception as e:
        error_message = str(e)
        return f"錯誤：Threads 搜索失敗。關鍵字：{keyword}，錯誤原因：{error_message}"


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
