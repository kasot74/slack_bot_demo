import requests
import re
import time
import random

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
        
        # 4. 提取網頁標題
        title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else "無標題"
        
        # 5. 精細清理內容
        # 移除不可見的腳本與樣式
        clean_content = re.sub(r'<(script|style).*?>.*?</\1>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
        # 移除所有 HTML 標籤
        clean_content = re.sub(r'<.*?>', '', clean_content, flags=re.DOTALL)
        
        # 處理 HTML 轉義字元
        clean_content = re.sub(r'&nbsp;', ' ', clean_content)
        clean_content = re.sub(r'&quot;', '"', clean_content)
        clean_content = re.sub(r'&amp;', '&', clean_content)
        clean_content = re.sub(r'&lt;', '<', clean_content)
        clean_content = re.sub(r'&gt;', '>', clean_content)

        # 移除過多重複的換行與空白
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
        return f"錯誤：網頁回應錯誤 (HTTP {e.response.status_code})，無法獲取內容。"
    except Exception as e:
        return f"錯誤：處理網頁時發生非預期問題: {str(e)}"

def google_search(query: str) -> str:
    """搜尋 Google 並回傳前 3 個有機搜尋結果網址。
    
    Args:
        query (str): 搜尋關鍵字
        
    Returns:
        str: 格式化後的網址列表
    """
    try:
        # 1. 延遲模擬，隨機等待 1~3 秒以降低被偵測風險
        time.sleep(random.uniform(1.0, 3.0))

        # 2. 使用桌面版 User-Agent 以獲取包含 id="search" 的標準結構
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.google.com/'
        }
        
        search_url = f"https://www.google.com/search?q={query}&num=15"
        response = requests.get(search_url, headers=headers, timeout=12)
        response.raise_for_status()
        return response
        # 3. 限縮範圍：抓取包含 id="search" 的 <div> 區塊
        # 使用非貪婪匹配來獲取 search 區塊內容
        search_block_match = re.search(r'<div[^>]*id="search"[^>]*>(.*?)</div>\s*<div[^>]*id="foot"', response.text, re.DOTALL | re.IGNORECASE)
        
        # 如果找不到 search block，則退而求其次使用全文 (提高容錯)
        search_content = search_block_match.group(1) if search_block_match else response.text
        
        # 4. 提取網址
        # 嘗試提取 Google 典型的結果連結格式
        links_basic = re.findall(r'href="/url\?q=(https?://[^"&]+)', search_content)
        links_direct = re.findall(r'href="(https?://[^"&]+)"', search_content)
        
        all_links = links_basic + links_direct        
        filtered_urls = []
        
        # 排除清單
        exclude_keywords = [
            'google.com', 'googleadservices', 'youtube.com', 'accounts.google',
            'facebook.com', 'instagram.com', 'twitter.com', 'support.google',
            'maps.google', 'play.google', 'whatsapp.com', 'dictionary.cambridge',
            'moe.edu.tw' # 排除教育部辭典等通常不需 AI 讀取全文的站點
        ]

        for url in all_links:
            # 清洗網址：移除 Google 的跳轉參數
            clean_url = url.split('&')[0]
            
            # 排除特定網域
            if any(domain in clean_url for domain in exclude_keywords):
                continue
                                    
            # 加入未重複且合法的網址
            if clean_url not in filtered_urls:
                filtered_urls.append(clean_url)
            
            # 達標 3 個就停止
            if len(filtered_urls) >= 3:
                break
                
        if not filtered_urls:
            return f"找不到關於 '{query}' 的相關有機結果。"
            
        result_text = f"關於 '{query}' 的 Google 搜尋前 3 名網址：\n"
        for i, url in enumerate(filtered_urls, 1):
            result_text += f"{i}. {url}\n"
            
        return result_text
        
    except Exception as e:
        return f"Google 爬取失敗: {str(e)}"
