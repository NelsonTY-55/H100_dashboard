# 設備設定儲存改進

## 概述

設備設定儲存已從 JSON 檔案改進為使用 SQLite 資料庫，提供更好的資料完整性和查詢效能。

## 改變內容

### 之前（JSON 版本）
- 設備設定儲存在 `multi_device_settings.json` 檔案中
- 每次讀取/寫入都需要載入整個檔案
- 資料結構相對簡單

### 現在（資料庫版本）
- 設備設定儲存在 SQLite 資料庫的 `device_info` 表格中
- 支援更豐富的欄位和關聯
- 更好的並發處理和資料完整性

## 資料庫結構

設備資訊儲存在 `device_info` 表格中，包含以下欄位：

```sql
CREATE TABLE device_info (
    mac_id TEXT PRIMARY KEY,
    device_name TEXT,
    device_type TEXT,
    device_model TEXT,
    factory_area TEXT,
    floor_level TEXT,
    location_description TEXT,
    installation_date DATE,
    last_maintenance DATE,
    status TEXT DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

## API 兼容性

`MultiDeviceSettingsManager` 類別的公開 API 保持不變：

- `load_all_devices()` - 載入所有設備設定
- `load_device_settings(mac_id)` - 載入特定設備設定
- `save_device_settings(mac_id, settings)` - 儲存設備設定
- `delete_device_settings(mac_id)` - 刪除設備設定
- `get_device_count()` - 取得設備數量
- `get_all_mac_ids()` - 取得所有 MAC ID
- `is_device_configured(mac_id)` - 檢查設備是否已設定

## 欄位對應

JSON 欄位到資料庫欄位的對應：

| JSON 欄位 | 資料庫欄位 | 說明 |
|-----------|-----------|------|
| device_name | device_name | 設備名稱 |
| device_location | location_description | 位置描述 |
| device_model | device_model | 設備型號 |
| device_serial | mac_id | MAC ID (主鍵) |
| device_description | location_description | 設備描述 |
| device_type | device_type | 設備類型 |
| factory_area | factory_area | 廠區 |
| floor_level | floor_level | 樓層 |
| installation_date | installation_date | 安裝日期 |
| last_maintenance | last_maintenance | 最後維護日期 |
| status | status | 設備狀態 |
| created_at | created_at | 建立時間 |
| updated_at | updated_at | 更新時間 |

## 優點

1. **資料完整性**：SQLite 提供 ACID 事務保證
2. **並發處理**：更好的多執行緒安全性
3. **查詢效能**：支援索引和複雜查詢
4. **資料關聯**：可以與其他表格建立關聯
5. **備份容易**：單一資料庫檔案包含所有資料
6. **擴展性**：容易新增新欄位和功能

## 注意事項

- 原有的 JSON 檔案不會自動遷移，需要手動處理
- 確保資料庫檔案有適當的備份
- 如果需要匯出資料，可以使用 `export_settings()` 方法

## 驗證

執行以下命令驗證系統運作正常：

```python
from multi_device_settings import MultiDeviceSettingsManager

manager = MultiDeviceSettingsManager()
devices = manager.load_all_devices()
print(f"目前有 {len(devices)} 個設備在資料庫中")
```

## 日期

2025年8月25日
