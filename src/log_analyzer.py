"""
Access Log Analyzer Module
處理和分析網站存取記錄檔的模組
"""

import re
import json
from datetime import datetime
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
import ipaddress
from .database import con_db
from .utilities import read_config


class AccessLogEntry:
    """表示單一存取記錄的類別"""
    
    def __init__(self, line: str):
        self.raw_line = line.strip()
        self.parse_line()
    
    def parse_line(self):
        """解析存取記錄行"""
        # Apache/Nginx Common Log Format 正規表達式
        pattern = r'^(\S+) \S+ \S+ \[([^\]]+)\] "([^"]*)" (\d+) (\d+|-) "([^"]*)" "([^"]*)" "([^"]*)"'
        
        match = re.match(pattern, self.raw_line)
        if match:
            self.ip_address = match.group(1)
            self.timestamp = match.group(2)
            self.request = match.group(3)
            self.status_code = int(match.group(4))
            self.response_size = match.group(5) if match.group(5) != '-' else 0
            self.referer = match.group(6) if match.group(6) != '-' else None
            self.user_agent = match.group(7) if match.group(7) != '-' else None
            self.extra = match.group(8) if match.group(8) != '-' else None
            
            # 解析請求詳情
            self.parse_request()
            
            # 解析時間戳
            self.parse_timestamp()
        else:
            # 處理無法解析的行
            self.ip_address = None
            self.timestamp = None
            self.request = self.raw_line
            self.status_code = None
            self.response_size = 0
            self.referer = None
            self.user_agent = None
            self.extra = None
            self.method = None
            self.url = None
            self.protocol = None
            self.datetime_obj = None
    
    def parse_request(self):
        """解析HTTP請求字串"""
        if self.request:
            parts = self.request.split()
            if len(parts) >= 2:
                self.method = parts[0]
                self.url = parts[1]
                self.protocol = parts[2] if len(parts) > 2 else None
            else:
                self.method = None
                self.url = self.request
                self.protocol = None
        else:
            self.method = None
            self.url = None
            self.protocol = None
    
    def parse_timestamp(self):
        """解析時間戳為datetime物件"""
        if self.timestamp:
            try:
                # 格式: 22/Jul/2025:01:54:28 +0000
                self.datetime_obj = datetime.strptime(
                    self.timestamp.split()[0], 
                    "%d/%b/%Y:%H:%M:%S"
                )
            except:
                self.datetime_obj = None
        else:
            self.datetime_obj = None
    
    def is_valid(self) -> bool:
        """檢查記錄是否有效"""
        return self.ip_address is not None and self.status_code is not None
    
    def is_bot(self) -> bool:
        """檢查是否為機器人存取"""
        if not self.user_agent:
            return False
        
        bot_indicators = [
            'bot', 'crawler', 'spider', 'scraper', 'wget', 'curl',
            'Googlebot', 'Bingbot', 'facebookexternalhit', 'Twitterbot',
            'zgrab', 'CensysInspect', 'OAI-SearchBot'
        ]
        
        user_agent_lower = self.user_agent.lower()
        return any(indicator.lower() in user_agent_lower for indicator in bot_indicators)
    
    def get_file_extension(self) -> Optional[str]:
        """取得請求檔案的副檔名"""
        if not self.url:
            return None
        
        # 移除查詢參數
        url_path = self.url.split('?')[0]
        if '.' in url_path:
            return url_path.split('.')[-1].lower()
        return None
    
    def to_dict(self) -> Dict:
        """轉換為字典格式"""
        return {
            'ip_address': self.ip_address,
            'timestamp': self.timestamp,
            'datetime': self.datetime_obj.isoformat() if self.datetime_obj else None,
            'method': self.method,
            'url': self.url,
            'protocol': self.protocol,
            'status_code': self.status_code,
            'response_size': int(self.response_size) if isinstance(self.response_size, str) and self.response_size.isdigit() else 0,
            'referer': self.referer,
            'user_agent': self.user_agent,
            'extra': self.extra,
            'is_bot': self.is_bot(),
            'file_extension': self.get_file_extension(),
            'created_at': datetime.now().isoformat()
        }


class AccessLogAnalyzer:
    """存取記錄分析器"""
    
    def __init__(self, log_file_path: str, use_database: bool = False):
        self.log_file_path = Path(log_file_path)
        self.entries: List[AccessLogEntry] = []
        self.stats = {}
        self.use_database = use_database
        self.db = None
        
        if use_database:
            self._init_database()
    
    def _init_database(self):
        """初始化資料庫連線"""
        try:
            config = read_config('config/config.txt')
            self.db = con_db(config)
            print("✓ 資料庫連線成功")
        except Exception as e:
            print(f"資料庫連線失敗: {e}")
            self.use_database = False
    
    def save_entry_to_db(self, entry: AccessLogEntry) -> bool:
        """將單筆記錄儲存到資料庫"""
        if not self.use_database or not self.db:
            return False
        
        try:
            collection = self.db.access_logs
            entry_data = entry.to_dict()
            
            # 建立唯一識別碼
            unique_key = f"{entry.ip_address}_{entry.timestamp}_{entry.url}_{entry.status_code}"
            entry_data['unique_key'] = unique_key
            
            # 使用 upsert 避免重複
            result = collection.update_one(
                {'unique_key': unique_key},
                {'$set': entry_data},
                upsert=True
            )
            
            return result.upserted_id is not None or result.modified_count > 0
            
        except Exception as e:
            print(f"儲存記錄失敗: {e}")
            return False
    
    def save_all_entries_to_db(self) -> int:
        """將所有記錄批次儲存到資料庫"""
        if not self.use_database or not self.db:
            return 0
        
        saved_count = 0
        collection = self.db.access_logs
        
        try:
            # 使用更高效的批次操作
            batch_data = []
            
            for entry in self.entries:
                entry_data = entry.to_dict()
                # 建立唯一識別碼用於去重
                entry_data['unique_key'] = f"{entry.ip_address}_{entry.timestamp}_{entry.url}_{entry.status_code}"
                batch_data.append(entry_data)
            
            if batch_data:
                # 使用 upsert 批次操作，避免重複
                for data in batch_data:
                    try:
                        result = collection.update_one(
                            {'unique_key': data['unique_key']},
                            {'$set': data},
                            upsert=True
                        )
                        if result.upserted_id or result.modified_count > 0:
                            saved_count += 1
                    except Exception as e:
                        print(f"儲存單筆記錄失敗: {e}")
                        continue
                
        except Exception as e:
            print(f"批次儲存失敗: {e}")
        
        return saved_count
    
    def create_database_indexes(self):
        """建立資料庫索引以提升查詢效能"""
        if not self.use_database or not self.db:
            return
        
        try:
            collection = self.db.access_logs
            
            # 建立索引
            collection.create_index("ip_address")
            collection.create_index("timestamp")
            collection.create_index("status_code")
            collection.create_index("datetime")
            collection.create_index("unique_key", unique=True)  # 唯一索引
            collection.create_index([("ip_address", 1), ("timestamp", 1)])
            
            print("✓ 資料庫索引建立完成")
        except Exception as e:
            print(f"建立索引失敗: {e}")
    
    def get_entries_from_db(self, limit: int = 1000, filter_dict: Dict = None) -> List[Dict]:
        """從資料庫取得記錄"""
        if not self.use_database or not self.db:
            return []
        
        try:
            collection = self.db.access_logs
            query = filter_dict or {}
            
            cursor = collection.find(query).limit(limit).sort("datetime", -1)
            return list(cursor)
            
        except Exception as e:
            print(f"從資料庫取得資料失敗: {e}")
            return []
    
    def load_log_file(self, max_lines: Optional[int] = None, save_to_db: bool = False) -> int:
        """載入記錄檔"""
        self.entries = []
        
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                lines_read = 0
                for line in f:
                    if max_lines and lines_read >= max_lines:
                        break
                    
                    entry = AccessLogEntry(line)
                    if entry.is_valid():
                        self.entries.append(entry)
                        
                        # 選擇性儲存到資料庫
                        if save_to_db and self.use_database:
                            self.save_entry_to_db(entry)
                            
                    lines_read += 1
            
            # 如果選擇批次儲存到資料庫
            if save_to_db and self.use_database and self.entries:
                saved_count = self.save_all_entries_to_db()
                print(f"✓ 已儲存 {saved_count} 筆新記錄到資料庫")
                
            return len(self.entries)
        except Exception as e:
            raise Exception(f"無法載入記錄檔: {e}")
    
    def get_top_ips(self, limit: int = 10) -> List[Tuple[str, int]]:
        """取得最常存取的IP位址"""
        ip_counter = Counter(entry.ip_address for entry in self.entries if entry.ip_address)
        return ip_counter.most_common(limit)
    
    def get_status_code_distribution(self) -> Dict[int, int]:
        """取得狀態碼分佈"""
        return dict(Counter(entry.status_code for entry in self.entries if entry.status_code))
    
    def get_most_requested_urls(self, limit: int = 10) -> List[Tuple[str, int]]:
        """取得最常被請求的URL"""
        url_counter = Counter(entry.url for entry in self.entries if entry.url)
        return url_counter.most_common(limit)
    
    def get_user_agent_stats(self, limit: int = 10) -> List[Tuple[str, int]]:
        """取得User Agent統計"""
        ua_counter = Counter(entry.user_agent for entry in self.entries if entry.user_agent)
        return ua_counter.most_common(limit)
    
    def get_bot_traffic_ratio(self) -> float:
        """取得機器人流量比例"""
        if not self.entries:
            return 0.0
        
        bot_count = sum(1 for entry in self.entries if entry.is_bot())
        return bot_count / len(self.entries)
    
    def get_error_requests(self, status_codes: List[int] = [404, 400, 403, 500, 502, 503]) -> List[AccessLogEntry]:
        """取得錯誤請求"""
        return [entry for entry in self.entries if entry.status_code in status_codes]
    
    def get_large_responses(self, min_size: int = 1000000) -> List[AccessLogEntry]:
        """取得大型回應"""
        return [entry for entry in self.entries 
                if isinstance(entry.response_size, int) and entry.response_size > min_size]
    
    def get_suspicious_requests(self) -> List[AccessLogEntry]:
        """取得可疑請求"""
        suspicious = []
        
        for entry in self.entries:
            if not entry.url:
                continue
                
            url_lower = entry.url.lower()
            
            # 檢查可疑路徑
            suspicious_patterns = [
                'shell', 'admin', 'login', 'password', 'wp-admin', 
                'phpmyadmin', 'config', '.git', '.env', 'backup',
                'sql', 'dump', 'exploit', 'hack'
            ]
            
            if any(pattern in url_lower for pattern in suspicious_patterns):
                suspicious.append(entry)
            
            # 檢查異常狀態碼
            elif entry.status_code in [400, 401, 403, 404]:
                suspicious.append(entry)
        
        return suspicious
    
    def get_hourly_traffic(self) -> Dict[int, int]:
        """取得每小時流量分佈"""
        hourly_traffic = defaultdict(int)
        
        for entry in self.entries:
            if entry.datetime_obj:
                hourly_traffic[entry.datetime_obj.hour] += 1
        
        return dict(hourly_traffic)
    
    def get_file_type_requests(self) -> Dict[str, int]:
        """取得檔案類型請求統計"""
        file_types = Counter()
        
        for entry in self.entries:
            ext = entry.get_file_extension()
            if ext:
                file_types[ext] += 1
        
        return dict(file_types)
    
    def analyze(self) -> Dict:
        """執行完整分析"""
        if not self.entries:
            return {"error": "沒有載入任何記錄"}
        
        analysis = {
            "總記錄數": len(self.entries),
            "分析時間": datetime.now().isoformat(),
            "前10個IP位址": self.get_top_ips(10),
            "狀態碼分佈": self.get_status_code_distribution(),
            "前10個請求URL": self.get_most_requested_urls(10),
            "前10個User Agent": self.get_user_agent_stats(10),
            "機器人流量比例": f"{self.get_bot_traffic_ratio():.2%}",
            "錯誤請求數": len(self.get_error_requests()),
            "可疑請求數": len(self.get_suspicious_requests()),
            "每小時流量": self.get_hourly_traffic(),
            "檔案類型請求": self.get_file_type_requests()
        }
        
        self.stats = analysis
        return analysis
    
    def export_analysis_to_json(self, output_file: str):
        """匯出分析結果為JSON"""
        if not self.stats:
            self.analyze()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2, default=str)
    
    def get_ip_geolocation_summary(self) -> Dict[str, List[str]]:
        """取得IP位址地理位置摘要（基於IP範圍的基本判斷）"""
        ip_ranges = {
            "私有網路": [],
            "本地網路": [],
            "公共網路": []
        }
        
        for entry in self.entries:
            if not entry.ip_address:
                continue
                
            try:
                ip = ipaddress.ip_address(entry.ip_address)
                if ip.is_private:
                    if entry.ip_address not in ip_ranges["私有網路"]:
                        ip_ranges["私有網路"].append(entry.ip_address)
                elif ip.is_loopback:
                    if entry.ip_address not in ip_ranges["本地網路"]:
                        ip_ranges["本地網路"].append(entry.ip_address)
                else:
                    if entry.ip_address not in ip_ranges["公共網路"]:
                        ip_ranges["公共網路"].append(entry.ip_address)
            except:
                continue
        
        return ip_ranges
    
    def generate_report(self) -> str:
        """產生分析報告"""
        if not self.stats:
            self.analyze()
        
        report = f"""
=== 存取記錄分析報告 ===
檔案: {self.log_file_path.name}
分析時間: {self.stats.get('分析時間', 'N/A')}
總記錄數: {self.stats.get('總記錄數', 0)}

=== 流量概況 ===
機器人流量比例: {self.stats.get('機器人流量比例', 'N/A')}
錯誤請求數: {self.stats.get('錯誤請求數', 0)}
可疑請求數: {self.stats.get('可疑請求數', 0)}

=== 前5個最常存取的IP位址 ===
"""
        
        top_ips = self.stats.get('前10個IP位址', [])[:5]
        for i, (ip, count) in enumerate(top_ips, 1):
            report += f"{i}. {ip}: {count} 次\n"
        
        report += "\n=== 狀態碼分佈 ===\n"
        status_codes = self.stats.get('狀態碼分佈', {})
        for code, count in sorted(status_codes.items()):
            report += f"{code}: {count} 次\n"
        
        report += "\n=== 前5個最常請求的URL ===\n"
        top_urls = self.stats.get('前10個請求URL', [])[:5]
        for i, (url, count) in enumerate(top_urls, 1):
            report += f"{i}. {url}: {count} 次\n"
        
        return report


def main():
    """主函式 - 示例用法"""
    log_file = "access.log"
    
    if not Path(log_file).exists():
        print(f"找不到記錄檔: {log_file}")
        return
    
    # 建立分析器
    analyzer = AccessLogAnalyzer(log_file)
    
    # 載入記錄檔（限制讀取1000行以加快處理速度）
    print("正在載入記錄檔...")
    entries_loaded = analyzer.load_log_file(max_lines=1000)
    print(f"已載入 {entries_loaded} 筆有效記錄")
    
    # 執行分析
    print("正在分析...")
    analyzer.analyze()
    
    # 顯示報告
    print(analyzer.generate_report())
    
    # 匯出JSON報告
    analyzer.export_analysis_to_json("access_log_analysis.json")
    print("分析結果已匯出到 access_log_analysis.json")


if __name__ == "__main__":
    main()