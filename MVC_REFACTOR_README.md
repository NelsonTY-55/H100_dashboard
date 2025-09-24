# H100 Dashboard MVC 重構版使用說明

## 概述

成功將 `app_integrated.py` 重構為 MVC 架構，提高程式碼的可維護性和擴展性。

## 檔案結構

### 主程式
- `app_integrated_mvc.py` - 新的主程式入口（MVC 版本）
- `app_integrated.py` - 原始版本（保留作為備份）

### 模型層 (Models)
- `models/logging_model.py` - 日誌處理模型
- `models/ftp_model.py` - FTP 服務模型  
- `models/dashboard_data_sender_model.py` - Dashboard 資料發送模型

### 控制器層 (Controllers)
- `controllers/integrated_home_controller.py` - 主頁面控制器
- `controllers/integrated_device_controller.py` - 設備管理控制器
- `controllers/integrated_wifi_controller.py` - WiFi 設定控制器
- `controllers/integrated_dashboard_controller.py` - Dashboard 控制器
- `controllers/integrated_protocol_controller.py` - 協議設定控制器
- `controllers/integrated_uart_controller.py` - UART 控制器

### 應用程式工廠
- `app_factory.py` - 更新支援新的 Blueprint 註冊

## 啟動方式

### 使用 MVC 重構版本
```bash
python app_integrated_mvc.py
```

### 使用原始版本
```bash
python app_integrated.py
```

## 主要改進

1. **模組化設計**：將原本 3500+ 行的單一檔案拆分為多個小模組
2. **MVC 架構**：清楚分離資料邏輯、控制邏輯和視圖
3. **Blueprint 組織**：使用 Flask Blueprint 組織路由
4. **工廠模式**：使用應用程式工廠模式統一管理
5. **程式碼重用**：提取共通類別到模型層

## 功能對應

所有原始功能均已保留：

- ✅ 主頁面和基本頁面
- ✅ 設備設定管理
- ✅ WiFi 網路管理
- ✅ Dashboard 監控
- ✅ 協議設定
- ✅ UART 資料處理
- ✅ FTP 本地測試服務器
- ✅ Dashboard 資料發送服務
- ✅ 日誌輪轉管理

## 測試

執行測試腳本驗證功能：

```bash
python test_integrated_mvc.py
```

測試結果顯示：
- ✅ 模組導入成功
- ✅ 模型層功能正常
- ✅ 控制器層功能正常
- ✅ 應用程式工廠正常
- ✅ Flask 路由註冊正常

## API 端點

維持與原版本相同的 API 端點：

### 主要頁面
- `/` - 主頁面
- `/db-setting` - 設備設定
- `/wifi` - WiFi 設定
- `/dashboard` - Dashboard 面板

### API 端點
- `/api/device-settings` - 設備設定 API
- `/api/wifi/*` - WiFi 管理 API
- `/api/uart/*` - UART 控制 API
- `/api/dashboard/*` - Dashboard 資料 API
- `/api/protocols` - 協議管理 API

## 注意事項

1. **向後相容**：所有 API 端點和功能保持不變
2. **依賴項目**：確保所有相依模組已正確安裝
3. **設定檔**：使用相同的 `config.json` 和其他設定檔
4. **端口**：預設仍使用端口 5001

## 優勢

1. **可維護性**：程式碼分離清楚，容易維護
2. **可測試性**：每個模組可獨立測試
3. **可擴展性**：新功能可輕鬆添加新的控制器
4. **團隊開發**：多人可同時開發不同模組

---

🎉 MVC 重構完成！現在可以使用更清潔、更模組化的程式碼架構。