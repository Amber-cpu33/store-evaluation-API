# -*- coding: utf-8 -*-
import httpx
import xml.etree.ElementTree as ET
from config import GOOGLE_MAPS_API_KEY


async def address_to_coords(address: str) -> tuple[float, float]:
    """
    地址 → (緯度, 經度)
    使用 Google Maps Geocoding API
    """
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": GOOGLE_MAPS_API_KEY, "language": "zh-TW"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    if data.get("status") != "OK" or not data.get("results"):
        raise ValueError(f"Geocoding 失敗：{data.get('status')} — {address}")
    loc = data["results"][0]["geometry"]["location"]
    return float(loc["lat"]), float(loc["lng"])


async def coords_to_village(lat: float, lon: float) -> dict:
    """
    座標 → 縣市 / 行政區 / 里別
    使用國土測繪免費 API（無需 API Key）
    GET https://api.nlsc.gov.tw/other/TownVillagePointQuery1/{經度}/{緯度}/4326
    """
    url = f"https://api.nlsc.gov.tw/other/TownVillagePointQuery1/{lon}/{lat}/4326"
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
    root = ET.fromstring(resp.text)
    return {
        '縣市': root.findtext('ctyName', ''),
        '行政區': root.findtext('townName', ''),
        '里別': root.findtext('villageName', ''),
    }
