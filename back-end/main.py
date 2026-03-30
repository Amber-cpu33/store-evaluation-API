# -*- coding: utf-8 -*-
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from data import loader
from core import predictor, geo
from core.feature_builder import build_features_from_address
from core.radar import compute_radar
from core import llm
from config import BRAND_MAP, CVS_BRANDS, SUPER_BRANDS

# ==========================================
# 啟動 / 關閉
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    loader.load_all()
    predictor.init_models()
    yield

app = FastAPI(lifespan=lifespan)
PREFIX = "/api"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# Geo / Brand 端點
# ==========================================

@app.get(PREFIX + "/cities")
async def get_cities():
    return geo.get_city_list()

@app.get(PREFIX + "/districts/{city}")
async def get_districts(city: str):
    return geo.get_district_list(city)

@app.get(PREFIX + "/neighborhoods/{city}/{district}")
async def get_neighborhoods(city: str, district: str):
    return geo.get_neighborhood_list(city, district)

@app.get(PREFIX + "/brands")
async def get_brands():
    return ["便利商店", "超市及藥妝"]

@app.get(PREFIX + "/brands-by-type/{brand_type}")
async def get_brands_by_type(brand_type: str):
    if brand_type == "便利商店":
        return CVS_BRANDS
    elif brand_type == "超市及藥妝":
        return SUPER_BRANDS
    raise HTTPException(status_code=400, detail="brand_type 必須為 便利商店 或 超市及藥妝")

@app.get(PREFIX + "/geo-check/{city}/{district}/{neighborhood}")
async def geo_check(city: str, district: str, neighborhood: str):
    return {"is_valid": geo.check_valid_geo(city, district, neighborhood)}

# ==========================================
# 查表預測端點
# ==========================================

@app.get(PREFIX + "/run-prediction/{city}/{district}/{neighborhood}/{brand}")
async def run_prediction(city: str, district: str, neighborhood: str, brand: str, store_index: int = 0):
    is_cvs = 1 if brand == "便利商店" else 0
    key = (city, district, neighborhood, is_cvs)

    if key not in loader.prediction_lookup:
        raise HTTPException(status_code=404, detail=f"查無位置資料：{city}{district}{neighborhood}（{brand}）")

    store_list = loader.prediction_lookup[key]
    total_count = len(store_list)
    store_index = max(0, min(store_index, total_count - 1))
    features = store_list[store_index]
    result = predictor.predict(features)
    score = result["score"]
    report = result["report"]

    # 人口 / 收入
    nbhd = loader.neighborhood_lookup.get((city, district, neighborhood), {})
    dist = loader.district_lookup.get((city, district), {})
    population = nbhd.get('里人口數', 0)
    income = nbhd.get('里人均收入中位數', 0)

    # 競店數 = 同里同類型店家總數
    competitor_count = total_count

    # Phase 3：雷達圖 & AI 洞察平行執行（方案 D）
    radar_task = asyncio.create_task(
        asyncio.to_thread(compute_radar, result["shap_values"], is_cvs)
    )

    brand_name = "便利商店" if is_cvs == 1 else "超市及藥妝"
    # AI 洞察串流由前端另行呼叫，此處回傳空字串
    radar = await radar_task

    return {
        "operation": {"score": score, "report": report},
        "totalPopulation": {"neighborhood": population, "district": dist.get('行政區人口', 0)},
        "medianIncome": {"neighborhood": income, "district": dist.get('行政區收入中位數', 0)},
        "competitorCount": competitor_count,
        "aiInsight": "",
        "radar": radar,
        "isSuccess": True,
        "storeIndex": store_index,
        "totalCount": total_count,
        "storeLabel": features.get('_store_label', ''),
        "brandName": features.get('_brand_name', brand_name),
    }

# ==========================================
# AI 洞察串流端點（方案 C）
# ==========================================

@app.get(PREFIX + "/ai-insight/{city}/{district}/{neighborhood}/{brand}")
async def ai_insight_stream(city: str, district: str, neighborhood: str, brand: str, store_index: int = 0):
    is_cvs = 1 if brand == "便利商店" else 0
    key = (city, district, neighborhood, is_cvs)

    if key not in loader.prediction_lookup:
        raise HTTPException(status_code=404, detail="查無位置資料")

    store_list = loader.prediction_lookup[key]
    store_index = max(0, min(store_index, len(store_list) - 1))
    features = store_list[store_index]
    result = predictor.predict(features)
    nbhd = loader.neighborhood_lookup.get((city, district, neighborhood), {})
    brand_type = "便利商店" if is_cvs == 1 else "超市及藥妝"

    async def event_stream():
        try:
            async for chunk in llm.stream_ai_insight(
                city=city, district=district, neighborhood=neighborhood,
                brand_type=brand_type,
                population=nbhd.get('里人口數', 0),
                income=nbhd.get('里人均收入中位數', 0),
                score=result["score"], report=result["report"],
                top1_feature=result["top1_feature"], top1_dir=result["top1_dir"],
                top2_feature=result["top2_feature"], top2_dir=result["top2_dir"],
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            import traceback
            print("❌ SSE error:", traceback.format_exc())
            yield f"data: [ERROR] {e}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

# ==========================================
# 即時地址查詢端點
# ==========================================

class AddressRequest(BaseModel):
    address: str
    brand_name: str  # 顯示名稱，例：全家、7-ELEVEN、全聯

@app.post(PREFIX + "/predict-by-address")
async def predict_by_address(req: AddressRequest):
    if req.brand_name not in BRAND_MAP:
        raise HTTPException(status_code=400, detail=f"未知品牌：{req.brand_name}")
    company_name, is_cvs = BRAND_MAP[req.brand_name]
    try:
        features = await build_features_from_address(req.address, is_cvs, company_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"特徵建構失敗：{str(e)}")

    result = predictor.predict(features)
    score = result["score"]
    report = result["report"]

    city = features.get('_city', '')
    district = features.get('_district', '')
    neighborhood = features.get('_neighborhood', '')

    dist_data = loader.district_lookup.get((city, district), {})
    brand_type = "便利商店" if is_cvs == 1 else "超市及藥妝"

    # Phase 3：雷達圖 & AI 洞察平行執行（方案 D）
    radar_task = asyncio.create_task(
        asyncio.to_thread(compute_radar, result["shap_values"], is_cvs)
    )
    ai_task = asyncio.create_task(
        llm.get_ai_insight(
            city=city, district=district, neighborhood=neighborhood,
            brand_type=brand_type,
            population=features.get('里人口數', 0),
            income=features.get('里人均收入中位數', 0),
            score=score, report=report,
            top1_feature=result["top1_feature"], top1_dir=result["top1_dir"],
            top2_feature=result["top2_feature"], top2_dir=result["top2_dir"],
        )
    )
    radar, ai_insight = await asyncio.gather(radar_task, ai_task)

    return {
        "operation": {"score": score, "report": report},
        "totalPopulation": {
            "neighborhood": features.get('里人口數', 0),
            "district": dist_data.get('行政區人口', 0),
        },
        "medianIncome": {
            "neighborhood": features.get('里人均收入中位數', 0),
            "district": dist_data.get('行政區收入中位數', 0),
        },
        "competitorCount": int(features.get('_competitor_count', 0)),
        "aiInsight": ai_insight,
        "radar": radar,
        "isSuccess": True,
        "location": {"city": city, "district": district, "neighborhood": neighborhood},
    }
