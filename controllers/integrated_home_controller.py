# controllers/integrated_home_controller.py
from flask import Blueprint, render_template, request, make_response
import logging

# 創建 Blueprint
integrated_home_bp = Blueprint('integrated_home', __name__)


@integrated_home_bp.route('/')
def home():
    """主頁面"""
    logging.info(f'訪問首頁, remote_addr={request.remote_addr}')
    
    # 這裡需要從外部傳入 uart_reader 實例
    from uart_integrated import uart_reader
    
    # 獲取UART資料
    uart_data = uart_reader.get_latest_data()
    com_port = uart_reader.get_uart_config()[0]
    uart_status = {
        'is_running': uart_reader.is_running,
        'data_count': uart_reader.get_data_count(),
        'latest_data': list(reversed(uart_data[-10:])) if uart_data else [],  # 只顯示最新10筆，最新在最上方
        'com_port': com_port
    }
    
    response = render_template('home.html', uart_status=uart_status)
    
    # 設定防止快取的 HTTP 標頭
    response = make_response(response)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response


@integrated_home_bp.route('/test-mac-id')
def test_mac_id():
    """MAC ID 測試頁面"""
    return render_template('mac_id_test.html')


@integrated_home_bp.route('/config-summary')
def config_summary():
    """配置摘要頁面"""
    logging.info(f'訪問配置摘要頁面, remote_addr={request.remote_addr}')
    return render_template('config_summary.html')


@integrated_home_bp.route('/11')
def page_11():
    """11 頁面"""
    return render_template('11.html')


@integrated_home_bp.route('/application/<protocol>')
def application_page(protocol):
    """應用程式頁面"""
    # 檢查協議是否支持
    supported_protocols = ['FTP', 'SFTP', 'Samba', 'TCP', 'UDP', 'MQTT']
    if protocol.upper() not in supported_protocols:
        return render_template('error.html', 
                             error_message=f'不支援的協議: {protocol}'), 404
    
    # 動態載入協議配置模組
    try:
        from multi_protocol_manager import multi_protocol_manager
        protocol_config = multi_protocol_manager.get_protocol_config(protocol.upper())
        
        return render_template('application.html', 
                             protocol=protocol.upper(),
                             config=protocol_config)
    except Exception as e:
        logging.error(f"載入協議 {protocol} 配置失敗: {e}")
        return render_template('error.html', 
                             error_message=f'載入協議配置失敗: {str(e)}'), 500