# controllers/integrated_protocol_controller.py
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
import logging

# 創建 Blueprint
integrated_protocol_bp = Blueprint('integrated_protocol', __name__)


@integrated_protocol_bp.route('/protocol-config/<protocol>')
def protocol_config(protocol):
    """特定協定的設定頁面"""
    logging.info(f'訪問協定設定頁面: {protocol}, remote_addr={request.remote_addr}')
    
    from config_manager import config_manager
    
    if not config_manager.validate_protocol(protocol):
        flash('不支援的協定', 'error')
        return redirect(url_for('integrated_home.home'))
    
    # 獲取當前設定
    current_config = config_manager.get_protocol_config(protocol)
    field_info = config_manager.get_protocol_field_info(protocol)
    description = config_manager.get_protocol_description(protocol)
    
    return render_template('protocol_config.html',
                         protocol=protocol,
                         current_config=current_config,
                         field_info=field_info,
                         description=description)


@integrated_protocol_bp.route('/save-protocol-config/<protocol>', methods=['POST'])
def save_protocol_config(protocol):
    """儲存協定設定"""
    logging.info(f'儲存協定設定: {protocol}, 表單資料: {request.form.to_dict()}, remote_addr={request.remote_addr}')
    print('收到儲存請求:', protocol)
    print('表單資料:', request.form.to_dict())
    
    from config_manager import config_manager
    
    if not config_manager.validate_protocol(protocol):
        return jsonify({'success': False, 'message': '不支援的協定'})
    
    try:
        # 檢查是否為離線模式
        offline_mode = config_manager.get('offline_mode', False)
        
        # 獲取表單資料
        form_data = request.form.to_dict()
        
        # 處理數值型欄位
        field_info = config_manager.get_protocol_field_info(protocol)
        processed_config = {}
        
        for field, value in form_data.items():
            if field in field_info:
                field_config = field_info[field]
                
                # 根據欄位類型處理值
                if field_config['type'] == 'number':
                    if value:
                        try:
                            # 先嘗試轉換為浮點數，如果是整數則轉為int
                            float_val = float(value)
                            if float_val.is_integer():
                                processed_config[field] = int(float_val)
                            else:
                                processed_config[field] = float_val
                        except ValueError:
                            processed_config[field] = field_config.get('default', 0)
                    else:
                        processed_config[field] = field_config.get('default', 0)
                elif field_config['type'] == 'checkbox':
                    processed_config[field] = field in form_data
                else:
                    processed_config[field] = value
        
        # 在離線模式下跳過網路相關的驗證
        if not offline_mode:
            # 驗證設定
            errors = config_manager.validate_protocol_config(protocol, processed_config)
            if errors:
                return jsonify({
                    'success': False, 
                    'message': '設定驗證失敗',
                    'errors': errors
                })
        
        # 儲存設定
        if config_manager.update_protocol_config(protocol, processed_config):
            config_manager.load_config()
            
            # 自動將此協定設為啟用協定
            if config_manager.set_active_protocol(protocol):
                logging.info(f"成功設定啟用協定為: {protocol}")
                # 驗證設定是否真的生效
                current_active = config_manager.get_active_protocol()
                logging.info(f"驗證: 目前啟用協定為: {current_active}")
            else:
                logging.error(f"設定啟用協定失敗: {protocol}")
            
            # 自動啟動已設定的協定（不僅限於MQTT）
            try:
                from uart_integrated import protocol_manager
                protocol_manager.start(protocol)
                logging.info(f"自動啟動協定: {protocol}")
            except Exception as e:
                logging.warning(f"自動啟動協定 {protocol} 失敗: {e}")
            
            message = f'{protocol} 設定已成功儲存並啟動'
            if offline_mode:
                message += '（離線模式）'
            
            flash(message, 'success')
            return jsonify({
                'success': True, 
                'message': '設定已儲存',
                'redirect_to_home': True,
                'redirect_delay': 1000  # 1秒後重定向
            })
        else:
            return jsonify({'success': False, 'message': '儲存設定時發生錯誤'})
            
    except Exception as e:
        logging.exception(f'儲存協定設定失敗: {str(e)}')
        return jsonify({'success': False, 'message': f'處理設定時發生錯誤: {str(e)}'})


@integrated_protocol_bp.route('/test-ftp-connection/<protocol>', methods=['POST'])
def test_ftp_connection(protocol):
    """測試 FTP 連接"""
    logging.info(f'測試 FTP 連接: {protocol}, remote_addr={request.remote_addr}')
    
    from config_manager import config_manager
    
    if protocol.upper() != 'FTP':
        return jsonify({'success': False, 'message': '此功能僅支援 FTP 協定'})
    
    try:
        # 獲取當前 FTP 設定
        config = config_manager.get_protocol_config('FTP')
        
        if not config:
            return jsonify({'success': False, 'message': '找不到 FTP 設定，請先儲存設定後再測試'})
        
        # 檢查必要參數
        host = config.get('host', '')
        port = config.get('port', 21)
        username = config.get('username', '')
        password = config.get('password', '')
        
        if not all([host, username]):
            return jsonify({
                'success': False, 
                'message': 'FTP 設定不完整，請檢查主機位址和使用者名稱'
            })
        
        # 執行 FTP 連接測試
        import ftplib
        from io import StringIO
        import contextlib
        
        # 捕獲連接過程中的輸出
        connection_log = StringIO()
        
        try:
            with contextlib.redirect_stdout(connection_log):
                ftp = ftplib.FTP()
                ftp.connect(host, int(port), timeout=10)
                ftp.login(username, password)
                
                # 測試目錄列表
                file_list = []
                ftp.retrlines('LIST', file_list.append)
                
                ftp.quit()
            
            return jsonify({
                'success': True,
                'message': 'FTP 連接測試成功',
                'details': {
                    'host': host,
                    'port': port,
                    'username': username,
                    'file_count': len(file_list),
                    'connection_info': connection_log.getvalue()
                }
            })
            
        except ftplib.error_perm as e:
            return jsonify({
                'success': False,
                'message': f'FTP 權限錯誤: {str(e)}'
            })
        except ftplib.error_temp as e:
            return jsonify({
                'success': False,
                'message': f'FTP 臨時錯誤: {str(e)}'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'FTP 連接失敗: {str(e)}'
            })
            
    except Exception as e:
        logging.error(f"FTP 連接測試失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'測試過程發生錯誤: {str(e)}'
        }), 500


@integrated_protocol_bp.route('/api/protocols')
def api_protocols():
    """API: 獲取支援的協定清單"""
    try:
        from config_manager import config_manager
        
        protocols = config_manager.get_supported_protocols()
        active_protocol = config_manager.get_active_protocol()
        
        return jsonify({
            'success': True,
            'protocols': protocols,
            'active_protocol': active_protocol
        })
    except Exception as e:
        logging.error(f"獲取協定清單失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@integrated_protocol_bp.route('/api/protocol-config/<protocol>')
def api_protocol_config(protocol):
    """API: 獲取特定協定的設定"""
    try:
        from config_manager import config_manager
        
        if not config_manager.validate_protocol(protocol):
            return jsonify({
                'success': False,
                'message': '不支援的協定'
            }), 400
        
        config = config_manager.get_protocol_config(protocol)
        field_info = config_manager.get_protocol_field_info(protocol)
        description = config_manager.get_protocol_description(protocol)
        
        return jsonify({
            'success': True,
            'protocol': protocol,
            'config': config,
            'field_info': field_info,
            'description': description
        })
    except Exception as e:
        logging.error(f"獲取協定設定失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@integrated_protocol_bp.route('/api/config')
def api_config():
    """API: 獲取完整設定"""
    try:
        from config_manager import config_manager
        config = config_manager.get_all_config()
        
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        logging.error(f"獲取設定失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500