"""
UART 資料模型
處理 UART 數據讀取和管理
"""

import os
import csv
import glob
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional


class UartDataModel:
    """UART 資料模型"""
    
    def __init__(self):
        self.current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.history_dir = os.path.join(self.current_dir, 'History')
    
    def safe_get_uart_data(self, uart_reader=None):
        """安全地獲取UART數據"""
        try:
            if uart_reader and hasattr(uart_reader, 'get_latest_data'):
                return uart_reader.get_latest_data()
            return []
        except Exception as e:
            logging.warning(f"獲取UART數據時發生錯誤: {e}")
            return []
    
    def get_uart_data_from_files(self, mac_id: Optional[str] = None, limit: int = 10000) -> Dict[str, Any]:
        """從History資料夾的CSV文件中讀取UART數據"""
        try:
            if not os.path.exists(self.history_dir):
                return {
                    'success': False,
                    'error': 'History資料夾不存在',
                    'data': []
                }
            
            # 尋找所有的uart_data_*.csv文件
            csv_pattern = os.path.join(self.history_dir, 'uart_data_*.csv')
            csv_files = glob.glob(csv_pattern)
            
            if not csv_files:
                return {
                    'success': False,
                    'error': '沒有找到UART數據文件',
                    'data': []
                }
            
            # 按檔案名稱排序，最新的在最後
            csv_files.sort()
            
            all_data = []
            total_count = 0
            
            # 讀取最近的文件數據（優先讀取今天的文件，確保獲取最新數據）
            today_file = f"uart_data_{datetime.now().strftime('%Y%m%d')}.csv"
            priority_files = []
            
            # 檢查今天的文件是否存在
            today_path = os.path.join(self.history_dir, today_file)
            if os.path.exists(today_path):
                priority_files.append(today_path)
            
            # 加入其他文件（倒序，最新的先讀）
            for file_path in reversed(csv_files):
                if file_path not in priority_files:
                    priority_files.append(file_path)
            
            # 讀取文件數據
            for file_path in priority_files:
                if total_count >= limit:
                    break
                
                try:
                    file_data = self._read_csv_file(file_path, mac_id, limit - total_count)
                    all_data.extend(file_data)
                    total_count = len(all_data)
                    
                except Exception as e:
                    logging.warning(f"讀取文件 {file_path} 時發生錯誤: {e}")
                    continue
            
            # 按時間戳排序（最新的在前）
            all_data.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # 限制返回數量
            if len(all_data) > limit:
                all_data = all_data[:limit]
            
            return {
                'success': True,
                'data': all_data,
                'total_count': len(all_data),
                'files_read': len(priority_files),
                'mac_filter': mac_id
            }
            
        except Exception as e:
            logging.error(f"讀取UART數據時發生錯誤: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': []
            }
    
    def _read_csv_file(self, file_path: str, mac_id: Optional[str] = None, limit: int = 10000) -> List[Dict[str, Any]]:
        """讀取單個CSV文件"""
        data = []
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as csvfile:
            # 嘗試自動偵測CSV格式
            sample = csvfile.read(1024)
            csvfile.seek(0)
            
            # 檢測分隔符
            sniffer = csv.Sniffer()
            try:
                delimiter = sniffer.sniff(sample).delimiter
            except:
                delimiter = ','
            
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            
            for row_count, row in enumerate(reader):
                if len(data) >= limit:
                    break
                
                try:
                    # 如果指定了MAC ID，進行過濾
                    if mac_id and row.get('mac_id') != mac_id:
                        continue
                    
                    # 清理和標準化數據
                    cleaned_row = self._clean_csv_row(row)
                    if cleaned_row:
                        data.append(cleaned_row)
                        
                except Exception as e:
                    logging.debug(f"處理CSV行時發生錯誤 (行 {row_count}): {e}")
                    continue
        
        return data
    
    def _clean_csv_row(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """清理和標準化CSV行數據"""
        try:
            cleaned = {}
            
            # 標準化字段名稱
            field_mapping = {
                'timestamp': ['timestamp', 'time', 'datetime'],
                'mac_id': ['mac_id', 'mac', 'device_id'],
                'data': ['data', 'payload', 'message'],
                'channel': ['channel', 'ch', 'channel_num'],
                'rssi': ['rssi', 'signal_strength'],
                'temperature': ['temperature', 'temp'],
                'humidity': ['humidity', 'hum']
            }
            
            # 映射字段
            for standard_field, possible_fields in field_mapping.items():
                for field in possible_fields:
                    if field in row and row[field]:
                        cleaned[standard_field] = row[field].strip()
                        break
            
            # 確保必要字段存在
            if 'timestamp' not in cleaned:
                cleaned['timestamp'] = datetime.now().isoformat()
            
            # 轉換數據類型
            if 'channel' in cleaned:
                try:
                    cleaned['channel'] = int(cleaned['channel'])
                except (ValueError, TypeError):
                    pass
            
            if 'rssi' in cleaned:
                try:
                    cleaned['rssi'] = float(cleaned['rssi'])
                except (ValueError, TypeError):
                    pass
            
            if 'temperature' in cleaned:
                try:
                    cleaned['temperature'] = float(cleaned['temperature'])
                except (ValueError, TypeError):
                    pass
            
            if 'humidity' in cleaned:
                try:
                    cleaned['humidity'] = float(cleaned['humidity'])
                except (ValueError, TypeError):
                    pass
            
            return cleaned
            
        except Exception as e:
            logging.debug(f"清理CSV行數據時發生錯誤: {e}")
            return None
    
    def get_mac_ids(self) -> List[str]:
        """獲取所有可用的MAC ID"""
        try:
            data_result = self.get_uart_data_from_files(limit=50000)
            if not data_result['success']:
                return []
            
            mac_ids = set()
            for record in data_result['data']:
                if 'mac_id' in record and record['mac_id']:
                    mac_ids.add(record['mac_id'])
            
            return sorted(list(mac_ids))
            
        except Exception as e:
            logging.error(f"獲取MAC ID列表時發生錯誤: {e}")
            return []
    
    def get_mac_channels(self, mac_id: str) -> List[int]:
        """獲取指定MAC ID的所有通道"""
        try:
            data_result = self.get_uart_data_from_files(mac_id=mac_id, limit=10000)
            if not data_result['success']:
                return []
            
            channels = set()
            for record in data_result['data']:
                if 'channel' in record and isinstance(record['channel'], int):
                    channels.add(record['channel'])
            
            return sorted(list(channels))
            
        except Exception as e:
            logging.error(f"獲取MAC通道列表時發生錯誤: {e}")
            return []