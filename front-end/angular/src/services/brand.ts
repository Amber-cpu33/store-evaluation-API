import { BACK_END_URL, HEADERS } from "../common";

export class BrandService {
    // 取得所有品牌列表（便利商店 / 超市及藥妝）
    async getBrandList(): Promise<string[]> {
        try {
            const response = await fetch(`${BACK_END_URL}/brands`, { headers: HEADERS });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error("無法取得品牌列表:", error);
            return [];
        }
    }

    // 依類型取得具體品牌名稱（地址模式用）
    async getBrandsByType(brandType: string): Promise<string[]> {
        try {
            const response = await fetch(`${BACK_END_URL}/brands-by-type/${encodeURIComponent(brandType)}`, { headers: HEADERS });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error("無法取得品牌列表:", error);
            return [];
        }
    }
}