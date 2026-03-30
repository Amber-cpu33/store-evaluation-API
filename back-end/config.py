import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")  # 僅用於正向 Geocoding（地址→座標）

# 模型檔案路徑
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_ONNX_PATH = os.path.join(BASE_DIR, "models", "store_prediction_model.onnx")
MODEL_JSON_PATH = os.path.join(BASE_DIR, "models", "store_xgb_model_v24.json")
SHAP_DB_PATH = os.path.join(BASE_DIR, "models", "SHAP_XGB_Full_Database_v28.pkl")

# 資料檔案路徑
FULL_DATA_PATH = os.path.join(BASE_DIR, "data", "full_data_v1.4.csv")
POPULAR_LOCATIONS_PATH = os.path.join(BASE_DIR, "data", "Popular_locations.csv")

# 品牌對照表：顯示名稱 → (公司名稱, is_cvs)
BRAND_MAP: dict[str, tuple[str, int]] = {
    # 便利商店
    '全家':     ('全家便利商店股份有限公司', 1),
    '7-ELEVEN': ('統一超商股份有限公司',    1),
    '萊爾富':   ('萊爾富國際股份有限公司',  1),
    'OK便利商店': ('來來超商股份有限公司',    1),
    # 超市及藥妝
    '全聯':   ('全聯實業股份有限公司',          0),
    '家樂福': ('家福股份有限公司',              0),
    '美廉社': ('三商家購股份有限公司',          0),
    '屈臣氏': ('台灣屈臣氏個人用品商店股份有限公司', 0),
    '康是美': ('統一生活事業股份有限公司',      0),
}

CVS_BRANDS      = [k for k, v in BRAND_MAP.items() if v[1] == 1]
SUPER_BRANDS    = [k for k, v in BRAND_MAP.items() if v[1] == 0]

# 公司名稱 → 顯示品牌名稱
COMPANY_TO_BRAND: dict[str, str] = {v[0]: k for k, v in BRAND_MAP.items()}
