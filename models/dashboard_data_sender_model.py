# models/dashboard_data_sender_model.py
import time
import threading
import logging

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logging.warning("requests 模組未安裝，Dashboard 資料發送功能將被停用")


class DashboardDataSender:
    """Dashboard 資料傳送管理器"""
    
    def __init__(self):
        self.dashboard_url = "http://192.168.113.239:5000"  # 預設 Dashboard 服務地址
        self.api_endpoint = "/api/uart/receive-from-pi"
        self.enabled = REQUESTS_AVAILABLE
        self.send_interval = 10  # 每10秒檢查一次
        self.batch_size = 20  # 批量大小
        self.last_sent_index = 0  # 記錄上次發送的資料索引
        self.is_running = False
        self.send_thread = None
        self.send_queue = []
        self.total_sent = 0
        self.send_errors = 0
        
        # 從設定檔讀取 Dashboard 地址
        self.load_dashboard_config()
        
    def load_dashboard_config(self):
        """從設定檔載入 Dashboard 配置"""
        try:
            # 可以從設定檔或環境變數讀取
            from config_manager import ConfigManager
            config_manager = ConfigManager()
            if hasattr(config_manager, 'get_dashboard_config'):
                dashboard_config = config_manager.get_dashboard_config()
                if dashboard_config and 'url' in dashboard_config:
                    self.dashboard_url = dashboard_config['url']
                    logging.info(f"從設定檔讀取 Dashboard 地址: {self.dashboard_url}")
        except Exception as e:
            logging.warning(f"載入 Dashboard 設定失敗，使用預設地址: {e}")
    
    def set_dashboard_url(self, url):
        """設定 Dashboard 服務地址"""
        self.dashboard_url = url
        logging.info(f"Dashboard 服務地址已更新為: {self.dashboard_url}")
    
    def send_single_data(self, data):
        """發送單筆資料到 Dashboard"""
        if not self.enabled:
            return False, "requests 模組未安裝"
            
        try:
            url = f"{self.dashboard_url}{self.api_endpoint}"
            response = requests.post(
                url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                self.total_sent += 1
                logging.debug(f"成功發送資料到 Dashboard: MAC={data.get('mac_id')}")
                return True, "發送成功"
            else:
                self.send_errors += 1
                logging.error(f"發送資料失敗: HTTP {response.status_code}")
                return False, f"HTTP錯誤: {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            self.send_errors += 1
            logging.error(f"無法連接到 Dashboard 服務: {self.dashboard_url}")
            return False, "連接失敗"
        except requests.exceptions.Timeout:
            self.send_errors += 1
            logging.error("發送資料超時")
            return False, "發送超時"
        except Exception as e:
            self.send_errors += 1
            logging.error(f"發送資料錯誤: {e}")
            return False, str(e)
    
    def send_batch_data(self, data_list):
        """批量發送資料到 Dashboard"""
        if not self.enabled:
            return False, "requests 模組未安裝"
            
        try:
            batch_data = {'data_list': data_list}
            url = f"{self.dashboard_url}{self.api_endpoint}"
            
            response = requests.post(
                url,
                json=batch_data,
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            
            if response.status_code == 200:
                self.total_sent += len(data_list)
                logging.info(f"成功批量發送 {len(data_list)} 筆資料到 Dashboard")
                return True, f"批量發送成功: {len(data_list)} 筆"
            else:
                self.send_errors += 1
                logging.error(f"批量發送失敗: HTTP {response.status_code}")
                return False, f"HTTP錯誤: {response.status_code}"
                
        except Exception as e:
            self.send_errors += 1
            logging.error(f"批量發送錯誤: {e}")
            return False, str(e)
    
    def data_sender_worker(self, uart_reader):
        """資料發送工作執行緒"""
        logging.info("🚀 Dashboard 資料發送服務已啟動")
        
        while self.is_running:
            try:
                if not uart_reader or not uart_reader.latest_data:
                    time.sleep(self.send_interval)
                    continue
                
                # 獲取新資料
                with uart_reader.lock:
                    current_data = uart_reader.latest_data.copy()
                
                # 找出需要發送的新資料
                if len(current_data) > self.last_sent_index:
                    new_data = current_data[self.last_sent_index:]
                    
                    if len(new_data) > 0:
                        # 準備發送資料，確保格式正確
                        prepared_data = []
                        for item in new_data:
                            # 確保資料格式符合 Dashboard API 需求
                            if isinstance(item, dict) and all(key in item for key in ['mac_id', 'channel', 'parameter', 'unit']):
                                prepared_data.append(item)
                        
                        if prepared_data:
                            if len(prepared_data) == 1:
                                # 單筆資料
                                success, message = self.send_single_data(prepared_data[0])
                            else:
                                # 批量資料
                                success, message = self.send_batch_data(prepared_data)
                            
                            if success:
                                self.last_sent_index = len(current_data)
                                logging.debug(f"已發送 {len(prepared_data)} 筆資料到 Dashboard")
                            else:
                                logging.warning(f"發送資料失敗: {message}")
                
                time.sleep(self.send_interval)
                
            except Exception as e:
                logging.error(f"資料發送執行緒錯誤: {e}")
                time.sleep(self.send_interval)
        
        logging.info("📤 Dashboard 資料發送服務已停止")
    
    def start(self, uart_reader=None):
        """啟動資料發送服務"""
        if not self.enabled:
            logging.warning("無法啟動 Dashboard 資料發送服務: requests 模組未安裝")
            return False
            
        if self.is_running:
            logging.warning("Dashboard 資料發送服務已在運行中")
            return False
        
        self.is_running = True
        self.send_thread = threading.Thread(target=self.data_sender_worker, args=(uart_reader,), daemon=True)
        self.send_thread.start()
        logging.info(f"✅ Dashboard 資料發送服務已啟動，目標: {self.dashboard_url}")
        return True
    
    def stop(self):
        """停止資料發送服務"""
        if not self.is_running:
            return False
            
        self.is_running = False
        if self.send_thread:
            self.send_thread.join(timeout=5)
        logging.info("🛑 Dashboard 資料發送服務已停止")
        return True
    
    def get_status(self):
        """獲取發送狀態"""
        return {
            'enabled': self.enabled,
            'running': self.is_running,
            'dashboard_url': self.dashboard_url,
            'total_sent': self.total_sent,
            'send_errors': self.send_errors,
            'last_sent_index': self.last_sent_index,
            'send_interval': self.send_interval
        }


class DashboardDataSenderModel:
    """Dashboard 資料發送模型"""
    
    def __init__(self):
        self.sender = DashboardDataSender()
        
    def get_sender(self):
        """獲取資料發送器實例"""
        return self.sender
        
    def start_sender(self, uart_reader=None):
        """啟動資料發送服務"""
        return self.sender.start(uart_reader)
        
    def stop_sender(self):
        """停止資料發送服務"""
        return self.sender.stop()
        
    def get_sender_status(self):
        """獲取發送器狀態"""
        return self.sender.get_status()
        
    def set_dashboard_url(self, url):
        """設定 Dashboard 服務地址"""
        self.sender.set_dashboard_url(url)
        
    def send_single_data(self, data):
        """發送單筆資料"""
        return self.sender.send_single_data(data)
        
    def send_batch_data(self, data_list):
        """批量發送資料"""
        return self.sender.send_batch_data(data_list)