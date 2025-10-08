"""
主程式 - 同時執行 app_integrated_mvc.py 和 dashboard.py
"""

import os
import signal
import subprocess
import sys
import threading
import time

from datetime import datetime

class ServiceManager:
    def __init__(self):
        self.processes = {}
        self.running = True
        
    def start_service(self, name, script_path, port):
        """啟動服務"""
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在啟動 {name} 服務...")
            
            # 設定環境變數
            env = os.environ.copy()
            env['PYTHONPATH'] = os.getcwd()
            env['PYTHONIOENCODING'] = 'utf-8'  # 確保 Python 子程序使用 UTF-8 編碼
            env['PYTHONUNBUFFERED'] = '1'  # 確保輸出不被緩衝
            
            # 啟動 Python 腳本
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace',  # 遇到編碼錯誤時替換為佔位符而不是崩潰
            )
            
            self.processes[name] = {
                'process': process,
                'script': script_path,
                'port': port,
                'start_time': datetime.now()
            }
            
            # 啟動輸出監控執行緒
            threading.Thread(
                target=self.monitor_output, 
                args=(name, process), 
                daemon=True
            ).start()
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {name} 服務已啟動 (PID: {process.pid}, Port: {port})")
            return True
            
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 啟動 {name} 服務失敗: {e}")
            return False
    
    def monitor_output(self, service_name, process):
        """監控服務輸出"""
        try:
            # 監控標準輸出
            def monitor_stdout():
                for line in iter(process.stdout.readline, ''):
                    if self.running and line.strip():
                        try:
                            # 確保線內容是可顯示的
                            line_content = line.strip().encode('utf-8', 'replace').decode('utf-8')
                            print(f"[{service_name}] {line_content}")
                        except Exception as e:
                            # 如果還是有編碼問題，使用 repr
                            print(f"[{service_name}] {repr(line.strip())}")
                            print(f"[{service_name}][ERROR] 輸出編碼錯誤: {e}")
            
            # 監控錯誤輸出
            def monitor_stderr():
                for line in iter(process.stderr.readline, ''):
                    if self.running and line.strip():
                        # 檢查是否是實際錯誤還是普通日誌
                        line_content = line.strip()
                        try:
                            # 確保線內容是可顯示的
                            line_content = line_content.encode('utf-8', 'replace').decode('utf-8')
                        except Exception:
                            line_content = repr(line_content)  # 如果編碼還是有問題，使用 repr
                            
                        if any(level in line_content for level in ['[ERROR]', '[CRITICAL]', 'Traceback', 'Exception', 'Error:']):
                            print(f"[{service_name}][ERROR] {line_content}")
                        elif any(level in line_content for level in ['[INFO]', '[DEBUG]', '[WARNING]']):
                            print(f"[{service_name}] {line_content}")
                        else:
                            print(f"[{service_name}][LOG] {line_content}")
            
            # 啟動兩個監控執行緒
            threading.Thread(target=monitor_stdout, daemon=True).start()
            threading.Thread(target=monitor_stderr, daemon=True).start()
            
        except Exception as e:
            if self.running:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {service_name} 輸出監控錯誤: {e}")
    
    def check_services(self):
        """檢查服務狀態"""
        for name, info in self.processes.items():
            process = info['process']
            if process.poll() is not None:
                exit_code = process.poll()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 警告: {name} 服務已停止 (返回碼: {exit_code})")
                
                # 顯示錯誤輸出（如果有的話）
                try:
                    # 嘗試讀取剩餘的輸出
                    stdout_output = process.stdout.read() if process.stdout else ""
                    stderr_output = process.stderr.read() if process.stderr else ""
                    
                    if stdout_output:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] {name} 標準輸出: {stdout_output}")
                    if stderr_output:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] {name} 錯誤輸出: {stderr_output}")
                except Exception as read_error:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 讀取 {name} 輸出時發生錯誤: {read_error}")
                
                # 可以在這裡添加重啟邏輯
    
    def stop_all_services(self):
        """停止所有服務"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 正在停止所有服務...")
        self.running = False
        
        for name, info in self.processes.items():
            try:
                process = info['process']
                if process.poll() is None:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 停止 {name} 服務...")
                    process.terminate()
                    
                    # 等待程序正常結束，如果超時則強制終止
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 強制終止 {name} 服務...")
                        process.kill()
                        process.wait()
                    
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] {name} 服務已停止")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 停止 {name} 服務時發生錯誤: {e}")
    
    def show_status(self):
        """顯示服務狀態"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 服務狀態:")
        print("-" * 60)
        
        for name, info in self.processes.items():
            process = info['process']
            status = "運行中" if process.poll() is None else f"已停止 (返回碼: {process.poll()})"
            uptime = datetime.now() - info['start_time']
            
            print(f"服務名稱: {name}")
            print(f"  狀態: {status}")
            print(f"  PID: {process.pid}")
            print(f"  端口: {info['port']}")
            print(f"  運行時間: {uptime}")
            print(f"  腳本路徑: {info['script']}")
            print()

def signal_handler(signum, frame):
    """處理系統信號"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 收到信號 {signum}，正在關閉服務...")
    if 'service_manager' in globals():
        service_manager.stop_all_services()
    sys.exit(0)

def main():
    global service_manager
    
    print("="*60)
    print("H100 Dashboard 多服務管理器")
    print("="*60)
    print(f"啟動時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 註冊信號處理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 創建服務管理器
    service_manager = ServiceManager()
    
    # 檢查腳本文件是否存在
    scripts = [
        ("主應用服務", "app_integrated_mvc.py", 5000),
        ("Dashboard API", "dashboard.py", 5001)
    ]
    
    for name, script, port in scripts:
        if not os.path.exists(script):
            print(f"錯誤: 找不到 {script} 文件")
            return 1
    
    # 啟動所有服務
    success_count = 0
    for name, script, port in scripts:
        if service_manager.start_service(name, script, port):
            success_count += 1
        time.sleep(3)  # 給每個服務更多啟動時間
    
    if success_count == 0:
        print("錯誤: 沒有成功啟動任何服務")
        return 1
    
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 已啟動 {success_count}/{len(scripts)} 個服務")
    
    # 等待服務完全啟動
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 等待服務完全啟動...")
    time.sleep(5)
    
    # 檢查端口是否開放
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 檢查服務端口...")
    import socket
    for name, script, port in scripts:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            if result == 0:
                print(f"  ✓ {name} (端口 {port}): 可連接")
            else:
                print(f"  ✗ {name} (端口 {port}): 無法連接")
        except Exception as e:
            print(f"  ✗ {name} (端口 {port}): 檢查失敗 - {e}")
    
    print("\n服務訪問地址:")
    print("  - 主應用: http://localhost:5000")
    print("  - Dashboard: http://localhost:5001/dashboard")
    print("  - 設備設定: http://localhost:5001/db-setting")
    print("  - API 健康檢查: http://localhost:5001/api/health")
    
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 服務監控中... (按 Ctrl+C 停止)")
    
    try:
        # 主循環 - 監控服務狀態
        while service_manager.running:
            time.sleep(10)  # 每10秒檢查一次
            service_manager.check_services()
            
    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 收到停止信號...")
    except Exception as e:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 監控過程中發生錯誤: {e}")
    finally:
        service_manager.stop_all_services()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 所有服務已停止")
    
    return 0

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"主程式執行錯誤: {e}")
        sys.exit(1)
