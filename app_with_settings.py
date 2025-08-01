"""
Flask Dashboard 應用程式 - 設備設定整合版本
包含設備設定管理功能的範例
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import os
from datetime import datetime
from device_settings import device_settings_manager

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 請更換為您的密鑰

# 首頁路由 - 重導向到設備設定或儀表板
@app.route('/')
def index():
    """首頁路由，根據設定狀態導向不同頁面"""
    if device_settings_manager.is_configured():
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('db_setting'))

# DB 設定頁面
@app.route('/db-setting')
def db_setting():
    """顯示 DB 設定頁面"""
    return render_template('db_setting.html')

# 設備設定 API
@app.route('/api/device-settings', methods=['GET', 'POST'])
def api_device_settings():
    """設備設定 API - 支援 GET 和 POST"""
    if request.method == 'GET':
        # 取得目前的設備設定
        settings = device_settings_manager.get_device_info()
        return jsonify({
            'success': True,
            'settings': settings
        })
    
    elif request.method == 'POST':
        # 儲存設備設定
        try:
            data = request.get_json()
            
            # 驗證必要欄位
            if not data.get('device_name', '').strip():
                return jsonify({
                    'success': False,  
                    'message': '設備名稱為必填欄位'
                }), 400
            
            # 限制欄位長度
            if len(data.get('device_name', '')) > 50:
                return jsonify({
                    'success': False,
                    'message': '設備名稱不能超過50個字元'
                }), 400
            
            # 儲存設定
            success = device_settings_manager.save_settings(data)
            
            if success:
                response_data = {
                    'success': True,
                    'message': '設定儲存成功'
                }
                
                # 檢查是否需要重定向到 dashboard
                redirect_to_dashboard = data.get('redirect_to_dashboard', False)
                if redirect_to_dashboard:
                    response_data['redirect_url'] = url_for('dashboard')
                
                return jsonify(response_data)
            else:
                return jsonify({
                    'success': False,
                    'message': '設定儲存失敗'
                }), 500
                
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'伺服器錯誤: {str(e)}'
            }), 500

# 儀表板頁面
@app.route('/dashboard')
def dashboard():
    """顯示儀表板頁面"""
    # 檢查是否已完成設備設定
    if not device_settings_manager.is_configured():
        return redirect(url_for('db_setting'))
    
    # 取得設備設定並傳遞給模板
    device_settings = device_settings_manager.get_device_info()
    
    # 模擬應用程式狀態資料（請根據實際狀況修改）
    app_stats = {
        'uart_running': False,
        'uart_data_count': 0,
        'current_mode': 'idle',
        'supported_protocols': ['UART', 'TCP', 'HTTP']
    }
    
    return render_template('dashboard.html', 
                         device_settings=device_settings,
                         app_stats=app_stats)

# 儀表板統計資料 API
@app.route('/api/dashboard/stats')
def api_dashboard_stats():
    """儀表板統計資料 API"""
    # 這裡應該從實際的系統中取得資料
    # 以下為範例資料
    stats = {
        'success': True,
        'application': {
            'uart_running': False,
            'uart_data_count': 0,
            'active_protocol': 'UART',
            'offline_mode': False
        }
    }
    return jsonify(stats)

# UART 狀態 API
@app.route('/api/uart/status')
def api_uart_status():
    """UART 狀態 API"""
    # 這裡應該從實際的 UART 系統中取得狀態
    # 以下為範例資料
    status = {
        'success': True,
        'is_running': False,
        'data_count': 0
    }
    return jsonify(status)

# UART MAC ID 列表 API
@app.route('/api/uart/mac-ids')
def api_uart_mac_ids():
    """UART MAC ID 列表 API"""
    # 這裡應該從實際的 UART 系統中取得 MAC ID 列表
    # 以下為範例資料
    mac_ids = [
        "AA:BB:CC:DD:EE:FF",
        "11:22:33:44:55:66", 
        "TEST-MAC-001",
        "DEMO-MAC-002"
    ]
    
    return jsonify({
        'success': True,
        'mac_ids': mac_ids,
        'message': f'已載入 {len(mac_ids)} 個 MAC ID'
    })

# 圖表數據 API
@app.route('/api/dashboard/chart-data')
def api_chart_data():
    """圖表數據 API"""
    limit = request.args.get('limit', 100, type=int)
    channel = request.args.get('channel', 'all')
    
    # 這裡應該從實際的資料庫中取得圖表資料
    # 以下為範例資料
    sample_data = []
    
    # 模擬一些測試資料
    from datetime import datetime, timedelta
    now = datetime.now()
    
    for i in range(min(limit, 50)):  # 最多50個測試點
        timestamp = now - timedelta(seconds=i*10)
        
        # 如果指定了特定通道
        if channel != 'all' and channel.isdigit():
            channel_num = int(channel)
            unit = 'A' if channel_num <= 6 else 'V'
            value = 1.0 + (i % 10) * 0.1 if unit == 'A' else 3.3 + (i % 5) * 0.01
            
            sample_data.append({
                'channel': channel_num,
                'unit': unit,
                'data': [{
                    'timestamp': timestamp.isoformat(),
                    'parameter': value
                }]
            })
        else:
            # 所有通道的資料
            for ch in range(8):  # 0-7 通道
                unit = 'A' if ch <= 6 else 'V'
                value = 1.0 + (i % 10) * 0.1 if unit == 'A' else 3.3 + (i % 5) * 0.01
                
                sample_data.append({
                    'channel': ch,
                    'unit': unit,
                    'data': [{
                        'timestamp': timestamp.isoformat(),
                        'parameter': value + ch * 0.1
                    }]
                })
    
    return jsonify({
        'success': True,
        'data': sample_data
    })

# 錯誤處理
@app.errorhandler(404)
def not_found(error):
    """404 錯誤處理"""
    return render_template('error.html', 
                         error_code=404,
                         error_message='頁面不存在'), 404

@app.errorhandler(500)
def server_error(error):
    """500 錯誤處理"""
    return render_template('error.html',
                         error_code=500,
                         error_message='伺服器內部錯誤'), 500

# 應用程式啟動前檢查
def setup_application():
    """應用程式啟動前的設定檢查"""
    print("=== Flask Dashboard 啟動 ===")
    
    if device_settings_manager.is_configured():
        device_info = device_settings_manager.get_device_info()
        print(f"設備名稱: {device_info.get('device_name', '未設定')}")
        print(f"設備位置: {device_info.get('device_location', '未設定')}")
    else:
        print("警告: 尚未完成設備設定")
        print("請先訪問 http://localhost:5000/db-setting 進行設定")
    
    print("應用程式已準備就緒")

if __name__ == '__main__':
    # 開發模式啟動
    print("正在啟動 Flask Dashboard...")
    print("請在瀏覽器中訪問: http://localhost:5000")
    
    # 在應用程式啟動前執行設定檢查
    setup_application()
    
    app.run(
        host='0.0.0.0',  # 允許外部訪問
        port=5000,       # 預設埠號
        debug=True       # 開發模式
    )
