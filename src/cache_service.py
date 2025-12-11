import redis
import json
import pickle
from datetime import timedelta
from typing import Any, Optional, Union
from .utilities import read_config

class CacheService:
    def __init__(self):
        self.config = read_config()
        # Redis 連線設定
        self.redis_client = redis.Redis(
            host=self.config.get('REDIS_HOST', 'localhost'),
            port=int(self.config.get('REDIS_PORT', 6379)),
            db=int(self.config.get('REDIS_DB', 0)),
            decode_responses=False,  # 保持二進制模式以支持 pickle
            socket_connect_timeout=5,
            socket_timeout=5
        )
        
    def set(self, key: str, value: Any, expire_time: Optional[Union[int, timedelta]] = None) -> bool:
        """
        設置快取值
        :param key: 快取鍵
        :param value: 快取值
        :param expire_time: 過期時間（秒或 timedelta 對象），默認不過期
        :return: 是否成功
        """
        try:
            serialized_value = pickle.dumps(value)
            result = self.redis_client.set(key, serialized_value, ex=expire_time)
            return result
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        獲取快取值
        :param key: 快取鍵
        :return: 快取值，如果不存在或過期則返回 None
        """
        try:
            cached_value = self.redis_client.get(key)
            if cached_value is None:
                return None
            return pickle.loads(cached_value)
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """
        刪除快取
        :param key: 快取鍵
        :return: 是否成功
        """
        try:
            result = self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        檢查快取是否存在
        :param key: 快取鍵
        :return: 是否存在
        """
        try:
            return self.redis_client.exists(key) > 0
        except Exception as e:
            print(f"Cache exists error: {e}")
            return False
    
    def clear_all(self) -> bool:
        """
        清除所有快取
        :return: 是否成功
        """
        try:
            self.redis_client.flushdb()
            return True
        except Exception as e:
            print(f"Cache clear error: {e}")
            return False
    
    def set_with_pattern(self, pattern: str, data: dict, expire_time: Optional[Union[int, timedelta]] = None):
        """
        批量設置具有相同模式的快取
        :param pattern: 快取鍵模式
        :param data: 鍵值對字典
        :param expire_time: 過期時間
        """
        pipe = self.redis_client.pipeline()
        try:
            for key, value in data.items():
                full_key = f"{pattern}:{key}"
                serialized_value = pickle.dumps(value)
                pipe.set(full_key, serialized_value, ex=expire_time)
            pipe.execute()
            return True
        except Exception as e:
            print(f"Cache batch set error: {e}")
            return False
    
    def get_by_pattern(self, pattern: str) -> dict:
        """
        根據模式獲取快取
        :param pattern: 快取鍵模式
        :return: 匹配的鍵值對字典
        """
        try:
            keys = self.redis_client.keys(f"{pattern}:*")
            if not keys:
                return {}
            
            result = {}
            for key in keys:
                value = self.redis_client.get(key)
                if value:
                    # 移除模式前綴
                    clean_key = key.decode('utf-8').replace(f"{pattern}:", "")
                    result[clean_key] = pickle.loads(value)
            return result
        except Exception as e:
            print(f"Cache pattern get error: {e}")
            return {}

# 創建全域快取實例
cache = CacheService()