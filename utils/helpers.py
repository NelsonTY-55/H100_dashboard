import logging
from functools import wraps
from flask import jsonify


def success_response(data=None, message=None, **kwargs):
    """
    回傳標準化的成功 JSON 響應。
    data: dict 包含要回傳的資料
    message: 積極訊息
    kwargs: 其他欄位
    """
    resp = {"success": True}
    if message:
        resp["message"] = message
    if isinstance(data, dict):
        resp.update(data)
    resp.update(kwargs)
    return jsonify(resp)


def error_response(message, code=500, **kwargs):
    """
    回傳標準化的錯誤 JSON 響應。
    message: 錯誤訊息
    code: HTTP 狀態碼
    kwargs: 其他欄位
    """
    logging.error(message)
    resp = {"success": False, "message": message}
    resp.update(kwargs)
    return jsonify(resp), code


def api_handler(default_data=None):
    """
    API 錯誤處理裝飾器。
    如果被包裹的函式回傳 dict，則視為成功並呼叫 success_response。
    若發生例外，回傳 error_response。
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                result = fn(*args, **kwargs)
                # 如果已經是 Flask 響應物件，直接回傳
                if hasattr(result, 'status_code'):
                    return result
                # 支援函式回傳 (data_dict) 或 (data_dict, code)
                if isinstance(result, tuple) and isinstance(result[0], dict):
                    data, code = result if len(result) == 2 and isinstance(result[1], int) else (result[0], None)
                    if code:
                        return success_response(data=data, **{}) , code
                    return success_response(data=data)
                if isinstance(result, dict):
                    return success_response(data=result)
                return result
            except Exception as e:
                logging.exception(f"API error in {fn.__name__}: {e}")
                return error_response(str(e))
        return wrapper
    return decorator
