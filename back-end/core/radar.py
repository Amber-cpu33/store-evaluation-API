# -*- coding: utf-8 -*-
import numpy as np
import core.predictor as predictor_module

# 雷達圖顯示的特徵索引（從 all_numeric_features 中選取）
RADAR_SELECTED_IDX = [1, 2, 3, 4, 6, 9]

# 特徵顯示名稱對應
FEATURE_NAME_MAP = {
    '競爭優勢': '區域市占率',
    'people_per_store': '店均服務人數',
    '競爭壓力指標': '競爭飽和度',
    '最近的熱鬧據點距離': '最近導流節點距離',
    '發票張數指標': '發票張數指標',
    '租金_log': '租金',
    '里人均收入中位數': '人均收入',
    '里人口數': '基礎客源',
    '日夜人流差': '商圈日夜落差',
    '發票銷售額指標': '發票銷售指標',
    '行政區平日日間活動人數': '日間活動人流',
}

# 負向特徵（SHAP 值越高，實際越不利）
NEGATIVE_FEATURES = ['競爭壓力指標', '最近的熱鬧據點距離', '租金_log']


def compute_radar(shap_values: dict, is_cvs: int) -> dict:
    """
    shap_values: { feature_name: shap_value } （來自 predictor.predict）
    is_cvs: 1=便利商店, 0=超市藥妝
    回傳: { labels: [str], values: [int] }
    """
    db = predictor_module.shap_package
    features = [f.replace(" ", "") for f in db['features']]
    # 排除類別型特徵
    all_numeric = [f for f in features if f != '最近的熱鬧據點類型']
    group_key = 'CVS' if is_cvs == 1 else 'Super'
    thresholds_dict = db[group_key]['thresholds']

    labels, values = [], []
    for idx in RADAR_SELECTED_IDX:
        if idx >= len(all_numeric):
            continue
        feat = all_numeric[idx]
        shap_val = abs(shap_values.get(feat, 0.0))
        feat_thresholds = thresholds_dict.get(feat, [0, 0, 0, 0])
        score = int(np.digitize(shap_val, feat_thresholds)) + 1

        if feat in NEGATIVE_FEATURES:
            score = max(1, 6 - score)
            sign = "(-)"
        else:
            sign = "(+)"

        display_name = FEATURE_NAME_MAP.get(feat, feat)
        labels.append(f"{display_name}\n{sign}")
        values.append(score)

    return {"labels": labels, "values": values}
