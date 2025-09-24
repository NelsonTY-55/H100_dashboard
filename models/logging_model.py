"""
日誌管理模型
處理應用程式日誌記錄和管理
"""

import os
import platform
import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler


class DailyLogHandler(TimedRotatingFileHandler):
    """自訂的日誌處理器，支援按日期自動切換"""
    
    def __init__(self, log_dir):
        # 建立日誌目錄
        os.makedirs(log_dir, exist_ok=True)
        
        # 初始日誌檔案名稱
        log_filename = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log")
        super().__init__(log_filename, when='midnight', interval=1, backupCount=30, encoding='utf-8')
        self.log_dir = log_dir
        self.suffix = "%Y%m%d"
        
    def rotation_filename(self, default_name):
        """自訂輪換後的檔案名稱格式"""
        timestamp = datetime.now().strftime('%Y%m%d')
        return os.path.join(self.log_dir, f"app_{timestamp}.log")


class LoggingModel:
    """日誌管理模型"""
    
    def __init__(self, log_dir=None):
        # 如果沒有指定日誌目錄，則根據平台自動選擇
        if log_dir is None:
            if platform.system() == 'Windows':
                # Windows 系統使用當前目錄下的 logs 資料夾
                self.log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
            else:
                # Linux/Pi 系統使用樹莓派專用路徑
                self.log_dir = "/home/pi/my_fastapi_app/logs"
        else:
            self.log_dir = log_dir
            
        self.daily_handler = None
        self.setup_logging()
    
    def setup_logging(self):
        """設定日誌系統"""
        try:
            # 建立自動切換日誌處理器
            self.daily_handler = DailyLogHandler(self.log_dir)
            self.daily_handler.setLevel(logging.INFO)
            self.daily_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
            
            # 設定基本日誌配置
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s [%(levelname)s] %(message)s',
                handlers=[
                    self.daily_handler,
                    logging.StreamHandler()
                ]
            )
            
            logging.info("日誌系統初始化完成")
            
        except Exception as e:
            print(f"設定日誌系統時發生錯誤: {e}")
    
    def get_log_files(self):
        """獲取所有日誌檔案"""
        try:
            if not os.path.exists(self.log_dir):
                return []
            
            log_files = []
            for filename in os.listdir(self.log_dir):
                if filename.startswith('app_') and filename.endswith('.log'):
                    filepath = os.path.join(self.log_dir, filename)
                    stat = os.stat(filepath)
                    log_files.append({
                        'filename': filename,
                        'filepath': filepath,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'date': filename.replace('app_', '').replace('.log', '')
                    })
            
            # 按修改時間排序
            log_files.sort(key=lambda x: x['modified'], reverse=True)
            return log_files
            
        except Exception as e:
            logging.error(f"獲取日誌檔案列表時發生錯誤: {e}")
            return []
    
    def read_log_file(self, filename, lines=100):
        """讀取指定日誌檔案的內容"""
        try:
            filepath = os.path.join(self.log_dir, filename)
            if not os.path.exists(filepath):
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
            
            # 返回最後 N 行
            if lines and len(all_lines) > lines:
                return all_lines[-lines:]
            
            return all_lines
            
        except Exception as e:
            logging.error(f"讀取日誌檔案 {filename} 時發生錯誤: {e}")
            return None
    
    def get_log_stats(self):
        """獲取日誌統計資訊"""
        try:
            log_files = self.get_log_files()
            
            total_size = sum(f['size'] for f in log_files)
            total_files = len(log_files)
            
            # 獲取今天的日誌檔案
            today_date = datetime.now().strftime('%Y%m%d')
            today_log = next((f for f in log_files if f['date'] == today_date), None)
            
            return {
                'total_files': total_files,
                'total_size': total_size,
                'total_size_mb': round(total_size / 1024 / 1024, 2),
                'today_log_size': today_log['size'] if today_log else 0,
                'oldest_log': log_files[-1] if log_files else None,
                'newest_log': log_files[0] if log_files else None,
                'log_directory': self.log_dir
            }
            
        except Exception as e:
            logging.error(f"獲取日誌統計時發生錯誤: {e}")
            return {
                'total_files': 0,
                'total_size': 0,
                'total_size_mb': 0,
                'today_log_size': 0,
                'oldest_log': None,
                'newest_log': None,
                'log_directory': self.log_dir
            }