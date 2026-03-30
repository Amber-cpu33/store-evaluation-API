# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from config import FULL_DATA_PATH, POPULAR_LOCATIONS_PATH, COMPANY_TO_BRAND

# ==========================================
# 全域記憶體查表（容器啟動時載入一次）
# ==========================================

geo_tree: dict = {}
# { 縣市: { 行政區: [里別, ...] } }

neighborhood_lookup: dict = {}
# { (縣市, 行政區, 里別): { 里人口數, 里人均收入中位數, 租金, ... } }

district_lookup: dict = {}
# { (縣市, 行政區): { 日間人流, 夜間人流, 行政區人口, 行政區收入中位數 } }

prediction_lookup: dict = {}
# { (縣市, 行政區, 里別, 是否便利商店): [ { 完整特徵值 dict }, ... ] }（按同一里所有店）

store_locations: list = []
# [ { lat, lon, is_cvs }, ... ]  僅營運中

popular_spots: list = []
# [ { lat, lon, fac_type, name }, ... ]


def load_all():
    """容器啟動時呼叫，載入所有靜態資料至記憶體"""
    _load_store_data()
    _load_popular_spots()
    print(f"✅ 記憶體查表載入完成：{len(store_locations)} 筆營運中店家 | {len(popular_spots)} 筆熱鬧據點")


def _load_store_data():
    df = pd.read_csv(FULL_DATA_PATH)

    # --- geo_tree ---
    for _, row in df[['縣市', '行政區', '里別']].drop_duplicates().iterrows():
        city, dist, nbhd = row['縣市'], row['行政區'], row['里別']
        geo_tree.setdefault(city, {}).setdefault(dist, set()).add(nbhd)
    for city in geo_tree:
        for dist in geo_tree[city]:
            geo_tree[city][dist] = sorted(geo_tree[city][dist])

    # --- neighborhood_lookup ---
    nbhd_cols = ['縣市', '行政區', '里別', '里人口數', '里人均收入中位數', '租金', '租金log']
    for _, row in df[nbhd_cols].drop_duplicates(subset=['縣市', '行政區', '里別']).iterrows():
        key = (row['縣市'], row['行政區'], row['里別'])
        neighborhood_lookup[key] = {
            '里人口數': int(row['里人口數']),
            '里人均收入中位數': int(row['里人均收入中位數']),
            '租金': float(row['租金']),
            '租金log': float(row['租金log']),
        }

    # --- district_lookup ---
    dist_cols = ['縣市', '行政區', '里別', '里人口數', '里人均收入中位數',
                 '行政區平日日間活動人數', '行政區平日夜間停留人數']
    dist_df = df[dist_cols].drop_duplicates(subset=['縣市', '行政區', '里別'])
    for (city, dist), grp in dist_df.groupby(['縣市', '行政區']):
        district_lookup[(city, dist)] = {
            '行政區平日日間活動人數': int(grp['行政區平日日間活動人數'].iloc[0]),
            '行政區平日夜間停留人數': int(grp['行政區平日夜間停留人數'].iloc[0]),
            '行政區人口': int(grp['里人口數'].sum()),
            '行政區收入中位數': int(grp['里人均收入中位數'].median()),
        }

    # --- prediction_lookup ---
    # CSV 欄位名 → 模型特徵名 對應
    col_map = {
        '歷史品牌優勢': '競爭優勢',
        '店均服務人口數': 'people_per_store',
        '區域競爭飽和度': '競爭壓力指標',
        '最近熱鬧據點類型': '最近的熱鬧據點類型',
        '最近熱鬧據點距離': '最近的熱鬧據點距離',
        '租金log': '租金_log',
    }
    csv_feature_cols = [
        '是否便利商店', '歷史品牌優勢', '店均服務人口數', '區域競爭飽和度',
        '里人均收入中位數', '發票銷售額指標', '行政區平日日間活動人數', '日夜人流差',
        '最近熱鬧據點類型', '最近熱鬧據點距離', '租金log', '里人口數', '發票張數指標',
        'id'
    ]
    meta_cols = ['公司名稱', '分公司名稱']
    for _, row in df[['縣市', '行政區', '里別'] + csv_feature_cols + meta_cols].iterrows():
        key = (row['縣市'], row['行政區'], row['里別'], int(row['是否便利商店']))
        entry = {}
        for col in csv_feature_cols:
            model_key = col_map.get(col, col)
            entry[model_key] = row[col]
        entry['_store_label'] = str(row['分公司名稱'])
        entry['_brand_name'] = COMPANY_TO_BRAND.get(str(row['公司名稱']), str(row['公司名稱']))
        if key not in prediction_lookup:
            prediction_lookup[key] = []
        prediction_lookup[key].append(entry)

    # --- store_locations（僅營運中） ---
    active = df[df['登記現況'] == '營運中'][['店_緯度', '店_經度', '是否便利商店', '公司名稱']].dropna()
    for _, row in active.iterrows():
        store_locations.append({
            'lat': float(row['店_緯度']),
            'lon': float(row['店_經度']),
            'is_cvs': int(row['是否便利商店']),
            'company': str(row['公司名稱']),
        })


def _load_popular_spots():
    df = pd.read_csv(POPULAR_LOCATIONS_PATH)
    df.columns = [c.lstrip('\ufeff') for c in df.columns]
    for _, row in df.iterrows():
        popular_spots.append({
            'lat': float(row['lat']),
            'lon': float(row['lon']),
            'fac_type': str(row['fac_type']),
            'name': str(row['facilities']),
        })
