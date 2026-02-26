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
    """使用 Scrapfly 方法搜索 Meta Threads 平台上的關鍵字內容。
    
    基於 Scrapfly 建議的方法：
    - 提取隱藏的 JSON 數據而非 DOM 元素
    - 尋找 script[type="application/json"][data-sjs] 標籤
    - 解析 thread_items 結構獲取貼文數據
    - 使用簡化的瀏覽器設定減少檢測風險
    
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
        search_url = f"https://www.threads.net/search?q={requests.utils.quote(keyword)}&serp_type=tags"
        search_type = f"搜索關鍵字: {keyword}"

        with sync_playwright() as p:
            # 2. 簡化的瀏覽器設定 (基於 Scrapfly 建議)
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-gpu',
                    '--no-sandbox', 
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-extensions',
                    '--disable-plugins'
                ]
            )
            
            # 3. 建立新頁面
            page = browser.new_page(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            
            # 4. 隱藏 webdriver 標識
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                window.chrome = {
                    runtime: {},
                    app: { isInstalled: false }
                };
            """)
            
            # 5. 攔截不需要的資源
            page.route("**/*.{png,jpg,gif,css,woff,woff2,ttf}", lambda route: route.abort())
            
            # 6. 導航至搜索頁面
            page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            
            # 7. 等待頁面載入完成
            try:
                page.wait_for_selector("[data-pressable-container=true]", timeout=15000)
            except:
                pass  # 如果特定元素不存在，繼續嘗試
                
            # 8. 模擬滾動載入更多內容
            for _ in range(3):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(random.uniform(1.0, 2.0))
            
            # 9. 檢查頁面載入狀況
            debug_info = []
            page_title = page.title() or "無標題"
            page_url = page.url
            debug_info.append(f"✓ 頁面載入成功：{page_title}")
            debug_info.append(f"✓ 當前URL：{page_url}")
            
            # 檢查頁面是否包含 Threads 相關內容
            page_content_check = page.evaluate("""() => {
                const bodyText = document.body.innerText || document.body.textContent || '';
                const hasThreadsContent = bodyText.toLowerCase().includes('threads') || 
                                        bodyText.includes('搜尋') || 
                                        bodyText.includes('search');
                const scriptCount = document.querySelectorAll('script').length;
                const jsonScriptCount = document.querySelectorAll('script[type="application/json"]').length;
                
                return {
                    hasThreadsContent,
                    totalScripts: scriptCount,
                    jsonScripts: jsonScriptCount,
                    bodyLength: bodyText.length
                };
            }""")
            
            debug_info.append(f"✓ 頁面包含Threads內容：{page_content_check['hasThreadsContent']}")
            debug_info.append(f"✓ Script標籤總數：{page_content_check['totalScripts']}")
            debug_info.append(f"✓ JSON Script標籤數：{page_content_check['jsonScripts']}")
            debug_info.append(f"✓ 頁面內容長度：{page_content_check['bodyLength']} 字元")
            
            # 9. 提取隱藏的 JSON 數據 (Scrapfly 方法)
            hidden_datasets_info = page.evaluate("""() => {
                const scripts = document.querySelectorAll('script[type="application/json"][data-sjs]');
                const datasets = [];
                const allJsonScripts = document.querySelectorAll('script[type="application/json"]');
                
                let scheduledServerJSCount = 0;
                let threadItemsCount = 0;
                
                scripts.forEach(script => {
                    try {
                        const text = script.textContent || script.innerText;
                        if (text) {
                            if (text.includes('ScheduledServerJS')) scheduledServerJSCount++;
                            if (text.includes('thread_items')) threadItemsCount++;
                            
                            if (text.includes('ScheduledServerJS') && text.includes('thread_items')) {
                                datasets.push(text);
                            }
                        }
                    } catch (e) {
                        console.log('解析 script 標籤時出錯:', e);
                    }
                });
                
                return {
                    datasets,
                    totalJsonScripts: allJsonScripts.length,
                    dataSjsScripts: scripts.length,
                    scheduledServerJSCount,
                    threadItemsCount,
                    foundValidDatasets: datasets.length
                };
            }""")
            
            hidden_datasets = hidden_datasets_info['datasets']
            
            debug_info.append(f"✓ 所有JSON Script標籤：{hidden_datasets_info['totalJsonScripts']} 個")
            debug_info.append(f"✓ data-sjs標籤：{hidden_datasets_info['dataSjsScripts']} 個") 
            debug_info.append(f"✓ 包含ScheduledServerJS：{hidden_datasets_info['scheduledServerJSCount']} 個")
            debug_info.append(f"✓ 包含thread_items：{hidden_datasets_info['threadItemsCount']} 個")
            debug_info.append(f"✓ 符合條件的數據集：{hidden_datasets_info['foundValidDatasets']} 個")
            
            browser.close()
            
            # 10. 解析 JSON 數據尋找貼文內容
            threads_data = []
            json_parse_errors = []
            thread_items_found = []
            
            for i, dataset_str in enumerate(hidden_datasets):
                try:
                    debug_info.append(f"✓ 正在解析第 {i+1} 個數據集，長度：{len(dataset_str)} 字元")
                    dataset = json.loads(dataset_str)
                    
                    # 遞迴搜尋 thread_items
                    def find_thread_items(obj, path=""):
                        if isinstance(obj, dict):
                            if 'thread_items' in obj:
                                return obj['thread_items']
                            for key, value in obj.items():
                                result = find_thread_items(value, f"{path}.{key}")
                                if result:
                                    return result
                        elif isinstance(obj, list):
                            for i, item in enumerate(obj):
                                result = find_thread_items(item, f"{path}[{i}]")
                                if result:
                                    return result
                        return None
                    
                    thread_items = find_thread_items(dataset)
                    
                    if thread_items:
                        thread_items_found.append(f"數據集{i+1}：找到thread_items，類型：{type(thread_items)}")
                        debug_info.append(f"✓ 數據集 {i+1} 找到 thread_items：{len(thread_items) if isinstance(thread_items, list) else '非列表類型'}")
                        
                        # 詳細分析 thread_items 結構
                        debug_info.append(f"🔍 深度分析 thread_items 結構：{type(thread_items)}")
                        if isinstance(thread_items, dict):
                            debug_info.append(f"🔍 字典鍵數量：{len(thread_items.keys())}")
                            debug_info.append(f"🔍 字典鍵列表：{list(thread_items.keys())[:10]}")  # 只顯示前10個鍵
                            
                            # 分析每個鍵的值類型和長度
                            for key, value in list(thread_items.items())[:5]:  # 只分析前5個鍵
                                debug_info.append(f"🔍 鍵 '{key}': 類型={type(value)}, 長度={len(value) if hasattr(value, '__len__') else 'N/A'}")
                        elif isinstance(thread_items, list):
                            debug_info.append(f"🔍 列表長度：{len(thread_items)}")
                            if len(thread_items) > 0:
                                debug_info.append(f"🔍 第一個元素類型：{type(thread_items[0])}")
                        
                        # 處理不同的 thread_items 結構
                        if isinstance(thread_items, list):
                            # thread_items 是列表，直接處理每個元素
                            threads_to_process = thread_items
                            debug_info.append(f"📋 使用列表模式，包含 {len(threads_to_process)} 個項目")
                        elif isinstance(thread_items, dict):
                            # thread_items 是字典，需要找到包含貼文的鍵
                            threads_to_process = []
                            for key, value in thread_items.items():
                                if isinstance(value, list) and len(value) > 0:
                                    debug_info.append(f"✓ 在字典鍵 '{key}' 中找到列表，包含 {len(value)} 個項目")
                                    # 檢查列表中的元素類型
                                    if len(value) > 0:
                                        debug_info.append(f"📝 鍵 '{key}' 列表第一個元素類型：{type(value[0])}")
                                        if isinstance(value[0], dict) and any(k in value[0] for k in ['post', 'thread', 'content', 'text']):
                                            debug_info.append(f"✅ 鍵 '{key}' 包含貼文相關數據，添加到處理隊列")
                                            threads_to_process.extend(value)
                                        else:
                                            debug_info.append(f"❌ 鍵 '{key}' 不包含貼文數據，跳過")
                                elif isinstance(value, dict):
                                    debug_info.append(f"✓ 在字典鍵 '{key}' 中找到字典數據")
                                    if any(k in value for k in ['post', 'thread', 'content', 'text', 'caption']):
                                        debug_info.append(f"✅ 鍵 '{key}' 包含貼文相關字段，添加到處理隊列")
                                        threads_to_process.append(value)
                                    else:
                                        debug_info.append(f"❌ 鍵 '{key}' 不包含貼文字段，跳過")
                                else:
                                    debug_info.append(f"➖ 鍵 '{key}': 類型 {type(value)}，不是列表或字典")
                            
                            debug_info.append(f"📋 字典模式處理完成，總共找到 {len(threads_to_process)} 個項目待處理")
                        else:
                            debug_info.append(f"✗ thread_items 類型不支持：{type(thread_items)}")
                            continue
                        
                        for thread_item in threads_to_process:
                            # 處理列表中的每個項目
                            if isinstance(thread_item, list):
                                # 如果是列表，處理列表中的每個貼文
                                debug_info.append(f"✓ 處理貼文列表，包含 {len(thread_item)} 個項目")
                                for thread in thread_item:
                                    try:
                                        # 提取貼文基本資訊
                                        if isinstance(thread, dict) and 'post' in thread:
                                            post = thread['post']
                                            
                                            # 提取內容文字
                                            content = ""
                                            if 'caption' in post and post['caption'] and 'text' in post['caption']:
                                                content = post['caption']['text']
                                            
                                            # 提取作者資訊
                                            author = "未知用戶"
                                            if 'user' in post and post['user'] and 'username' in post['user']:
                                                author = post['user']['username']
                                            
                                            # 提取時間 (Unix 時間戳)
                                            post_time = "最近"
                                            if 'taken_at' in post and post['taken_at']:
                                                try:
                                                    timestamp = int(post['taken_at'])
                                                    from datetime import datetime
                                                    dt = datetime.fromtimestamp(timestamp)
                                                    post_time = dt.strftime("%Y-%m-%d %H:%M")
                                                except:
                                                    pass
                                            
                                            # 提取互動數據
                                            like_count = post.get('like_count', 0)
                                            
                                            # 降低內容長度限制，並加入調試信息
                                            debug_info.append(f"📝 檢查貼文內容：長度={len(content.strip()) if content else 0}，作者=@{author}")
                                            
                                            if content and len(content.strip()) > 5:  # 降低從10到5
                                                threads_data.append({
                                                    'author': f"@{author}",
                                                    'content': content.strip(),
                                                    'time': post_time,
                                                    'likes': like_count,
                                                    'index': len(threads_data) + 1
                                                })
                                                debug_info.append(f"✅ 成功提取貼文 {len(threads_data)}：@{author}")
                                            else:
                                                debug_info.append(f"❌ 跳過貼文：內容太短或為空")
                                    except Exception as e:
                                        debug_info.append(f"✗ 解析個別貼文失敗：{str(e)}")
                                        continue
                                        
                                debug_info.append(f"📊 此列表處理完成，已提取 {len(threads_data)} 筆貼文")
                                
                            elif isinstance(thread_item, dict):
                                # 如果是字典，直接處理這個貼文
                                debug_info.append(f"✓ 處理單個貼文字典")
                                try:
                                    # 檢查是否直接包含 post 數據
                                    if 'post' in thread_item:
                                        post = thread_item['post']
                                        debug_info.append(f"📝 字典包含post結構")
                                    elif 'caption' in thread_item and 'user' in thread_item:
                                        # 可能這個字典本身就是 post 數據
                                        post = thread_item
                                        debug_info.append(f"📝 字典本身為post數據")
                                    else:
                                        debug_info.append(f"✗ 字典結構不符合預期，鍵有：{list(thread_item.keys())[:5]}")
                                        continue
                                    
                                    # 提取內容文字
                                    content = ""
                                    if 'caption' in post and post['caption'] and 'text' in post['caption']:
                                        content = post['caption']['text']
                                    
                                    # 提取作者資訊
                                    author = "未知用戶"
                                    if 'user' in post and post['user'] and 'username' in post['user']:
                                        author = post['user']['username']
                                    
                                    # 提取時間 (Unix 時間戳)
                                    post_time = "最近"
                                    if 'taken_at' in post and post['taken_at']:
                                        try:
                                            timestamp = int(post['taken_at'])
                                            from datetime import datetime
                                            dt = datetime.fromtimestamp(timestamp)
                                            post_time = dt.strftime("%Y-%m-%d %H:%M")
                                        except:
                                            pass
                                    
                                    # 提取互動數據
                                    like_count = post.get('like_count', 0)
                                    
                                    # 降低內容長度限制，並加入調試信息
                                    debug_info.append(f"📝 檢查字典貼文內容：長度={len(content.strip()) if content else 0}，作者=@{author}")
                                    
                                    if content and len(content.strip()) > 5:  # 降低從10到5
                                        threads_data.append({
                                            'author': f"@{author}",
                                            'content': content.strip(),
                                            'time': post_time,
                                            'likes': like_count,
                                            'index': len(threads_data) + 1
                                        })
                                        debug_info.append(f"✅ 成功提取字典貼文 {len(threads_data)}：@{author}")
                                    else:
                                        debug_info.append(f"❌ 跳過字典貼文：內容太短或為空")
                                        
                                except Exception as e:
                                    debug_info.append(f"✗ 解析字典貼文失敗：{str(e)}")
                                    continue
                            else:
                                debug_info.append(f"✗ 未知的貼文項目類型：{type(thread_item)}")
                        
                        debug_info.append(f"📊 數據集 {i+1} 處理完成，目前總計 {len(threads_data)} 筆貼文")
                        
                        # 只有在達到最大結果數時才跳出，讓它處理完所有數據
                        if len(threads_data) >= max_results:
                            debug_info.append(f"🔄 已達到最大結果數 {max_results}，停止處理")
                            break
                    else:
                        debug_info.append(f"✗ 數據集 {i+1} 沒有找到 thread_items")
                    
                    if len(threads_data) >= max_results:
                        break
                        
                except Exception as e:
                    json_parse_errors.append(f"數據集{i+1}解析失敗：{str(e)}")
                    debug_info.append(f"✗ JSON 解析失敗：{str(e)}")
                    continue
            
            # 11. 格式化搜索結果
            debug_summary = "\n".join(debug_info)
            
            if not threads_data:
                error_detail = f"""
                🔍 **Threads 搜索調試報告**
                【搜索類型】：{search_type}
                【搜索URL】：{search_url}

                📋 **執行步驟詳情：**
                {debug_summary}

                ❌ **最終結果：** 未找到有效貼文數據

                💡 **可能原因分析：**
                1. 如果 JSON Script 標籤數量為 0：頁面結構可能已改變
                2. 如果找不到 ScheduledServerJS：Threads 可能更新了數據載入方式  
                3. 如果找不到 thread_items：搜索結果可能為空或需要登入
                4. 如果有 JSON 解析錯誤：數據格式可能已變更

                🔧 **建議解決方案：**
                - 檢查是否需要登入 Threads 帳號
                - 嘗試其他關鍵字進行搜索
                - 確認搜索URL是否正確載入
                """
                return error_detail
            
            result_text = f"🧵 **Threads 搜索結果** (Scrapfly 方法)\n"
            result_text += f"【搜索類型】：{search_type}\n"
            result_text += f"【找到】：{len(threads_data)} 筆結果\n"
            result_text += f"【來源】：{search_url}\n"
            result_text += f"\n📋 **執行摘要：**\n"
            result_text += f"- 頁面載入：✓ {page_title}\n" 
            result_text += f"- JSON數據集：{hidden_datasets_info['foundValidDatasets']} 個\n"
            result_text += f"- 提取貼文：{len(threads_data)} 筆\n"
            result_text += f"\n🔍 **詳細調試信息：**\n"
            result_text += f"{debug_summary}\n"
            result_text += f"{'=' * 50}\n\n"
            
            for post in threads_data:
                result_text += f"▶ **貼文 {post['index']}**\n"
                result_text += f"👤 **作者**：{post['author']}\n"
                result_text += f"⏰ **時間**：{post['time']}\n"
                result_text += f"❤️ **讚數**：{post['likes']}\n"
                result_text += f"💬 **內容**：{post['content'][:300]}{'...' if len(post['content']) > 300 else ''}\n"
                result_text += f"{'-' * 40}\n\n"
            
            return result_text
                
    except Exception as e:
        error_message = str(e)
        return f"錯誤：Threads 搜索失敗。關鍵字：{keyword}，錯誤：{error_message}\n\n注意：Threads 的搜索功能主要在行動應用程式中提供，網頁版的搜索結果可能有限。"


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
