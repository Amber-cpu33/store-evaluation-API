# -*- coding: utf-8 -*-
import math
from data import loader


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """回傳兩座標間距離（公尺）"""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_nearest_store(lat: float, lon: float) -> dict:
    """回傳最近競店距離（公尺）"""
    min_dist = float('inf')
    for s in loader.store_locations:
        d = haversine(lat, lon, s['lat'], s['lon'])
        if d < min_dist:
            min_dist = d
    return {'最近鄰店距離': round(min_dist, 2)}


def get_nearest_popular_spot(lat: float, lon: float) -> dict:
    """回傳最近熱鬧據點距離（公尺）與類型"""
    min_dist = float('inf')
    nearest_type = ''
    for s in loader.popular_spots:
        d = haversine(lat, lon, s['lat'], s['lon'])
        if d < min_dist:
            min_dist = d
            nearest_type = s['fac_type']
    return {
        '最近熱鬧據點距離': round(min_dist, 2),
        '最近熱鬧據點類型': nearest_type,
    }


def count_stores_within_500m(lat: float, lon: float, company_name: str, is_cvs: int) -> dict:
    """
    回傳 500m 內的同品牌展店數與同類型競爭店數
    - 展店：公司名稱相同（同品牌）
    - 競爭：同類型（同為CVS或同為超市藥妝）但不同品牌
    """
    same_brand, other_same_type = 0, 0
    for s in loader.store_locations:
        if haversine(lat, lon, s['lat'], s['lon']) <= 500:
            if s['company'] == company_name:
                same_brand += 1
            elif s['is_cvs'] == is_cvs:
                other_same_type += 1
    return {
        '500m歷史展店': same_brand,
        '500m歷史競爭': other_same_type,
    }
