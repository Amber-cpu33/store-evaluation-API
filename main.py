# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException
import onnxruntime as rt
import numpy as np
import pickle
import json
import os
import xgboost as xgb
from google.cloud import storage

# ==========================================
# 1. 常數與雲端環境設定
# ==========================================
BUCKET_NAME = "conveniencestore-analysis-ml-bucket"
MODEL_ONNX = "store_prediction_model.onnx"
MODEL_JSON = "store_xgb_model_v24.json"
SHAP_DB_FILE = "SHAP_XGB_Full_Database_v28
.pkl"

def download_assets():
    try:
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        for f in [MODEL_ONNX, MODEL_JSON, SHAP_DB_FILE]:
            if not os.path.exists(f) or os.path.getsize(f) < 100:
                print(f"📡 正在從雲端下載: {f}...")
                blob = bucket.blob(f)
                blob.download_to_filename(f)
    except Exception as e:
        print(f"❌ 資源下載失敗: {str(e)}")
        raise e

download_assets()

# ==========================================
# 2. 模型初始化 (分組基準計算)
# ==========================================

# 分組中位數店鋪數據：為了加速shap值計算，先產出兩群的中位數基準值
MEDIAN_CVS = np.array([[1.0, 0.375, 176.045, 0.0039, 587.0, 79.0, 305471.0, -15381.0, 1.0, 251.6, 10.19, 5138.0, 74.5]], dtype=np.float32)
MEDIAN_SUPER = np.array([[0.0, 0.041, 165.269, 0.0055, 590.0, 81.5, 305471.0, -27046.0, 1.0, 238.4, 10.18, 5196.0, 80.0]], dtype=np.float32)

xgb_booster = None
FEATURE_ORDER = None
BASE_MARGIN_CVS = 0.0
BASE_MARGIN_SUPER = 0.0
sess = None
CAT_MAPPING = {}
shap_package = None

try:
    # A. 載入 XGBoost
    xgb_booster = xgb.Booster()
    xgb_booster.load_model(MODEL_JSON)

    # B. 載入 SHAP 資料庫與特徵順序
    with open(SHAP_DB_FILE, 'rb') as f:
        shap_package = pickle.load(f)
    FEATURE_ORDER = [f.replace(" ", "") for f in shap_package['features']]

    # C. 🚀 計算分組基準值 (Approach 2)
    def get_margin(booster, vals):
        d = xgb.DMatrix(vals, feature_names=FEATURE_ORDER)
        return float(booster.predict(d, output_margin=True)[0])

    BASE_MARGIN_CVS = get_margin(xgb_booster, MEDIAN_CVS)
    BASE_MARGIN_SUPER = get_margin(xgb_booster, MEDIAN_SUPER)

    # D. 載入 ONNX
    sess = rt.InferenceSession(MODEL_ONNX)
    onnx_meta = json.loads(sess.get_modelmeta().custom_metadata_map['model_config'])
    CAT_MAPPING = onnx_meta['category_mapping']
    
    print(f"✅ v28 啟動成功！ (CVS Base: {BASE_MARGIN_CVS:.2f} | Super Base: {BASE_MARGIN_SUPER:.2f})")

except Exception as e:
    raise RuntimeError(f"初始化失敗: {str(e)}")

# ==========================================
# 3. API 路由設定
# ==========================================
app = FastAPI()

@app.post("/predict")
async def predict(data: dict):
    try:
        # 1. 預處理輸入
        is_cvs = int(data.get("是否便利商店", 0))
        threshold = 0.5 if is_cvs == 1 else 0.7
        
        inputs = []
        for col in FEATURE_ORDER:
            val = data.get(col)
            if col == '最近的熱鬧據點類型' and not isinstance(val, (int, float)):
                val = CAT_MAPPING.get(str(val), -1)
            elif col == '租金_log' and val is None:
                val = np.log1p(float(data.get('租金', 0)))
            elif col == '日夜人流差' and val is None:
                day = float(data.get('行政區平日日間活動人數', 0))
                night = float(data.get('行政區平日夜間停留人數', 0))
                val = day - night
            inputs.append(float(val) if val is not None else 0.0)
            
        input_array = np.array([inputs], dtype=np.float32)

        # 2. 推論與 SHAP 計算
        prob = float(sess.run(None, {sess.get_inputs()[0].name: input_array})[1][0][1])
        dmat = xgb.DMatrix(input_array, feature_names=FEATURE_ORDER)
        
        raw_shaps = xgb_booster.predict(dmat, pred_contribs=True)[0]
        native_shaps, native_base = raw_shaps[:-1], float(raw_shaps[-1])
        target_base = BASE_MARGIN_CVS if is_cvs == 1 else BASE_MARGIN_SUPER
        
        # 🚀 執行基準平移
        shift = (native_base - target_base) / len(FEATURE_ORDER)
        shap_values = native_shaps + shift

        # 3. 提取 Top 2 影響因子
        analysis = []
        for i, col in enumerate(FEATURE_ORDER):
            if col in ["是否便利商店", "最近的熱鬧據點類型"]: continue
            val = float(shap_values[i])
            analysis.append({"col": col, "val": val, "abs": abs(val)})
        
        top = sorted(analysis, key=lambda x: x['abs'], reverse=True)[:2]

        # 4. 🚀 封裝為「本地端最方便對接」格式 (v28 專屬)
        return {
            "id": int(data.get("id", 0)),
            "score": round(prob * 100, 1), # 直接對齊本地端變數 score
            "report": "優質位點 (推薦展店)" if prob >= threshold else "高風險位點 (建議迴避)",
            
            # 對齊 get_ai_insight 所需欄位
            "top1_feature": top[0]['col'],
            "top1_dir": "(+)" if top[0]['val'] > 0 else "(-)",
            "top2_feature": top[1]['col'],
            "top2_dir": "(+)" if top[1]['val'] > 0 else "(-)",

            # 對齊 LLM 顧問準則所需元數據
            "metadata": {
                "縣市": data.get("縣市"),
                "行政區": data.get("行政區"),
                "里別": data.get("里別"),
                "里人口數": data.get("里人口數"),
                "里人均收入中位數": data.get("里人均收入中位數"),
                "是否便利商店": is_cvs
            },

            # 🚀 對齊雷達圖所需 SHAP 值 (保留原始名稱)
            "shap_values": {col: round(float(shap_values[i]), 5) for i, col in enumerate(FEATURE_ORDER)}
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Store Intelligence API v28 (Unified Logic) is active."}

if __name__ == "__main__":
    import sys
    # 如果只是想檢查初始化 (BASE_MARGIN 等)
    print("✨ 初始化檢查完成。")
    
    if "--serve" in sys.argv:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        print("ℹ️ 伺服器未啟動。若要啟動 API，請加入 --serve 參數。")