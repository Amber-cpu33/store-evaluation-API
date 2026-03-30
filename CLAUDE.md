# CLAUDE.md — store-prediction-website

連鎖展店選址分析系統。後端 FastAPI（Cloud Run），前端 Angular（Firebase Hosting）。

## 部署資訊

| | URL |
|---|---|
| 前端 | https://conveniencestore-analysis-ml.web.app |
| 後端 API | https://store-prediction-service-776185979298.asia-east1.run.app |
| GitHub | https://github.com/Amber-cpu33/store-evaluation-API |
| GCP Project | conveniencestore-analysis-ml |

## 本地啟動

```bash
# 後端（API keys 在 ../.env）
cd back-end
set -a && source ../.env && set +a
uvicorn main:app --host 0.0.0.0 --port 8000

# 前端
cd front-end/angular
npx ng serve
```

若 port 8000 被占用：`powershell -Command "Stop-Process -Name python -Force"`

## 專案結構

```
back-end/
├── main.py              # FastAPI 9 個端點
├── config.py            # 品牌對照表、API key、模型路徑
├── core/
│   ├── predictor.py     # ONNX 推論 + XGBoost SHAP
│   ├── feature_builder.py  # 地址→特徵（含 geo 快取）
│   ├── radar.py         # SHAP → 6 維雷達圖分數
│   ├── geocoding.py     # Google Maps + 國土測繪 NLSC API
│   ├── geo.py           # 城市/行政區/里別查詢
│   ├── distance.py      # Haversine 距離、500m 競店統計
│   └── llm.py           # Gemini 2.5 Flash SSE 串流
├── data/
│   ├── loader.py        # 啟動時載入所有靜態資料至記憶體
│   ├── full_data_v1.4.csv
│   └── Popular_locations.csv
└── models/
    ├── store_prediction_model.onnx
    ├── store_xgb_model_v24.json
    └── SHAP_XGB_Full_Database_v28.pkl

front-end/angular/src/
├── common.ts            # BACK_END_URL（切換本地/Cloud Run）
├── services/            # geo.ts / brand.ts / prediction.ts
├── app/site-analyzer/   # 主頁元件（查表 + 地址模式）
└── value-objects/       # 型別定義
```

## 關鍵設計決策

### 記憶體查表架構
啟動時 `loader.load_all()` 一次性載入全部資料：
- `prediction_lookup`: `dict[(縣市, 行政區, 里別, is_cvs), list[dict]]` — 每里所有門市特徵
- `neighborhood_lookup`: 里別人口/收入/租金
- `district_lookup`: 行政區人口/人流
- `store_locations`: 營運中店家座標（5073 筆，用於距離計算）
- `popular_spots`: 熱鬧據點座標（939 筆）

### prediction_lookup 含廢止店（刻意保留）
查表模式**不過濾**廢止店。若只顯示營運中，每個查詢分數都偏高，缺乏對比。
保留廢止店讓使用者看到同一里既有成功也有失敗案例，分析才有意義。
啟動 log 的 5073 筆是 `store_locations`（只含營運中），`prediction_lookup` 總筆數約 7000 筆。

### 雙軌推薦門檻
- 便利商店：閾值 0.5（積極市佔擴張）
- 超市藥妝：閾值 0.7（高質量選址優先）

### 快取策略
- **後端 geo 快取**（`feature_builder._geo_cache`）：同一地址換品牌時，跳過 Google Maps + NLSC，只重算競店特徵
- **前端預測快取**（`PredictionService.addressCache`）：key = `address__brandName`，完全相同組合直接回傳，不打 API

### 查表模式多店切換
同一里可能有多間同類型門市，用 `store_index` query param 切換，前端 `switchStore(delta)` 方法。

### SSE 串流
- 查表模式：AI 洞察用 SSE 串流（`/api/ai-insight`），前端 `onChunk(chunk, isFirst)` — isFirst=true 時取代 loading 文字
- 地址模式：AI 洞察與雷達圖計算用 `asyncio.gather` 並行，一次回傳

### NLSC SSL
國土測繪 API 用 `httpx.AsyncClient(verify=False)` 繞過憑證驗證

## 前端部署流程

```bash
cd front-end/angular

# 切換到 Cloud Run URL（common.ts）
npx ng build

firebase deploy
```

本地測試時記得把 `common.ts` 的 `BACK_END_URL` 換回 `http://localhost:8000/api`。

## 後端部署（Cloud Run）

```bash
# 在 GCP Cloud Shell
git clone https://github.com/Amber-cpu33/store-evaluation-API.git
cd store-evaluation-API/back-end
gcloud run deploy store-prediction-service --source . --region asia-east1 --platform managed --allow-unauthenticated --set-env-vars GEMINI_API_KEY=...,GOOGLE_MAPS_API_KEY=...
```

Dockerfile 使用 `${PORT:-8000}` 兼容 Cloud Run 的 PORT 環境變數。

## 品牌對照表（config.py）

| 顯示名稱 | 公司名稱 | is_cvs |
|---|---|---|
| 全家 | 全家便利商店股份有限公司 | 1 |
| 7-ELEVEN | 統一超商股份有限公司 | 1 |
| 萊爾富 | 萊爾富國際股份有限公司 | 1 |
| OK便利商店 | 來來超商股份有限公司 | 1 |
| 全聯 | 全聯實業股份有限公司 | 0 |
| 家樂福 | 家福股份有限公司 | 0 |
| 美廉社 | 三商家購股份有限公司 | 0 |
| 屈臣氏 | 台灣屈臣氏個人用品商店股份有限公司 | 0 |
| 康是美 | 統一生活事業股份有限公司 | 0 |

## 已知問題 / 注意事項

- `ng serve` 有時不熱重載：需重啟才能套用 TS 變更
- `prediction_lookup` 無廢止/營運中標示，前端查表不顯示店家狀態
- 地址模式的 `發票銷售額指標` 和 `發票張數指標` 填 0（無法即時取得）
