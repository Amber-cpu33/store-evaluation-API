# -*- coding: utf-8 -*-
from typing import AsyncGenerator
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from config import GEMINI_API_KEY


def _build_prompt(city: str, district: str, neighborhood: str, brand_type: str,
                  population: int, income: int, score: float, report: str,
                  top1_feature: str, top1_dir: str,
                  top2_feature: str, top2_dir: str) -> str:
    return (
        f"你是一位精通雙北零售市場的資深顧問。請根據以下數據提供 60 字內中文評語。\n"
        f"【位點數據】：\n"
        f"- 縣市：{city}\n"
        f"- 位置：{district}{neighborhood}\n"
        f"- 區域人口：{population} 人 / 收入中位數：{income} 千元\n"
        f"- 業態：{brand_type}\n"
        f"- 預測分數：{score:.1f} (決策：{report})\n"
        f"- 影響指標 1：{top1_feature} ({top1_dir})\n"
        f"- 影響指標 2：{top2_feature} ({top2_dir})\n\n"
        f"【分析邏輯與顧問語氣準則】：\n"
        f"0. 絕對規模判定：若里人口數 < 2000，無論收入多高，優先判定為『商圈規模小，基礎客源支撐力不足』，此時不適用強勢商圈保護邏輯。"
        f"1. 體質防禦：新北市(人口>4800/收入>510k)或台北市(人口>5500/收入>670k)符合任一則判定為強勢商圈，禁止說體質差。\n"
        f"2. 專業轉化：將'核心據點距離優異'轉化為'位處人流聚集核心'；'租金壓力優異'轉化為'具備展店成本優勢'；'市占/飽和度弱'轉化為'品牌進入門檻顯著'。\n"
        f"3. 歸因策略：若分數低但體質強，應解讀為'市場競爭飽和'。若兩者皆低，則解讀為'基礎客源門檻未達'。\n"
        f"4. 市場規模補償：若人口 > 10,000 且分數低(<40)，絕不可否定商圈，必須解讀為'市場雖極具誘力，但品牌面臨飽和競爭或進入門檻限制'。\n"
        f"5. 藍海判定：若分數高(>60)且市占率弱，應解讀為'具備高度開發潛力之藍海商圈'。\n"
        f"\n【顧問語氣強度控制規則】：\n"
        f"6. 業態門檻感知：\n"
        f"   - 若為「便利商店」(門檻 50)：50-60 分應定位為『險勝』，語氣保守；60-80 分為『優質』，語氣正向；80 分以上為『極佳』。\n"
        f"   - 若為「超市及藥妝」(門檻 70)：70-75 分應定位為『險勝』，語氣保守且需強調成本控制；75-85 分為『優質』；85 分以上為『極佳』。\n"
        f"7. 針對「險勝」區間（如超市 71.9 分）：禁止使用『極力推薦』、『高潛力』，改用『具備基礎條件』、『建議審慎評估成本』。\n"
        f"8. 以'該位點...'開頭，禁提品牌與登記狀態，字數嚴控 60 字內。"
    )


async def stream_ai_insight(
    city: str, district: str, neighborhood: str, brand_type: str,
    population: int, income: int, score: float, report: str,
    top1_feature: str, top1_dir: str,
    top2_feature: str, top2_dir: str
) -> AsyncGenerator[str, None]:
    """
    Streaming 輸出 AI 洞察（方案 C）
    以 async generator 逐 chunk yield 文字
    """
    llm = ChatGoogleGenerativeAI(
        model='gemini-2.5-flash',
        google_api_key=GEMINI_API_KEY,
        streaming=True,
    )
    prompt = _build_prompt(city, district, neighborhood, brand_type,
                           population, income, score, report,
                           top1_feature, top1_dir, top2_feature, top2_dir)
    async for chunk in llm.astream([HumanMessage(content=prompt)]):
        if chunk.content:
            yield chunk.content


async def get_ai_insight(
    city: str, district: str, neighborhood: str, brand_type: str,
    population: int, income: int, score: float, report: str,
    top1_feature: str, top1_dir: str,
    top2_feature: str, top2_dir: str
) -> str:
    """一次性回傳完整 AI 洞察（用於需要完整文字的場景）"""
    result = ""
    async for chunk in stream_ai_insight(
        city, district, neighborhood, brand_type,
        population, income, score, report,
        top1_feature, top1_dir, top2_feature, top2_dir
    ):
        result += chunk
    return result
