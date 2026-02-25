import requests
import os
from datetime import datetime, timedelta
from .utilities import read_config

class ThreadsSearchAPI:
    def __init__(self):
        config = read_config('config/config.txt')
        self.access_token = config.get('THREADS_ACCESS_TOKEN', '')
        self.base_url = "https://graph.threads.net/v1.0"
    
    def search_threads(self, query, limit=10, days_back=3):
        """搜尋 Threads 內容 - 預設搜尋最近3天"""
        url = f"{self.base_url}/me/threads_search"
        
        # 檢查 token 是否存在
        if not self.access_token:
            return {'error': '未設定 THREADS_ACCESS_TOKEN，請在 config.txt 中設定'}
        
        # 計算時間範圍
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        params = {
            'access_token': self.access_token,
            'q': query,
            'limit': limit,
            'fields': 'id,text,permalink,timestamp,media_type,media_url,username',
            'since': int(start_date.timestamp()),
            'until': int(end_date.timestamp())
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {'error': str(e)}

def search_threads_content(query, days=3):
    """搜尋 Threads 內容的主要函數 - 預設3天"""
    api = ThreadsSearchAPI()
    return api.search_threads(query, days_back=days)