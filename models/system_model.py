"""
系統資訊模型
處理系統狀態和資訊獲取
"""

import platform
import os
import logging
import psutil if psutil else None

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

class SystemModel:
    """系統資訊模型"""
    
    @staticmethod
    def get_system_info():
        """獲取系統基本資訊"""
        return {
            'platform': platform.system(),
            'platform_version': platform.release(),
            'python_version': platform.python_version(),
            'working_directory': os.getcwd(),
            'psutil_available': PSUTIL_AVAILABLE
        }
    
    @staticmethod
    def get_system_stats():
        """獲取系統統計資訊"""
        if not PSUTIL_AVAILABLE:
            return {
                'success': False,
                'error': 'psutil 未安裝，系統監控功能受限'
            }
        
        try:
            # CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 記憶體資訊
            memory = psutil.virtual_memory()
            memory_info = {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent,
                'used': memory.used,
                'free': memory.free
            }
            
            # 磁碟資訊
            disk = psutil.disk_usage('/')
            disk_info = {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': (disk.used / disk.total) * 100
            }
            
            # 網路資訊
            network = psutil.net_io_counters()
            network_info = {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv
            }
            
            return {
                'success': True,
                'cpu_percent': cpu_percent,
                'memory': memory_info,
                'disk': disk_info,
                'network': network_info
            }
        
        except Exception as e:
            logging.error(f"獲取系統統計資訊失敗: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_detailed_system_info():
        """獲取詳細系統資訊"""
        basic_info = SystemModel.get_system_info()
        stats = SystemModel.get_system_stats()
        
        return {
            'basic': basic_info,
            'stats': stats,
            'timestamp': os.path.getmtime(__file__) if os.path.exists(__file__) else None
        }