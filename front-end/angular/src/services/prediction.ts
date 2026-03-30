import { BACK_END_URL, HEADERS } from "../common";
import { IPrediction, Prediction } from "../value-objects/prediction";
import { Operation } from "../value-objects/operation";
import { TotalPopulation } from "../value-objects/population";
import { MedianIncome } from "../value-objects/income";
import { Radar } from "../value-objects/radar";

export class PredictionService {
    private addressCache = new Map<string, IPrediction>();

    // 執行查表預測
    async runPrediction(city: string, district: string, neighborhood: string, brand: string, storeIndex: number = 0): Promise<IPrediction> {
        try {
            const url = `${BACK_END_URL}/run-prediction/${encodeURIComponent(city)}/${encodeURIComponent(district)}/${encodeURIComponent(neighborhood)}/${encodeURIComponent(brand)}?store_index=${storeIndex}`;
            const response = await fetch(url, { headers: HEADERS });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            return new Prediction(
                new Operation(data.operation.score, data.operation.report),
                new TotalPopulation(data.totalPopulation.neighborhood, data.totalPopulation.district),
                new MedianIncome(data.medianIncome.neighborhood, data.medianIncome.district),
                data.competitorCount,
                data.aiInsight,
                new Radar(data.radar.labels, data.radar.values),
                data.isSuccess,
                undefined,
                data.storeIndex,
                data.totalCount,
                data.storeLabel,
                data.brandName,
            );
        } catch (error) {
            console.error("無法執行預測:", error);
            return new Prediction(new Operation(0, ""), new TotalPopulation(0, 0), new MedianIncome(0, 0), 0, "", new Radar([], []), false);
        }
    }

    // 即時地址查詢
    async runPredictionByAddress(address: string, brand_name: string): Promise<IPrediction> {
        const cacheKey = `${address}__${brand_name}`;
        if (this.addressCache.has(cacheKey)) {
            return this.addressCache.get(cacheKey)!;
        }
        try {
            const response = await fetch(`${BACK_END_URL}/predict-by-address`, {
                method: 'POST',
                headers: { ...HEADERS, 'Content-Type': 'application/json' },
                body: JSON.stringify({ address, brand_name }),
            });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            const result = new Prediction(
                new Operation(data.operation.score, data.operation.report),
                new TotalPopulation(data.totalPopulation.neighborhood, data.totalPopulation.district),
                new MedianIncome(data.medianIncome.neighborhood, data.medianIncome.district),
                data.competitorCount,
                data.aiInsight,
                new Radar(data.radar.labels, data.radar.values),
                data.isSuccess,
                data.location
            );
            this.addressCache.set(cacheKey, result);
            return result;
        } catch (error) {
            console.error("無法執行地址預測:", error);
            return new Prediction(new Operation(0, ""), new TotalPopulation(0, 0), new MedianIncome(0, 0), 0, "", new Radar([], []), false);
        }
    }

    // AI 洞察串流（方案 C）
    streamAiInsight(
        city: string, district: string, neighborhood: string, brand: string,
        onChunk: (text: string, isFirst: boolean) => void,
        storeIndex: number = 0
    ): void {
        const url = `${BACK_END_URL}/ai-insight/${encodeURIComponent(city)}/${encodeURIComponent(district)}/${encodeURIComponent(neighborhood)}/${encodeURIComponent(brand)}?store_index=${storeIndex}`;
        fetch(url, { headers: HEADERS }).then(response => {
            const reader = response.body!.getReader();
            const decoder = new TextDecoder();
            let isFirst = true;
            const read = () => {
                reader.read().then(({ done, value }) => {
                    if (done) return;
                    const text = decoder.decode(value);
                    text.split('\n').forEach(line => {
                        if (line.startsWith('data: ')) {
                            const chunk = line.slice(6);
                            if (chunk === '[DONE]' || chunk.startsWith('[ERROR]')) return;
                            onChunk(chunk, isFirst);
                            isFirst = false;
                        }
                    });
                    read();
                }).catch(() => {});
            };
            read();
        }).catch(err => console.error("AI 洞察串流錯誤:", err));
    }
}