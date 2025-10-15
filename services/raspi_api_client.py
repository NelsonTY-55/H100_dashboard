"""
RAS_pi API 客戶端
專門處理與 RAS_pi 系統的 API 通訊，提供即時資料獲取功能
"""

# 修正 charset_normalizer 循環導入問題
import sys
import warnings
import os

# 設置環境變數
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
warnings.filterwarnings('ignore', category=UserWarning, module='charset_normalizer')

# 嘗試安全導入 requests
REQUESTS_AVAILABLE = False
try:
    # 先清理可能問題的模組
    charset_mod_keys = [k for k in sys.modules.keys() if 'charset' in k.lower()]
    for key in charset_mod_keys:
        if key in sys.modules:
            del sys.modules[key]
    
    import charset_normalizer
    getattr(charset_normalizer, '__version__', None)
    import requests
    REQUESTS_AVAILABLE = True
except (ImportError, AttributeError) as e:
    print(f"Warning: requests module unavailable: {e}")
    # 創建一個假的 requests 模組來避免錯誤
    class MockRequests:
        class Response:
            def __init__(self):
                self.status_code = 503
                self.text = "Service Unavailable - requests module not available"
            def json(self):
                return {"error": "requests module not available"}
        
        @staticmethod
        def get(*args, **kwargs):
            return MockRequests.Response()
        
        @staticmethod
        def post(*args, **kwargs):
            return MockRequests.Response()
    
    requests = MockRequests()
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import time
from dataclasses import dataclass


@dataclass
class RaspberryPiConfig:
    """RAS_pi 連接配置"""
    host: str = "192.168.113.239"
    port: int = 5000
    timeout: int = 10
    retry_count: int = 3
    retry_delay: float = 1.0
    poll_interval: int = 5  # 輪詢間隔（秒）


class RaspberryPiApiClient:
    """RAS_pi API 客戶端"""
    
    def __init__(self, config: RaspberryPiConfig = None):
        self.config = config or RaspberryPiConfig()
        self.logger = logging.getLogger(__name__)
        self.base_url = f"http://{self.config.host}:{self.config.port}"
        self.session = requests.Session()
        self.session.timeout = self.config.timeout
        
        # 連接狀態
        self.is_connected = False
        self.last_check_time = None
        self.connection_errors = 0
        
        # 快取機制
        self.cache = {}
        self.cache_ttl = {}
        
    def _make_request(self, endpoint: str, method: str = 'GET', data: Dict = None, 
                     use_cache: bool = False, cache_ttl: int = 30) -> Tuple[bool, Dict]:
        """發送 HTTP 請求到 RAS_pi"""
        
        # 檢查快取
        cache_key = f"{method}:{endpoint}:{json.dumps(data) if data else ''}"
        if use_cache and cache_key in self.cache:
            cache_time = self.cache_ttl.get(cache_key, datetime.min)
            if datetime.now() - cache_time < timedelta(seconds=cache_ttl):
                return True, self.cache[cache_key]
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.config.retry_count):
            try:
                if method.upper() == 'GET':
                    response = self.session.get(url, params=data)
                elif method.upper() == 'POST':
                    response = self.session.post(url, json=data)
                else:
                    response = self.session.request(method, url, json=data)
                
                response.raise_for_status()
                result = response.json()
                
                # 更新連接狀態
                self.is_connected = True
                self.connection_errors = 0
                self.last_check_time = datetime.now()
                
                # 更新快取
                if use_cache:
                    self.cache[cache_key] = result
                    self.cache_ttl[cache_key] = datetime.now()
                
                return True, result
                
            except requests.exceptions.RequestException as e:
                self.connection_errors += 1
                self.logger.warning(f"RAS_pi API 請求失敗 (嘗試 {attempt + 1}/{self.config.retry_count}): {e}")
                
                if attempt < self.config.retry_count - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    self.is_connected = False
                    self.logger.error(f"RAS_pi API 連接失敗，所有重試已用盡: {e}")
                    return False, {'error': str(e), 'success': False}
            
            except Exception as e:
                self.logger.error(f"RAS_pi API 請求發生未預期錯誤: {e}")
                return False, {'error': str(e), 'success': False}
        
        return False, {'error': 'All retry attempts failed', 'success': False}
    
    def health_check(self) -> Tuple[bool, Dict]:
        """健康檢查"""
        return self._make_request('/api/health', use_cache=True, cache_ttl=10)
    
    def get_status(self) -> Tuple[bool, Dict]:
        """獲取系統狀態"""
        return self._make_request('/api/status', use_cache=True, cache_ttl=15)
    
    def get_uart_status(self) -> Tuple[bool, Dict]:
        """獲取 UART 狀態"""
        return self._make_request('/api/uart/status', use_cache=True, cache_ttl=5)
    
    def get_uart_mac_ids(self) -> Tuple[bool, List[str]]:
        """獲取 UART MAC ID 列表"""
        success, result = self._make_request('/api/uart/mac-ids', use_cache=True, cache_ttl=10)
        if success and result.get('success'):
            return True, result.get('mac_ids', [])
        return False, []
    
    def get_uart_mac_channels(self, mac_id: str = None) -> Tuple[bool, Dict]:
        """獲取 MAC ID 通道資訊"""
        if mac_id:
            endpoint = f'/api/uart/mac-channels/{mac_id}'
        else:
            endpoint = '/api/uart/mac-channels/'
        
        return self._make_request(endpoint, use_cache=True, cache_ttl=10)
    
    def get_uart_mac_data(self, mac_id: str, minutes: int = 10) -> Tuple[bool, List]:
        """獲取特定 MAC ID 的最近資料"""
        endpoint = f'/api/uart/mac-data/{mac_id}'
        params = {'minutes': minutes}
        
        success, result = self._make_request(endpoint, method='GET', data=params)
        if success and result.get('success'):
            return True, result.get('data', [])
        return False, []
    
    def get_dashboard_stats(self) -> Tuple[bool, Dict]:
        """獲取 Dashboard 統計資料"""
        return self._make_request('/api/dashboard/stats', use_cache=True, cache_ttl=20)
    
    def get_dashboard_overview(self) -> Tuple[bool, Dict]:
        """獲取 Dashboard 總覽資料"""
        return self._make_request('/api/dashboard/overview', use_cache=True, cache_ttl=15)
    
    def get_database_latest_data(self) -> Tuple[bool, Dict]:
        """獲取資料庫最新資料"""
        return self._make_request('/api/database/latest-data')
    
    def get_database_statistics(self) -> Tuple[bool, Dict]:
        """獲取資料庫統計資訊"""
        return self._make_request('/api/database/statistics', use_cache=True, cache_ttl=30)
    
    def start_uart(self) -> Tuple[bool, Dict]:
        """啟動 RAS_pi UART 讀取"""
        return self._make_request('/api/uart/start', method='POST')
    
    def stop_uart(self) -> Tuple[bool, Dict]:
        """停止 RAS_pi UART 讀取"""
        return self._make_request('/api/uart/stop', method='POST')
    
    def test_uart_connection(self) -> Tuple[bool, Dict]:
        """測試 RAS_pi UART 連接"""
        return self._make_request('/api/uart/test', method='POST')
    
    def get_connection_status(self) -> Dict:
        """獲取連接狀態資訊"""
        return {
            'connected': self.is_connected,
            'last_check': self.last_check_time.isoformat() if self.last_check_time else None,
            'connection_errors': self.connection_errors,
            'config': {
                'host': self.config.host,
                'port': self.config.port,
                'timeout': self.config.timeout
            }
        }
    
    def clear_cache(self):
        """清除快取"""
        self.cache.clear()
        self.cache_ttl.clear()
        self.logger.info("RAS_pi API 客戶端快取已清除")
    
    def close(self):
        """關閉客戶端"""
        if self.session:
            self.session.close()
        self.clear_cache()
        self.logger.info("RAS_pi API 客戶端已關閉")


class RaspberryPiDataAggregator:
    """RAS_pi 資料聚合器 - 整合多個 API 呼叫的結果"""
    
    def __init__(self, client: RaspberryPiApiClient):
        self.client = client
        self.logger = logging.getLogger(__name__)
    
    def get_complete_status(self) -> Dict:
        """獲取完整系統狀態"""
        result = {
            'success': False,
            'timestamp': datetime.now().isoformat(),
            'connection': self.client.get_connection_status(),
            'system': {},
            'uart': {},
            'dashboard': {},
            'database': {}
        }
        
        try:
            # 系統狀態
            success, system_data = self.client.get_status()
            if success:
                result['system'] = system_data
            
            # UART 狀態
            success, uart_data = self.client.get_uart_status()
            if success:
                result['uart'] = uart_data
            
            # Dashboard 統計
            success, dashboard_data = self.client.get_dashboard_stats()
            if success:
                result['dashboard'] = dashboard_data
            
            # 資料庫統計
            success, db_data = self.client.get_database_statistics()
            if success:
                result['database'] = db_data
            
            result['success'] = result['connection']['connected']
            
        except Exception as e:
            self.logger.error(f"獲取完整狀態時發生錯誤: {e}")
            result['error'] = str(e)
        
        return result
    
    def get_real_time_uart_summary(self) -> Dict:
        """獲取即時 UART 資料摘要"""
        result = {
            'success': False,
            'timestamp': datetime.now().isoformat(),
            'uart_active': False,
            'mac_ids': [],
            'total_mac_count': 0,
            'recent_data_points': 0,
            'channels_summary': {}
        }
        
        try:
            # UART 狀態
            success, uart_status = self.client.get_uart_status()
            if not success:
                return result
            
            result['uart_active'] = uart_status.get('success', False) and \
                                   uart_status.get('status') == 'running'
            
            if not result['uart_active']:
                result['success'] = True
                return result
            
            # MAC IDs
            success, mac_ids = self.client.get_uart_mac_ids()
            if success:
                result['mac_ids'] = mac_ids
                result['total_mac_count'] = len(mac_ids)
            
            # 各 MAC ID 的通道和資料統計
            recent_data_count = 0
            channels_summary = {}
            
            for mac_id in mac_ids[:5]:  # 限制前5個，避免過多 API 呼叫
                # 通道資訊
                success, channels_data = self.client.get_uart_mac_channels(mac_id)
                if success and channels_data.get('success'):
                    channel_count = len(channels_data.get('data', {}).get('channels', []))
                    channels_summary[mac_id] = {'channel_count': channel_count}
                
                # 最近資料
                success, recent_data = self.client.get_uart_mac_data(mac_id, minutes=1)
                if success:
                    data_count = len(recent_data)
                    recent_data_count += data_count
                    if mac_id in channels_summary:
                        channels_summary[mac_id]['recent_data_points'] = data_count
            
            result['recent_data_points'] = recent_data_count
            result['channels_summary'] = channels_summary
            result['success'] = True
            
        except Exception as e:
            self.logger.error(f"獲取 UART 摘要時發生錯誤: {e}")
            result['error'] = str(e)
        
        return result


# 全域實例
_raspi_client = None
_raspi_aggregator = None


def get_raspi_client(config: RaspberryPiConfig = None) -> RaspberryPiApiClient:
    """獲取 RAS_pi 客戶端實例（單例模式）"""
    global _raspi_client
    if _raspi_client is None:
        _raspi_client = RaspberryPiApiClient(config)
    return _raspi_client


def get_raspi_aggregator() -> RaspberryPiDataAggregator:
    """獲取 RAS_pi 資料聚合器實例（單例模式）"""
    global _raspi_aggregator
    if _raspi_aggregator is None:
        client = get_raspi_client()
        _raspi_aggregator = RaspberryPiDataAggregator(client)
    return _raspi_aggregator


def cleanup_raspi_client():
    """清理 RAS_pi 客戶端資源"""
    global _raspi_client, _raspi_aggregator
    if _raspi_client:
        _raspi_client.close()
        _raspi_client = None
    _raspi_aggregator = None