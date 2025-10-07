#!/usr/bin/env python3
"""
修復 charset_normalizer 循環導入問題的腳本
"""

import subprocess
import sys
import importlib
import os

def fix_charset_normalizer():
    """修復 charset_normalizer 問題"""
    print("開始修復 charset_normalizer 問題...")
    
    try:
        # 嘗試導入 charset_normalizer
        import charset_normalizer
        print(f"當前 charset_normalizer 版本: {charset_normalizer.__version__}")
        print("測試模組是否正常工作...")
        
        # 測試基本功能
        test_str = "測試字串"
        result = charset_normalizer.from_bytes(test_str.encode('utf-8'))
        print("charset_normalizer 基本功能測試通過")
        return True
        
    except ImportError as e:
        print(f"charset_normalizer 未安裝: {e}")
        print("正在安裝 charset_normalizer...")
        
    except Exception as e:
        print(f"charset_normalizer 錯誤: {e}")
        print("正在重新安裝 charset_normalizer...")
    
    # 重新安裝 charset_normalizer
    try:
        # 先卸載
        print("卸載現有的 charset_normalizer...")
        subprocess.run([sys.executable, "-m", "pip", "uninstall", "charset-normalizer", "-y"], 
                      check=False, capture_output=True)
        
        # 清理快取
        print("清理 Python 快取...")
        import shutil
        cache_dirs = [
            "__pycache__",
            ".pytest_cache"
        ]
        
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
                print(f"清理快取目錄: {cache_dir}")
        
        # 重新安裝最新版本
        print("安裝最新版本的 charset_normalizer...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", "charset-normalizer==3.3.2"], 
                               check=True, capture_output=True, text=True)
        
        print("安裝完成，驗證安裝...")
        
        # 重新載入模組
        if 'charset_normalizer' in sys.modules:
            importlib.reload(sys.modules['charset_normalizer'])
        
        # 驗證安裝
        import charset_normalizer
        print(f"新版本 charset_normalizer: {charset_normalizer.__version__}")
        
        # 測試基本功能
        test_str = "測試字串"
        result = charset_normalizer.from_bytes(test_str.encode('utf-8'))
        print("charset_normalizer 修復成功！")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"安裝失敗: {e}")
        print(f"錯誤輸出: {e.stderr if e.stderr else '無'}")
        return False
        
    except Exception as e:
        print(f"修復過程中發生錯誤: {e}")
        return False

def fix_flask_monitoringdashboard():
    """修復 Flask MonitoringDashboard 問題"""
    print("\n檢查 Flask MonitoringDashboard...")
    
    try:
        import flask_monitoringdashboard
        print(f"Flask MonitoringDashboard 版本: {flask_monitoringdashboard.__version__}")
        return True
        
    except ImportError:
        print("Flask MonitoringDashboard 未安裝，正在安裝...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "flask-monitoringdashboard"], 
                          check=True, capture_output=True, text=True)
            print("Flask MonitoringDashboard 安裝成功")
            return True
        except Exception as e:
            print(f"Flask MonitoringDashboard 安裝失敗: {e}")
            return False
            
    except Exception as e:
        print(f"Flask MonitoringDashboard 錯誤: {e}")
        return False

def main():
    """主函數"""
    print("=" * 50)
    print("依賴套件修復工具")
    print("=" * 50)
    
    # 修復 charset_normalizer
    charset_ok = fix_charset_normalizer()
    
    # 修復 Flask MonitoringDashboard
    dashboard_ok = fix_flask_monitoringdashboard()
    
    print("\n" + "=" * 50)
    print("修復結果:")
    print(f"charset_normalizer: {'✓ 正常' if charset_ok else '✗ 失敗'}")
    print(f"flask_monitoringdashboard: {'✓ 正常' if dashboard_ok else '✗ 失敗'}")
    print("=" * 50)
    
    if charset_ok:
        print("\n✓ 修復完成！現在可以重新啟動應用程式。")
    else:
        print("\n✗ 修復失敗，請檢查錯誤訊息並手動處理。")
        print("建議手動執行:")
        print("pip uninstall charset-normalizer -y")
        print("pip install charset-normalizer==3.3.2")

if __name__ == "__main__":
    main()
