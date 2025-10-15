# 離線資源配置說明

本專案已將所有外部 CDN 資源下載到本地，確保在無網路環境下也能正常運行。

## 靜態資源資料夾結構

```
static/
├── css/
│   └── vendor/                     # 第三方 CSS 庫
│       ├── bootstrap.min.css       # Bootstrap 5.1.3 CSS 框架
│       ├── fontawesome.min.css     # Font Awesome 6.0.0 圖標庫
│       └── animate.min.css         # Animate.css 4.1.1 動畫庫
├── js/
│   └── vendor/                     # 第三方 JavaScript 庫
│       ├── bootstrap.bundle.min.js            # Bootstrap 5.1.3 JavaScript
│       ├── chart.min.js                       # Chart.js 圖表庫
│       └── chartjs-adapter-date-fns.bundle.min.js  # Chart.js 日期適配器
└── fonts/                          # 字型檔案
    ├── fa-solid-900.woff2          # Font Awesome 實心圖標字型
    ├── fa-regular-400.woff2        # Font Awesome 常規圖標字型
    └── fa-brands-400.woff2         # Font Awesome 品牌圖標字型
```

## 已更新的 HTML 檔案

所有 templates/ 資料夾中的 HTML 檔案都已經更新，外部 CDN 連結已替換為本地路徑：

- 11.html
- 404.html  
- application.html
- config_summary.html
- dashboard.html
- db_setting.html
- error.html
- home.html
- host_config.html
- multi_protocol_management.html
- protocol_config.html
- wifi.html

## CDN 連結替換對照表

| 原始 CDN 連結 | 本地路徑 |
|--------------|----------|
| https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css | /static/css/vendor/bootstrap.min.css |
| https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css | /static/css/vendor/bootstrap.min.css |
| https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css | /static/css/vendor/fontawesome.min.css |
| https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css | /static/css/vendor/fontawesome.min.css |
| https://cdn.jsdelivr.net/npm/animate.css@4.1.1/animate.min.css | /static/css/vendor/animate.min.css |
| https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js | /static/js/vendor/bootstrap.bundle.min.js |
| https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js | /static/js/vendor/bootstrap.bundle.min.js |
| https://cdn.jsdelivr.net/npm/chart.js | /static/js/vendor/chart.min.js |
| https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js | /static/js/vendor/chartjs-adapter-date-fns.bundle.min.js |

## 字型路徑調整

Font Awesome CSS 檔案中的字型路徑已從 `../webfonts/` 調整為 `../fonts/`，以符合本專案的資料夾結構。

## 離線運行確認

現在您的專案可以完全離線運行，所有必要的 CSS、JavaScript 和字型檔案都已儲存在本地。無需網路連線即可正常顯示所有樣式和圖標。

## 備註

- 所有檔案都是壓縮版本（.min），載入速度已優化
- 字型檔案使用 WOFF2 格式，支援現代瀏覽器並具有最佳壓縮率
- 如需更新這些庫版本，請重新下載對應檔案並更新相關路徑

最後更新日期: 2025年10月15日