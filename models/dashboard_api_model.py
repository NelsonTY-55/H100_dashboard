"""
Dashboard API 模型
處理 Dashboard API 相關的數據邏輯和業務規則
"""

import os
import json
import logging
import platform
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple


class DashboardAPIModel:
    """Dashboard API 資料模型"""
    
    def __init__(self):
        """初始化 Dashboard API 模型"""
        self.logger = logging.getLogger(__name__)
        self.start_time = time.time()
        
    def get_basic_system_info(self) -> Dict[str, Any]:
        """取得基本系統資訊"""
        try:
            import psutil
            
            # CPU 資訊
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # 記憶體資訊
            memory = psutil.virtual_memory()
            
            # 磁碟資訊
            disk_usage = psutil.disk_usage('/')
            
            return {
                'platform': platform.system(),
                'platform_version': platform.version(),
                'hostname': platform.node(),
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'used': memory.used,
                    'percent': memory.percent
                },
                'disk': {
                    'total': disk_usage.total,
                    'used': disk_usage.used,
                    'free': disk_usage.free,
                    'percent': (disk_usage.used / disk_usage.total) * 100
                }
            }
        except ImportError:
            return {
                'platform': platform.system(),
                'platform_version': platform.version(),
                'hostname': platform.node(),
                'note': 'psutil 未安裝，系統資訊有限'
            }
    
    def get_performance_data(self) -> Dict[str, Any]:
        """取得效能資料"""
        try:
            import psutil
            
            # CPU 使用率（過去1秒）
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 記憶體使用率
            memory = psutil.virtual_memory()
            
            # 磁碟 I/O
            disk_io = psutil.disk_io_counters()
            
            # 網路 I/O
            net_io = psutil.net_io_counters()
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_io': {
                    'read_bytes': disk_io.read_bytes if disk_io else 0,
                    'write_bytes': disk_io.write_bytes if disk_io else 0
                },
                'network_io': {
                    'bytes_sent': net_io.bytes_sent if net_io else 0,
                    'bytes_recv': net_io.bytes_recv if net_io else 0
                }
            }
        except ImportError:
            return {
                'note': 'psutil 未安裝，效能資料無法取得'
            }
    
    def get_network_info(self) -> Dict[str, Any]:
        """取得網路資訊"""
        try:
            import psutil
            
            # 網路介面
            net_if_addrs = psutil.net_if_addrs()
            interfaces = {}
            
            for interface, addrs in net_if_addrs.items():
                interfaces[interface] = []
                for addr in addrs:
                    interfaces[interface].append({
                        'family': str(addr.family),
                        'address': addr.address,
                        'netmask': addr.netmask,
                        'broadcast': addr.broadcast
                    })
            
            return {
                'interfaces': interfaces
            }
        except ImportError:
            return {
                'note': 'psutil 未安裝，網路資訊無法取得'
            }
    
    def get_storage_info(self) -> Dict[str, Any]:
        """取得儲存資訊"""
        try:
            import psutil
            
            # 磁碟分割
            partitions = psutil.disk_partitions()
            storage_info = []
            
            for partition in partitions:
                try:
                    partition_usage = psutil.disk_usage(partition.mountpoint)
                    storage_info.append({
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'fstype': partition.fstype,
                        'total': partition_usage.total,
                        'used': partition_usage.used,
                        'free': partition_usage.free,
                        'percent': (partition_usage.used / partition_usage.total) * 100
                    })
                except PermissionError:
                    continue
            
            return {
                'partitions': storage_info
            }
        except ImportError:
            return {
                'note': 'psutil 未安裝，儲存資訊無法取得'
            }
    
    def get_basic_config(self) -> Dict[str, Any]:
        """取得基本設定"""
        config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.json')
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {'note': '設定檔不存在'}
        except Exception as e:
            return {'error': f'讀取設定檔失敗: {str(e)}'}
    
    def check_database_status(self) -> str:
        """檢查資料庫狀態"""
        try:
            # 這裡可以加入實際的資料庫連線檢查
            return 'unknown'
        except:
            return 'error'
    
    def check_uart_status(self) -> str:
        """檢查 UART 狀態"""
        try:
            # 這裡可以加入實際的 UART 狀態檢查
            return 'unknown'
        except:
            return 'error'
    
    def check_wifi_status(self) -> str:
        """檢查 WiFi 狀態"""
        try:
            # 這裡可以加入實際的 WiFi 狀態檢查
            return 'unknown'
        except:
            return 'error'
    
    def get_uptime(self) -> str:
        """取得服務運行時間"""
        uptime_seconds = time.time() - self.start_time
        return f"{uptime_seconds:.2f} 秒"
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """取得完整的儀表板資料"""
        return {
            'system': self.get_basic_system_info(),
            'performance': self.get_performance_data(),
            'network': self.get_network_info(),
            'storage': self.get_storage_info()
        }
    
    def get_service_status(self) -> Dict[str, Any]:
        """取得服務狀態"""
        return {
            'api_service': 'running',
            'database': self.check_database_status(),
            'uart': self.check_uart_status(),
            'wifi': self.check_wifi_status(),
            'last_update': datetime.now().isoformat()
        }