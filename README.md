# 🏪 Smart Site Selection｜連鎖展店分析智慧系統 (v2.0)

全端網頁應用，協助連鎖品牌（便利商店、超市藥妝）評估展店位點潛力。

> 運用 Vibe Coding 製作。

🌐 **線上體驗**：https://conveniencestore-analysis-ml.web.app

| | URL |
|---|---|
| **前端** | https://conveniencestore-analysis-ml.web.app |
| **後端 API** | https://store-prediction-service-776185979298.asia-east1.run.app |

---

## ✨ 主要功能

### 查表模式
- 下拉選單選擇縣市 / 行政區（依人口數排序）/ 里別
- 同一里有多間門市時可用箭頭切換（第 X 間 / 共 Y 間）
- 顯示該分公司名稱與品牌

### 地址模式
- 輸入任意地址 → Google Maps 轉座標 → 國土測繪 API 識別里別
- 即時計算特徵（競店距離、熱鬧據點距離、租金等）
- 支援 9 個品牌選擇（精確計算同品牌 vs 同類競爭）

### 分析結果
- **營運推薦分數**（0–100）與展店建議
- **雷達圖**：6 大競爭維度視覺化
- **AI 洞察報告**：Gemini 2.5 Flash 逐字串流輸出
- 里人口數、收入中位數、周邊競店數

---

## 🏗 專案結構

```
store-prediction-website/
├── back-end/
│   ├── main.py              # FastAPI 9 個端點
│   ├── config.py            # API keys、品牌對照表
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── core/
│   │   ├── predictor.py     # ONNX 推論 + XGBoost SHAP
│   │   ├── radar.py         # 雷達圖分數計算
│   │   ├── geocoding.py     # Google Maps + 國土測繪 API
│   │   ├── geo.py           # 城市/行政區/里別查詢
│   │   ├── distance.py      # Haversine 距離計算
│   │   ├── feature_builder.py  # 地址模式特徵建構
│   │   └── llm.py           # Gemini SSE 串流
│   ├── data/
│   │   ├── loader.py        # 啟動時載入所有靜態資料至記憶體
│   │   ├── full_data_v1.4.csv
│   │   └── Popular_locations.csv
│   └── models/
│       ├── store_prediction_model.onnx
│       ├── store_xgb_model_v24.json
│       └── SHAP_XGB_Full_Database_v28.pkl
├── front-end/
│   └── angular/             # Angular 前端
│       └── src/
│           ├── common.ts    # BACK_END_URL 設定
│           ├── services/    # API 呼叫
│           ├── app/site-analyzer/  # 主頁元件
│           └── value-objects/      # 型別定義
├── proxy/nginx/             # Nginx 反向代理
├── docker-compose.yaml
└── .env                     # API Keys（不納入版控）
```

---

## 🚀 本地啟動

### 環境需求
- Python 3.10+
- Node.js 18+（前端）

### 後端
```bash
cd back-end
# 建立 .env 並填入金鑰
echo "GEMINI_API_KEY=your_key" >> .env
echo "GOOGLE_MAPS_API_KEY=your_key" >> .env

pip install -r requirements.txt
GEMINI_API_KEY=your_key GOOGLE_MAPS_API_KEY=your_key uvicorn main:app --host 0.0.0.0 --port 8000
```

### 前端
```bash
cd front-end/angular
npm install
npx ng serve
# 開啟 http://localhost:4200
```

---

## 📡 API 端點

| 端點 | 說明 |
|------|------|
| `GET /api/cities` | 城市列表 |
| `GET /api/districts/{city}` | 行政區列表（依人口數降序） |
| `GET /api/neighborhoods/{city}/{district}` | 里別列表 |
| `GET /api/brands` | 品牌類型 |
| `GET /api/brands-by-type/{type}` | 具體品牌（全家、7-ELEVEN 等） |
| `GET /api/geo-check/{city}/{district}/{neighborhood}` | 地理驗證 |
| `GET /api/run-prediction/{city}/{district}/{neighborhood}/{brand}?store_index=0` | 查表預測 |
| `GET /api/ai-insight/{city}/{district}/{neighborhood}/{brand}?store_index=0` | AI 洞察 SSE 串流 |
| `POST /api/predict-by-address` | 地址即時查詢 `{address, brand_name}` |

---

## 🧠 模型說明

- **推論**：ONNX Runtime（v28 模型）
- **解釋性**：XGBoost SHAP，業態基準校準（CVS: 0.13 / Super: 1.58）
- **雷達圖特徵**：區域市占率、店均服務人數、競爭飽和度、人均收入、日間人流、租金
- **AI 洞察**：Gemini 2.5 Flash，含 8 條業務邏輯規則的顧問提示詞

---

## 🏷 支援品牌

| 便利商店 | 超市及藥妝 |
|---------|-----------|
| 全家、7-ELEVEN、萊爾富、OK便利商店 | 全聯、家樂福、美廉社、屈臣氏、康是美 |

---

## v1.0 → v2.0 改動 (使用 Claude Vibe Coding)

- 架構重組：扁平 → `back-end/` + `front-end/` 分離
- 資料載入：CSV 逐次讀取 → 啟動時全部載入記憶體
- 新增地址即時查詢模式
- AI 洞察改為 SSE 串流（逐字輸出）
- 同品牌 vs 同類競爭精確計算
- 多店切換瀏覽同里所有門市
- 地址模式 Geo 快取（Google Maps + NLSC 不重複呼叫）
- 前端預測結果快取（同地址+品牌直接回傳）
- 後端部署 Cloud Run、前端部署 Firebase Hosting
