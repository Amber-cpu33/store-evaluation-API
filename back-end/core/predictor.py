# -*- coding: utf-8 -*-
import pickle
import json
import numpy as np
import xgboost as xgb
import onnxruntime as rt
from config import MODEL_ONNX_PATH, MODEL_JSON_PATH, SHAP_DB_PATH

# ==========================================
# 模型與 SHAP 初始化（模組載入時執行一次）
# ==========================================

MEDIAN_CVS = np.array([[1.0, 0.375, 176.045, 0.0039, 587.0, 79.0, 305471.0, -15381.0, 1.0, 251.6, 10.19, 5138.0, 74.5]], dtype=np.float32)
MEDIAN_SUPER = np.array([[0.0, 0.041, 165.269, 0.0055, 590.0, 81.5, 305471.0, -27046.0, 1.0, 238.4, 10.18, 5196.0, 80.0]], dtype=np.float32)

xgb_booster: xgb.Booster = None
FEATURE_ORDER: list = []
BASE_MARGIN_CVS: float = 0.0
BASE_MARGIN_SUPER: float = 0.0
sess: rt.InferenceSession = None
CAT_MAPPING: dict = {}
shap_package: dict = None


def init_models():
    global xgb_booster, FEATURE_ORDER, BASE_MARGIN_CVS, BASE_MARGIN_SUPER, sess, CAT_MAPPING, shap_package

    # A. 載入 XGBoost
    xgb_booster = xgb.Booster()
    xgb_booster.load_model(MODEL_JSON_PATH)

    # B. 載入 SHAP 數據庫
    with open(SHAP_DB_PATH, 'rb') as f:
        shap_package = pickle.load(f)
    FEATURE_ORDER = [f.replace(" ", "") for f in shap_package['features']]

    # C. 計算業態分組基準邊際值
    def _get_margin(booster, vals):
        d = xgb.DMatrix(vals, feature_names=FEATURE_ORDER)
        return float(booster.predict(d, output_margin=True)[0])

    BASE_MARGIN_CVS = _get_margin(xgb_booster, MEDIAN_CVS)
    BASE_MARGIN_SUPER = _get_margin(xgb_booster, MEDIAN_SUPER)

    # D. 載入 ONNX
    sess = rt.InferenceSession(MODEL_ONNX_PATH)
    onnx_meta = json.loads(sess.get_modelmeta().custom_metadata_map['model_config'])
    CAT_MAPPING = onnx_meta['category_mapping']

    print(f"✅ 模型載入完成（CVS Base: {BASE_MARGIN_CVS:.2f} | Super Base: {BASE_MARGIN_SUPER:.2f}）")


def predict(features: dict) -> dict:
    """
    輸入特徵 dict，回傳預測結果。
    features 必須包含所有 FEATURE_ORDER 欄位（或可衍生的原始欄位）。
    回傳: { score, report, shap_values, top1_feature, top1_dir, top2_feature, top2_dir }
    """
    is_cvs = int(features.get("是否便利商店", 0))
    threshold = 0.5 if is_cvs == 1 else 0.7

    # 1. 組合特徵向量
    inputs = []
    for col in FEATURE_ORDER:
        val = features.get(col)
        if col == '最近的熱鬧據點類型' and not isinstance(val, (int, float)):
            val = CAT_MAPPING.get(str(val), -1)
        elif col == '租金_log' and val is None:
            val = np.log1p(float(features.get('租金', 0)))
        elif col == '日夜人流差' and val is None:
            day = float(features.get('行政區平日日間活動人數', 0))
            night = float(features.get('行政區平日夜間停留人數', 0))
            val = day - night
        inputs.append(float(val) if val is not None else 0.0)

    input_array = np.array([inputs], dtype=np.float32)

    # 2. ONNX 推論
    prob = float(sess.run(None, {sess.get_inputs()[0].name: input_array})[1][0][1])

    # 3. XGBoost SHAP + 基準平移
    dmat = xgb.DMatrix(input_array, feature_names=FEATURE_ORDER)
    raw_shaps = xgb_booster.predict(dmat, pred_contribs=True)[0]
    native_shaps, native_base = raw_shaps[:-1], float(raw_shaps[-1])
    target_base = BASE_MARGIN_CVS if is_cvs == 1 else BASE_MARGIN_SUPER
    shift = (native_base - target_base) / len(FEATURE_ORDER)
    shap_values = native_shaps + shift

    # 4. Top 2 影響因子
    analysis = []
    for i, col in enumerate(FEATURE_ORDER):
        if col in ["是否便利商店", "最近的熱鬧據點類型"]:
            continue
        val = float(shap_values[i])
        analysis.append({"col": col, "val": val, "abs": abs(val)})
    top = sorted(analysis, key=lambda x: x['abs'], reverse=True)[:2]

    return {
        "score": round(prob * 100, 1),
        "report": "優質位點 (推薦展店)" if prob >= threshold else "高風險位點 (建議迴避)",
        "top1_feature": top[0]['col'],
        "top1_dir": "(+)" if top[0]['val'] > 0 else "(-)",
        "top2_feature": top[1]['col'],
        "top2_dir": "(+)" if top[1]['val'] > 0 else "(-)",
        "shap_values": {col: round(float(shap_values[i]), 5) for i, col in enumerate(FEATURE_ORDER)},
    }
