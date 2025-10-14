# H100 Dashboard 專案結構說明

## 重構後的 MVC 架構

本專案已完全重構為 MVC（Model-View-Controller）架構，提供更好的程式碼組織和維護性。

## 主要程式檔案

### 1. 樹莓派端主程式
**檔案**: `app_integrated_mvc.py`
- **功能**: 完整的 H100 Dashboard 應用程式
- **架構**: MVC 架構 + Flask 工廠模式
- **連接埠**: 5000
- **用途**: 在樹莓派上執行，提供完整的 UART、設備管理、資料庫等功能

### 2. 筆電端 API 服務
**檔案**: `dashboard.py`
- **功能**: 獨立的 Dashboard API 服務
- **架構**: 簡化的 MVC 架構
- **連接埠**: 5001
- **用途**: 在筆電上執行，提供 API 服務和遠端控制

## MVC 架構組件

### Controllers（控制器層）
**位置**: `controllers/`
- `integrated_home_controller.py` - 首頁控制器
- `integrated_device_controller.py` - 設備管理控制器
- `integrated_wifi_controller.py` - WiFi 設定控制器
- `integrated_dashboard_controller.py` - 儀表板控制器
- `integrated_protocol_controller.py` - 協定管理控制器
- `integrated_uart_controller.py` - UART 通訊控制器
- `dashboard_controller.py` - Dashboard API 控制器

### Models（模型層）
**位置**: `models/`
- `dashboard_data_sender_model.py` - 資料發送模型
- `dashboard_model.py` - 儀表板資料模型
- `device_model.py` - 設備模型
- `ftp_model.py` - FTP 服務模型
- `logging_model.py` - 日誌模型
- `network_model.py` - 網路模型
- `system_model.py` - 系統模型
- `uart_model.py` - UART 通訊模型

### Views（視圖層）
**位置**: `views/`
- `api_responses.py` - API 回應格式化
- `dashboard_view.py` - 儀表板視圖
- `template_views.py` - 模板視圖

### Core（核心層）
**位置**: `core/`
- `app_factory.py` - Flask 應用程式工廠

### Configuration（配置層）
**位置**: `config/`
- `config_manager.py` - 配置管理器

## 支援檔案

### 業務邏輯模組
- `database_manager.py` - 資料庫管理
- `device_settings.py` - 設備設定管理
- `multi_device_settings.py` - 多設備設定管理
- `uart_integrated.py` - UART 整合通訊
- `multi_protocol_manager.py` - 多協定管理
- `network_utils.py` - 網路工具
- `port_manager.py` - 串口管理
- `wifi_manager.py` - WiFi 管理

### 模板檔案
**位置**: `templates/`
- HTML 模板檔案

### 工具與腳本
**位置**: `tools/`, `scripts/`
- `run_services.py` - 服務管理器
- 各種輔助腳本

### 測試檔案
**位置**: `tests/`
- 單元測試和整合測試

## 部署建議

### 雙設備部署（推薦）
1. **樹莓派**: 執行 `app_integrated_mvc.py`
2. **筆電**: 執行 `dashboard.py`

### 單設備部署
- 執行 `app_integrated_mvc.py` 即可獲得完整功能

## 已清理的檔案

以下舊版檔案已被刪除：
- `app.py` - 舊版主程式
- `dashboard_legacy.py` - 舊版 dashboard
- `dashboard_original.py` - 原始版 dashboard
- `core/app_integrated.py` - 舊版整合應用
- `core/app_with_settings.py` - 舊版設定應用
- `controllers/dashboard_controller_old.py` - 舊版控制器

## 優勢

1. **清晰的架構**: MVC 模式使程式碼結構更清晰
2. **模組化設計**: 每個功能都有獨立的模組
3. **易於維護**: 關注點分離，易於修改和擴展
4. **可重用性**: 組件可以在不同場景中重用
5. **測試友好**: 模組化設計便於單元測試
6. **部署靈活**: 支援單設備或多設備部署