"""
Dashboard 模型
處理 Dashboard 相關的數據邏輯和業務規則
"""

import os
import json
import logging
import platform
import time
import threading
import glob
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple


class DashboardModel:
    """Dashboard 資料模型"""
    
    def __init__(self):
        """初始化 Dashboard 模型"""
        self.logger = logging.getLogger(__name__)
        
    def get_system_info(self) -> Dict[str, Any]:
        """取得系統資訊"""
        try:
            # 嘗試導入 psutil
            try:
                import psutil
                PSUTIL_AVAILABLE = True
            except ImportError:
                PSUTIL_AVAILABLE = False
                
            if PSUTIL_AVAILABLE:
                # 獲取系統統計
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # 網路統計
                net_io = psutil.net_io_counters()
                network_sent = net_io.bytes_sent if net_io else 0
                network_recv = net_io.bytes_recv if net_io else 0
                
                return {
                    'platform': platform.system(),
                    'platform_version': platform.version(),
                    'architecture': platform.architecture()[0],
                    'processor': platform.processor(),
                    'hostname': platform.node(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available': memory.available,
                    'memory_total': memory.total,
                    'disk_percent': disk.percent,
                    'disk_free': disk.free,
                    'disk_total': disk.total,
                    'network_sent': network_sent,
                    'network_recv': network_recv,
                    'psutil_available': True
                }
            else:
                return {
                    'platform': platform.system(),
                    'platform_version': platform.version(),
                    'architecture': platform.architecture()[0],
                    'processor': platform.processor(),
                    'hostname': platform.node(),
                    'cpu_percent': 0,
                    'memory_percent': 0,
                    'memory_available': 0,
                    'memory_total': 0,
                    'disk_percent': 0,
                    'disk_free': 0,
                    'disk_total': 0,
                    'network_sent': 0,
                    'network_recv': 0,
                    'psutil_available': False
                }
        except Exception as e:
            self.logger.error(f"取得系統資訊失敗: {e}")
            return {
                'platform': 'Unknown',
                'platform_version': 'Unknown',
                'architecture': 'Unknown',
                'processor': 'Unknown',
                'hostname': 'Unknown',
                'cpu_percent': 0,
                'memory_percent': 0,
                'memory_available': 0,
                'memory_total': 0,
                'disk_percent': 0,
                'disk_free': 0,
                'disk_total': 0,
                'network_sent': 0,
                'network_recv': 0,
                'psutil_available': False
            }
    
    def get_application_stats(self, uart_reader=None) -> Dict[str, Any]:
        """取得應用程式統計"""
        try:
            return {
                'uptime': datetime.now().isoformat(),
                'uart_connection': uart_reader.is_running if uart_reader else False,
                'total_devices': 0,  # 這裡可以從設備管理器獲取
                'active_connections': 1,
                'data_points_today': 0,  # 這裡可以從資料庫獲取
                'last_data_received': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"取得應用程式統計失敗: {e}")
            return {
                'uptime': datetime.now().isoformat(),
                'uart_connection': False,
                'total_devices': 0,
                'active_connections': 0,
                'data_points_today': 0,
                'last_data_received': None
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """取得健康狀態"""
        system_info = self.get_system_info()
        return {
            'status': 'healthy',
            'service': 'Dashboard API',
            'timestamp': datetime.now().isoformat(),
            'system_info': system_info
        }
    
    def get_service_status(self, uart_reader=None, device_settings_manager=None) -> Dict[str, Any]:
        """取得服務狀態"""
        try:
            # 嘗試導入 psutil
            try:
                import psutil
                PSUTIL_AVAILABLE = True
            except ImportError:
                PSUTIL_AVAILABLE = False
                
            return {
                'success': True,
                'service': 'Dashboard API',
                'version': '1.0.0',
                'uptime': datetime.now().isoformat(),
                'psutil_available': PSUTIL_AVAILABLE,
                'uart_connection': uart_reader.is_running if uart_reader else False,
                'device_configured': device_settings_manager.is_configured() if device_settings_manager else False
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'狀態檢查失敗: {str(e)}'
            }


class ChartDataModel:
    """圖表資料模型"""
    
    def __init__(self):
        """初始化圖表資料模型"""
        self.logger = logging.getLogger(__name__)
    
    def get_local_chart_data(self, mac_id: Optional[str] = None, limit: int = 1000) -> Dict[str, Any]:
        """取得本地圖表資料"""
        try:
            from uart_integrated import uart_reader
            
            if not uart_reader:
                return {
                    'success': False,
                    'message': 'UART Reader 未初始化',
                    'data': [],
                    'total_channels': 0,
                    'source': '錯誤',
                    'raspberry_pi_ip': '本地主機',
                    'timestamp': datetime.now().isoformat()
                }
            
            # 從 uart_reader 獲取資料
            raw_data = uart_reader.get_data()
            
            if not raw_data or len(raw_data) == 0:
                return {
                    'success': True,
                    'data': [],
                    'total_channels': 0,
                    'filtered_by_mac_id': mac_id,
                    'data_source': '本地CSV文件 (無數據)',
                    'source': '本地主機',
                    'raspberry_pi_ip': '本地主機',
                    'timestamp': datetime.now().isoformat()
                }
            
            # 處理本地數據
            chart_data = {}
            
            # 限制數據量
            if len(raw_data) > limit:
                raw_data = raw_data[-limit:]
            
            # 處理數據 - 按通道分組
            for entry in raw_data:
                if mac_id and entry.get('mac_id') != mac_id:
                    continue
                
                channels = entry.get('channels', [])
                timestamp = entry.get('timestamp', datetime.now().isoformat())
                entry_mac_id = entry.get('mac_id', 'unknown')
                
                for channel_data in channels:
                    channel_name = f"MAC_{entry_mac_id}_CH{channel_data.get('channel', 0)}"
                    
                    if channel_name not in chart_data:
                        chart_data[channel_name] = {
                            'label': channel_name,
                            'data': [],
                            'mac_id': entry_mac_id,
                            'channel': channel_data.get('channel', 0)
                        }
                    
                    chart_data[channel_name]['data'].append({
                        'x': timestamp,
                        'y': channel_data.get('current', 0)
                    })
            
            # 轉換為列表格式
            final_data = list(chart_data.values())
            
            return {
                'success': True,
                'data': final_data,
                'total_channels': len(final_data),
                'filtered_by_mac_id': mac_id,
                'data_source': '本地UART數據',
                'source': '本地主機',
                'raspberry_pi_ip': '本地主機',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"取得本地圖表資料失敗: {e}")
            return {
                'success': False,
                'message': f'獲取圖表數據失敗: {str(e)}',
                'data': [],
                'total_channels': 0,
                'source': '錯誤',
                'raspberry_pi_ip': '本地主機',
                'timestamp': datetime.now().isoformat()
            }


class DatabaseModel:
    """資料庫資料模型"""
    
    def __init__(self, db_manager=None):
        """初始化資料庫模型"""
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        self.database_available = db_manager is not None
    
    def get_chart_data(self, factory_area=None, floor_level=None, mac_id=None, 
                      device_model=None, data_type='temperature', limit=1000,
                      start_time=None, end_time=None) -> Dict[str, Any]:
        """取得資料庫圖表資料"""
        if not self.database_available:
            return {
                'success': False,
                'message': '資料庫功能未啟用',
                'data': []
            }
        
        try:
            # 構建查詢參數
            query_params = {
                'limit': limit,
                'data_type': data_type
            }
            
            if factory_area:
                query_params['factory_area'] = factory_area
            if floor_level:
                query_params['floor_level'] = floor_level
            if mac_id:
                query_params['mac_id'] = mac_id
            if device_model:
                query_params['device_model'] = device_model
            if start_time:
                query_params['start_time'] = start_time
            if end_time:
                query_params['end_time'] = end_time
            
            # 從資料庫獲取資料
            data = self.db_manager.get_chart_data(**query_params)
            
            return {
                'success': True,
                'data': data,
                'count': len(data),
                'query_params': query_params,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"取得資料庫圖表資料失敗: {e}")
            return {
                'success': False,
                'message': f'取得圖表資料失敗: {str(e)}',
                'data': []
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """取得資料庫統計資訊"""
        if not self.database_available:
            return {
                'success': False,
                'message': '資料庫功能未啟用',
                'data': {}
            }
        
        try:
            stats = self.db_manager.get_statistics()
            return {
                'success': True,
                'data': stats,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"取得資料庫統計失敗: {e}")
            return {
                'success': False,
                'message': f'取得統計資訊失敗: {str(e)}',
                'data': {}
            }
    
    def get_latest_data(self, limit: int = 100) -> Dict[str, Any]:
        """取得最新資料"""
        if not self.database_available:
            return {
                'success': False,
                'message': '資料庫功能未啟用',
                'data': []
            }
        
        try:
            data = self.db_manager.get_latest_data(limit=limit)
            return {
                'success': True,
                'data': data,
                'count': len(data),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"取得最新資料失敗: {e}")
            return {
                'success': False,
                'message': f'取得最新資料失敗: {str(e)}',
                'data': []
            }
    
    def get_factory_areas(self) -> Dict[str, Any]:
        """取得廠區列表"""
        if not self.database_available:
            return {
                'success': False,
                'message': '資料庫功能未啟用',
                'data': []
            }
        
        try:
            areas = self.db_manager.get_factory_areas()
            return {
                'success': True,
                'data': areas,
                'count': len(areas)
            }
        except Exception as e:
            self.logger.error(f"取得廠區列表失敗: {e}")
            return {
                'success': False,
                'message': f'取得廠區列表失敗: {str(e)}',
                'data': []
            }
    
    def register_device(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """註冊設備"""
        if not self.database_available:
            return {
                'success': False,
                'message': '資料庫功能未啟用'
            }
        
        try:
            result = self.db_manager.register_device(device_data)
            return {
                'success': True,
                'message': '設備註冊成功',
                'device_id': result.get('device_id')
            }
        except Exception as e:
            self.logger.error(f"註冊設備失敗: {e}")
            return {
                'success': False,
                'message': f'註冊設備失敗: {str(e)}'
            }
    
    def get_device_info(self, mac_id: Optional[str] = None) -> Dict[str, Any]:
        """取得設備資訊"""
        if not self.database_available:
            return {
                'success': False,
                'message': '資料庫功能未啟用',
                'data': []
            }
        
        try:
            device_info = self.db_manager.get_device_info(mac_id=mac_id)
            return {
                'success': True,
                'data': device_info,
                'count': len(device_info),
                'filter': {'mac_id': mac_id} if mac_id else {}
            }
        except Exception as e:
            self.logger.error(f"取得設備資訊失敗: {e}")
            return {
                'success': False,
                'message': f'取得設備資訊失敗: {str(e)}',
                'data': []
            }


class DeviceAreasModel:
    """設備區域模型"""
    
    def __init__(self):
        """初始化設備區域模型"""
        self.logger = logging.getLogger(__name__)
    
    def get_areas_statistics(self) -> Dict[str, Any]:
        """取得所有廠區、位置、設備型號統計資料"""
        try:
            from multi_device_settings import multi_device_settings_manager
            
            # 取得所有設備設定
            all_devices = multi_device_settings_manager.get_all_device_settings()
            
            areas = set()
            locations = set()
            models = set()
            
            for device_id, settings in all_devices.items():
                # 廠區
                factory_area = settings.get('factory_area')
                if factory_area and factory_area.strip():
                    areas.add(factory_area.strip())
                
                # 位置
                floor_level = settings.get('floor_level')
                if floor_level and floor_level.strip():
                    locations.add(floor_level.strip())
                
                # 設備型號
                device_model = settings.get('device_model')
                if isinstance(device_model, list):
                    for model in device_model:
                        if model and model.strip():
                            models.add(model.strip())
                elif isinstance(device_model, str) and device_model.strip():
                    models.add(device_model.strip())
            
            return {
                'success': True,
                'areas': sorted(list(areas)),
                'locations': sorted(list(locations)),
                'models': sorted(list(models)),
                'device_count': len(all_devices),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"獲取廠區統計資料時發生錯誤: {e}")
            return {
                'success': False,
                'message': f'獲取廠區統計資料失敗: {str(e)}',
                'areas': [],
                'locations': [],
                'models': []
            }


class UartDataModel:
    """UART 資料模型"""
    
    def __init__(self, uart_reader=None):
        """初始化 UART 資料模型"""
        self.uart_reader = uart_reader
        self.logger = logging.getLogger(__name__)
    
    def get_status(self) -> Dict[str, Any]:
        """取得 UART 狀態"""
        try:
            if not self.uart_reader:
                return {
                    'success': False,
                    'message': 'UART Reader 未初始化',
                    'status': 'not_available'
                }
            
            return {
                'success': True,
                'status': 'running' if self.uart_reader.is_running else 'stopped',
                'is_running': self.uart_reader.is_running,
                'data_count': len(self.uart_reader.get_latest_data()) if self.uart_reader.get_latest_data() else 0,
                'last_update': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"取得 UART 狀態失敗: {e}")
            return {
                'success': False,
                'message': f'取得 UART 狀態失敗: {str(e)}',
                'status': 'error'
            }
    
    def get_mac_ids(self) -> Dict[str, Any]:
        """取得 MAC ID 列表"""
        try:
            if not self.uart_reader:
                return {
                    'success': False,
                    'message': 'UART Reader 未初始化',
                    'mac_ids': []
                }
            
            # 首先嘗試從即時數據獲取
            data = self.uart_reader.get_latest_data()
            mac_ids = set()
            
            if data:
                # UART 數據格式: [{'timestamp': '...', 'mac_id': '...', 'channel': 0, 'parameter': 61.45, 'unit': 'A'}, ...]
                for entry in data:
                    mac_id = entry.get('mac_id')
                    if mac_id and mac_id.strip() and mac_id not in ['N/A', '', 'None']:
                        mac_ids.add(mac_id)
            
            # 如果即時數據沒有足夠的 MAC ID，嘗試載入歷史數據
            if len(mac_ids) == 0:
                self.logger.info("即時數據中沒有 MAC ID，嘗試載入歷史數據")
                if hasattr(self.uart_reader, 'load_historical_data'):
                    self.uart_reader.load_historical_data(days_back=7)
                    data = self.uart_reader.get_latest_data()
                    
                    for entry in data:
                        mac_id = entry.get('mac_id')
                        if mac_id and mac_id.strip() and mac_id not in ['N/A', '', 'None']:
                            mac_ids.add(mac_id)
            
            unique_mac_ids = sorted(list(mac_ids))
            data_source = '歷史文件' if len(mac_ids) > 0 and len(self.uart_reader.get_latest_data()) > len(data) else 'UART即時數據'
            
            return {
                'success': True,
                'mac_ids': unique_mac_ids,
                'count': len(unique_mac_ids),
                'data_source': data_source,
                'total_entries': len(data) if data else 0
            }
        except Exception as e:
            self.logger.error(f"取得 MAC ID 列表失敗: {e}")
            return {
                'success': False,
                'message': f'取得 MAC ID 列表失敗: {str(e)}',
                'mac_ids': []
            }
    
    def get_mac_channels(self, mac_id: Optional[str] = None) -> Dict[str, Any]:
        """取得指定 MAC ID 的通道資訊，或所有 MAC ID 的通道統計"""
        try:
            if not self.uart_reader:
                return {
                    'success': False,
                    'message': 'UART Reader 未初始化',
                    'data': {}
                }
            
            data = self.uart_reader.get_latest_data()
            
            if mac_id:
                # 取得特定 MAC ID 的通道資訊
                channels = {}
                for entry in data:
                    if entry.get('mac_id') == mac_id:
                        for channel_data in entry.get('channels', []):
                            channel_num = channel_data.get('channel')
                            if channel_num is not None:
                                if channel_num not in channels:
                                    channels[channel_num] = []
                                channels[channel_num].append(channel_data)
                
                return {
                    'success': True,
                    'mac_id': mac_id,
                    'channels': channels,
                    'channel_count': len(channels)
                }
            else:
                # 取得所有 MAC ID 的通道統計
                mac_stats = {}
                for entry in data:
                    entry_mac_id = entry.get('mac_id')
                    if entry_mac_id:
                        if entry_mac_id not in mac_stats:
                            mac_stats[entry_mac_id] = {'channels': set(), 'data_count': 0}
                        
                        mac_stats[entry_mac_id]['data_count'] += 1
                        for channel_data in entry.get('channels', []):
                            channel_num = channel_data.get('channel')
                            if channel_num is not None:
                                mac_stats[entry_mac_id]['channels'].add(channel_num)
                
                # 轉換 set 為 list
                for mac_id, stats in mac_stats.items():
                    stats['channels'] = sorted(list(stats['channels']))
                    stats['channel_count'] = len(stats['channels'])
                
                return {
                    'success': True,
                    'data': mac_stats,
                    'mac_count': len(mac_stats)
                }
                
        except Exception as e:
            self.logger.error(f"取得 MAC 通道資訊失敗: {e}")
            return {
                'success': False,
                'message': f'取得 MAC 通道資訊失敗: {str(e)}',
                'data': {}
            }
    
    def get_mac_data_recent(self, mac_id: str, minutes: int = 10) -> Dict[str, Any]:
        """取得特定 MAC ID 最近 N 分鐘的電流數據"""
        try:
            if not self.uart_reader:
                return {
                    'success': False,
                    'message': 'UART Reader 未初始化',
                    'data': []
                }
            
            data = self.uart_reader.get_data()
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(minutes=minutes)
            
            filtered_data = []
            for entry in data:
                if entry.get('mac_id') == mac_id:
                    timestamp_str = entry.get('timestamp')
                    if timestamp_str:
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            if timestamp >= cutoff_time:
                                filtered_data.append(entry)
                        except:
                            # 如果時間解析失敗，仍然包含這筆資料
                            filtered_data.append(entry)
            
            return {
                'success': True,
                'mac_id': mac_id,
                'minutes': minutes,
                'data': filtered_data,
                'count': len(filtered_data),
                'timestamp': current_time.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"取得 MAC 最近資料失敗: {e}")
            return {
                'success': False,
                'message': f'取得 MAC 最近資料失敗: {str(e)}',
                'data': []
            }