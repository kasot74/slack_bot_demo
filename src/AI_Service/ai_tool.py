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
    """使用 Playwright 增強隱蔽模式搜索 Meta Threads 平台上的關鍵字內容。
    
    專為動態內容設計的增強隱蔽模式特點：
    - 深度隱藏自動化標識，完全模擬真實瀏覽器
    - 智能等待動態內容載入完成
    - 多階段反檢測與行為模擬
    - 增強的瀏覽器指紋偽裝
    
    Args:
        keyword (str): 要搜索的關鍵字
        max_results (int): 最大返回結果數量，預設為 10
        
    Returns:
        str: 格式化的 Threads 搜索結果，包含貼文內容、作者、時間等資訊
    """
    
    # 重試機制
    max_retries = 2
    for attempt in range(max_retries):
        try:
            # 1. 驗證關鍵字
            if not keyword or not keyword.strip():
                return "錯誤：搜索關鍵字不能為空。"
                
            keyword = keyword.strip()
            search_url = f"https://www.threads.net/search?q={requests.utils.quote(keyword)}"

            with sync_playwright() as p:
                # 2. 啟動無頭瀏覽器 - 增強隱蔽模式
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        # 基礎參數
                        '--disable-gpu',
                        '--no-sandbox', 
                        '--disable-dev-shm-usage',
                        '--disable-setuid-sandbox',
                        
                        # 核心反檢測參數
                        '--disable-blink-features=AutomationControlled',
                        '--no-first-run',
                        '--disable-default-apps',
                        '--disable-extensions-file-access-check',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding',
                        '--disable-component-extensions-with-background-pages',
                        
                        # 增強反檢測
                        '--disable-ipc-flooding-protection',
                        '--disable-hang-monitor',
                        '--disable-prompt-on-repost',
                        '--disable-background-networking',
                        '--disable-sync',
                        '--disable-translate',
                        '--hide-scrollbars',
                        '--mute-audio',
                        
                        # 功能細化控制
                        '--disable-extensions',
                        '--disable-plugins',
                        '--disable-features=TranslateUI,BlinkGenPropertyTrees,VizDisplayCompositor',
                        '--disable-logging',
                        '--disable-gpu-logging',
                        '--silent',
                        
                        # 記憶體與快取優化
                        '--memory-pressure-off',
                        '--max_old_space_size=4096',
                        '--disk-cache-size=16777216',  # 16MB
                        '--media-cache-size=8388608',  # 8MB
                    ]
                )
                
                # 3. 建立新頁面 - 超真實瀏覽器模擬
                page = browser.new_page(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    viewport={'width': random.randint(1200, 1440), 'height': random.randint(720, 900)},
                    locale='zh-TW',
                    timezone_id='Asia/Taipei',
                    has_touch=False,
                    is_mobile=False,
                    device_scale_factor=1
                )
                
                # 4. 深度隱蔽模式 JavaScript 偽裝
                page.add_init_script("""
                    // 完全隱藏 webdriver 痕跡
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                        configurable: true
                    });
                    
                    // 移除 automation 相關屬性
                    delete window.navigator.__proto__.webdriver;
                    
                    // 偽造完整的 Chrome 對象
                    window.chrome = {
                        runtime: {
                            onConnect: null,
                            onMessage: null
                        },
                        app: {
                            isInstalled: false,
                            InstallState: {
                                DISABLED: 'disabled',
                                INSTALLED: 'installed',
                                NOT_INSTALLED: 'not_installed'
                            }
                        }
                    };
                    
                    // 偽造真實的 plugins 陣列
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => {
                            return Array.from(Array(5), (_, i) => ({
                                name: `Plugin ${i}`,
                                filename: `plugin${i}.dll`,
                                description: `Description ${i}`
                            }));
                        },
                        configurable: true
                    });
                    
                    // 偽造語言設定
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['zh-TW', 'zh-CN', 'zh', 'en-US', 'en'],
                        configurable: true
                    });
                    
                    // 偽造設備資訊
                    Object.defineProperty(navigator, 'deviceMemory', {
                        get: () => 8,
                        configurable: true
                    });
                    
                    Object.defineProperty(navigator, 'hardwareConcurrency', {
                        get: () => 8,
                        configurable: true
                    });
                    
                    // 偽造螢幕資訊
                    Object.defineProperty(screen, 'width', {
                        get: () => 1920,
                        configurable: true
                    });
                    
                    Object.defineProperty(screen, 'height', {
                        get: () => 1080,
                        configurable: true
                    });
                    
                    // 偽造時區
                    Date.prototype.getTimezoneOffset = function() {
                        return -480; // GMT+8
                    };
                    
                    // 偽造 permissions API
                    navigator.permissions.query = navigator.permissions.query || function() {
                        return Promise.resolve({ state: 'granted' });
                    };
                """)
                
                # 5. 設定超時與資源攔截
                page.set_default_timeout(15000)
                
                # 只攔截大型媒體檔案，保留 CSS/JS 以確保動態內容載入
                page.route("**/*.{jpg,jpeg,png,gif,webp,mp4,avi,mov,wmv,flv,woff,woff2,ttf,otf}", 
                          lambda route: route.abort())
                
                # 6. 預載入等待 - 模擬真實用戶行為
                time.sleep(random.uniform(2.0, 4.0))
                
                # 7. 導航至 Threads 主頁（模擬真實用戶路徑）
                try:
                    page.goto("https://www.threads.net", wait_until='domcontentloaded', timeout=25000)
                    page.wait_for_timeout(random.randint(2000, 4000))
                    
                    # 模擬點擊搜索或直接導航
                    time.sleep(random.uniform(1.0, 2.0))
                except:
                    pass  # 如果主頁失敗，直接進行搜索
                
                # 8. 導航至搜索頁面
                response = page.goto(search_url, wait_until='networkidle', timeout=30000)
                
                # 9. 檢查回應狀態
                if response and response.status >= 400:
                    browser.close()
                    if attempt < max_retries - 1:
                        continue
                    return f"錯誤：Threads 回應錯誤 (HTTP {response.status})，可能被限制存取。"
                
                # 10. 深度等待與互動模擬
                # 第一階段：等待基本頁面結構
                page.wait_for_timeout(random.randint(3000, 6000))
                
                # 模擬真實用戶互動
                # 隨機滑鼠移動到不同位置
                for _ in range(random.randint(2, 4)):
                    x = random.randint(100, 1000)
                    y = random.randint(100, 600)
                    page.mouse.move(x, y, steps=random.randint(5, 15))
                    time.sleep(random.uniform(0.5, 1.5))
                
                # 第二階段：模擬滾動以觸發內容載入
                scroll_attempts = 0
                max_scroll_attempts = 8
                
                while scroll_attempts < max_scroll_attempts:
                    # 向下滾動
                    scroll_amount = random.randint(200, 500)
                    page.evaluate(f"""
                        window.scrollTo({{
                            top: window.scrollY + {scroll_amount},
                            behavior: 'smooth'
                        }});
                    """)
                    
                    # 等待內容載入
                    time.sleep(random.uniform(1.5, 3.0))
                    
                    # 檢查是否有新內容出現
                    content_check = page.evaluate("""
                        () => {
                            const posts = document.querySelectorAll('[role="article"], article, div[data-testid*="thread"], div[style*="cursor"]');
                            return posts.length;
                        }
                    """)
                    
                    if content_check > 0:
                        break
                        
                    scroll_attempts += 1
                
                # 第三階段：最終等待確保所有動態內容載入
                page.wait_for_timeout(random.randint(3000, 5000))
                
                # 11. 智能內容提取
                threads_data = page.evaluate(f"""() => {{
                    console.log('開始提取 Threads 內容...');
                    const posts = [];
                    const maxResults = {max_results};
                    
                    // 更全面的內容選擇器
                    const contentSelectors = [
                        '[role="article"]',
                        'article',
                        'div[data-testid*="thread"]', 
                        'div[data-testid*="post"]',
                        'div[aria-label*="post"]',
                        'div[style*="cursor: pointer"]',
                        'div[tabindex="0"]'
                    ];
                    
                    let foundElements = [];
                    
                    // 嘗試各種選擇器
                    for (const selector of contentSelectors) {{
                        console.log('嘗試選擇器:', selector);
                        const elements = document.querySelectorAll(selector);
                        console.log('找到元素數量:', elements.length);
                        
                        if (elements.length > 0) {{
                            foundElements = Array.from(elements);
                            break;
                        }}
                    }}
                    
                    // 備用方法：尋找包含文字的 div
                    if (foundElements.length === 0) {{
                        console.log('使用備用方法搜尋內容...');
                        const allDivs = document.querySelectorAll('div');
                        foundElements = Array.from(allDivs).filter(div => {{
                            const text = (div.textContent || div.innerText || '').trim();
                            const hasReasonableLength = text.length > 30 && text.length < 2000;
                            const hasPostLikeContent = /[\u4e00-\u9fff]|[a-zA-Z]/.test(text);
                            const notNavigationElement = !div.querySelector('nav') && !div.closest('nav');
                            
                            return hasReasonableLength && hasPostLikeContent && notNavigationElement;
                        }});
                    }}
                    
                    console.log('總共找到可能的內容元素:', foundElements.length);
                    
                    // 提取內容
                    const processedTexts = new Set(); // 避免重複
                    
                    for (let i = 0; i < foundElements.length && posts.length < maxResults; i++) {{
                        const element = foundElements[i];
                        
                        try {{
                            let postText = (element.textContent || element.innerText || '').trim();
                            
                            // 基本過濾
                            if (postText.length < 20 || postText.length > 2000) {{
                                continue;
                            }}
                            
                            // 避免重複內容
                            if (processedTexts.has(postText)) {{
                                continue;
                            }}
                            
                            // 過濾明顯的導航或系統文字
                            const systemWords = ['登入', '註冊', '隱私', '條款', '設定', '搜尋', '首頁', 'Home', 'Search', 'Settings'];
                            const isSystemText = systemWords.some(word => postText.includes(word) && postText.length < 100);
                            
                            if (isSystemText) {{
                                continue;
                            }}
                            
                            processedTexts.add(postText);
                            
                            // 嘗試提取作者資訊
                            let author = '未知用戶';
                            const authorSelectors = [
                                'a[href*="@"]',
                                '[data-testid*="user"]',
                                '[data-testid*="username"]',
                                'span[dir="ltr"]',
                                'strong'
                            ];
                            
                            for (const selector of authorSelectors) {{
                                const authorElement = element.querySelector(selector);
                                if (authorElement && authorElement.textContent) {{
                                    const authorText = authorElement.textContent.trim();
                                    if (authorText.length < 50 && !authorText.includes('\\n')) {{
                                        author = authorText;
                                        break;
                                    }}
                                }}
                            }}
                            
                            // 嘗試提取時間
                            let postTime = '最近';
                            const timeSelectors = ['time', '[datetime]', 'span'];
                            
                            for (const selector of timeSelectors) {{
                                const timeElement = element.querySelector(selector);
                                if (timeElement) {{
                                    const timeText = timeElement.textContent || timeElement.getAttribute('datetime') || '';
                                    if (timeText && (timeText.includes('分') || timeText.includes('時') || timeText.includes('天') || timeText.match(/\\d/))) {{
                                        postTime = timeText.trim();
                                        break;
                                    }}
                                }}
                            }}
                            
                            posts.push({{
                                author: author,
                                content: postText,
                                time: postTime,
                                index: posts.length + 1
                            }});
                            
                            console.log(`成功提取貼文 ${{posts.length}}: ${{postText.substring(0, 50)}}...`);
                            
                        }} catch (e) {{
                            console.log('處理元素時發生錯誤:', e);
                            continue;
                        }}
                    }}
                    
                    console.log('最終提取到的貼文數量:', posts.length);
                    return posts;
                }}""")
                
                browser.close()
                
                # 12. 格式化搜索結果
                if not threads_data or len(threads_data) == 0:
                    if attempt < max_retries - 1:
                        time.sleep(random.uniform(2.0, 5.0))  # 重試前等待
                        continue
                    return f"搜索關鍵字「{keyword}」在 Threads 上沒有找到相關結果。這可能是由於內容動態載入或訪問限制。"
                
                # 成功獲取結果，格式化輸出
                result_text = f"🧵 **Threads 搜索結果** (隱蔽模式)\n"
                result_text += f"【關鍵字】：{keyword}\n"
                result_text += f"【找到】：{len(threads_data)} 筆結果\n"
                result_text += f"【來源】：{search_url}\n"
                result_text += f"{'=' * 50}\n\n"
                
                for post in threads_data:
                    result_text += f"▶ **貼文 {post['index']}**\n"
                    result_text += f"👤 **作者**：{post['author']}\n"
                    result_text += f"⏰ **時間**：{post['time']}\n"
                    result_text += f"💬 **內容**：{post['content'][:250]}{'...' if len(post['content']) > 250 else ''}\n"
                    result_text += f"{'-' * 40}\n\n"
                
                return result_text
                
        except Exception as e:
            error_message = str(e)
            if attempt < max_retries - 1:
                time.sleep(random.uniform(3.0, 6.0))  # 重試前等待
                continue
            return f"錯誤：Threads 搜索失敗。關鍵字：{keyword}，錯誤：{error_message}"
    
    return f"錯誤：經過 {max_retries} 次嘗試後仍無法完成 Threads 搜索。"


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
