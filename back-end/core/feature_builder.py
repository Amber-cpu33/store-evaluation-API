# -*- coding: utf-8 -*-
import numpy as np
from data import loader
from core.geocoding import address_to_coords, coords_to_village
from core.distance import get_nearest_store, get_nearest_popular_spot, count_stores_within_500m


async def build_features_from_address(address: str, is_cvs: int, company_name: str) -> dict:
    """
    地址 → 完整特徵值 dict（供 predictor.predict 使用）
    流程：地址 → 座標 → 里別 → 查表 + 距離計算
    """
    # 1. 地址 → 座標
    lat, lon = await address_to_coords(address)

    # 2. 座標 → 縣市/行政區/里別（國土測繪 API）
    village_info = await coords_to_village(lat, lon)
    city = village_info['縣市']
    district = village_info['行政區']
    neighborhood = village_info['里別']

    # 3. 查里別靜態資料
    nbhd_data = loader.neighborhood_lookup.get((city, district, neighborhood), {})
    dist_data = loader.district_lookup.get((city, district), {})

    # 4. 距離計算（記憶體內）
    nearest_store = get_nearest_store(lat, lon)
    nearest_spot = get_nearest_popular_spot(lat, lon)
    stores_500m = count_stores_within_500m(lat, lon, company_name, is_cvs)

    # 5. 衍生特徵
    day_flow = dist_data.get('行政區平日日間活動人數', 0)
    night_flow = dist_data.get('行政區平日夜間停留人數', 0)
    day_night_diff = day_flow - night_flow
    rent = nbhd_data.get('租金', 0)
    rent_log = float(np.log1p(rent)) if rent else 0.0
    population = nbhd_data.get('里人口數', 0)
    income = nbhd_data.get('里人均收入中位數', 0)

    # 競爭衍生
    total_500m = stores_500m['500m歷史展店'] + stores_500m['500m歷史競爭']
    people_per_store = population / max(total_500m, 1)
    competition_advantage = stores_500m['500m歷史展店'] / max(total_500m, 1)
    competition_pressure = total_500m / max(population / 1000, 1)
    competitor_count = total_500m  # 500m 內同類型競店總數（含同品牌）

    return {
        # 回應用元資料（非模型特徵）
        '_competitor_count': competitor_count,
        # 模型特徵
        '是否便利商店': is_cvs,
        '競爭優勢': round(competition_advantage, 4),
        'people_per_store': round(people_per_store, 2),
        '競爭壓力指標': round(competition_pressure, 4),
        '里人均收入中位數': income,
        '發票銷售額指標': 0,   # 即時查詢無法取得，填 0
        '行政區平日日間活動人數': day_flow,
        '日夜人流差': day_night_diff,
        '最近的熱鬧據點類型': nearest_spot['最近熱鬧據點類型'],
        '最近的熱鬧據點距離': nearest_spot['最近熱鬧據點距離'],
        '租金_log': rent_log,
        '里人口數': population,
        '發票張數指標': 0,     # 即時查詢無法取得，填 0
        # 回應用元資料
        '_city': city,
        '_district': district,
        '_neighborhood': neighborhood,
        '_lat': lat,
        '_lon': lon,
    }
