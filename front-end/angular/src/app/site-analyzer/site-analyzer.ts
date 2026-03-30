import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import Chart from 'chart.js/auto';

import { GeoService } from '../../services/geo';
import { BrandService } from '../../services/brand';
import { PredictionService } from '../../services/prediction';

import { IPrediction } from '../../value-objects/prediction';
import { Prediction } from '../../value-objects/prediction';
import { Operation } from '../../value-objects/operation';
import { TotalPopulation } from '../../value-objects/population';
import { MedianIncome } from '../../value-objects/income';
import { Radar } from '../../value-objects/radar';

@Component({
  selector: 'app-site-analyzer',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './site-analyzer.html',
  styleUrls: ['./site-analyzer.css']
})
export class SiteAnalyzerComponent implements OnInit {
  constructor(private cdr: ChangeDetectorRef) { }

  // 服務
  private geoService = new GeoService();
  private brandService = new BrandService();
  private predictionService = new PredictionService();

  // 表單綁定變數
  selectedCity: string = '';
  selectedDistrict: string = '';
  selectedNeighborhood: string = '';
  selectedBrand: string = '';

  // 城市下拉選單
  cities: string[] = [];
  // 行政區下拉選單
  districts: string[] = [];
  // 里別下拉選單
  neighborhoods: string[] = [];
  // 品牌下拉選單
  brands: string[] = [];

  // 狀態控制
  isLoading: boolean = false;
  showResult: boolean = false;
  queryMode: 'lookup' | 'address' = 'lookup';
  addressInput: string = '';
  aiInsightText: string = '';
  displayDistrict: string = '';
  displayNeighborhood: string = '';
  currentStoreIndex: number = 0;
  totalStoreCount: number = 1;
  currentStoreLabel: string = '';
  currentBrandName: string = '';
  brandNames: string[] = [];       // 地址模式用：具體品牌（全家、7-ELEVEN...）
  selectedBrandName: string = '';  // 地址模式選擇的品牌

  // 數據與圖表
  prediction: IPrediction = new Prediction(
    new Operation(0, ""),
    new TotalPopulation(0, 0),
    new MedianIncome(0, 0),
    0,
    '',
    new Radar([], []),
    false
  );

  private charts: any = {};

  async ngOnInit() {
    await this.SetDefault();
    this.cdr.detectChanges();
  }

  async SetDefault() {
    await this.updateCity();
    this.selectedCity = this.cities[0];
    await this.updateDistricts();
    this.selectedDistrict = this.districts[0];
    await this.updateNeighborhoods();
    this.selectedNeighborhood = this.neighborhoods[0];
    await this.updateBrands();
    this.selectedBrand = this.brands[0];
  }

  async updateCity() {
    this.selectedCity = '';
    this.selectedDistrict = '';
    this.selectedNeighborhood = '';
    this.cities = await this.geoService.getCityList();
    console.log("cities", this.cities);
  }

  async updateDistricts() {
    this.selectedDistrict = '';
    this.selectedNeighborhood = '';
    this.districts = await this.geoService.getDistrictList(this.selectedCity);
  }

  async updateNeighborhoods() {
    this.selectedNeighborhood = '';
    this.currentStoreIndex = 0;
    this.neighborhoods = await this.geoService.getNeighborhoodList(this.selectedCity, this.selectedDistrict);
  }

  async updateBrands() {
    this.brands = await this.brandService.getBrandList();
    if (!this.selectedBrand) this.selectedBrand = this.brands[0];
    await this.updateBrandNames();
  }

  async updateBrandNames() {
    this.brandNames = await this.brandService.getBrandsByType(this.selectedBrand);
    this.selectedBrandName = this.brandNames[0] ?? '';
  }

  async checkGeo() {
    return await this.geoService.checkValidGeo(this.selectedCity, this.selectedDistrict, this.selectedNeighborhood);
  }

  async runPrediction() {
    try {
      const isValidGeo = await this.checkGeo();
      if (!isValidGeo) {
        alert(`目前選擇的城市、行政區與里別為無效，請重新選擇`);
        return;
      }
      this.showResult = false;
      this.isLoading = true;
      this.aiInsightText = '分析中...';
      this.cdr.detectChanges();
      await this.generateResult();
      this.isLoading = false;
      this.showResult = true;
      this.cdr.detectChanges();
    } catch (error) {
      this.isLoading = false;
      this.showResult = false;
      console.error("無法執行預測:", error);
      alert("無法執行預測，請稍後再試");
    }
  }

  async switchStore(delta: number) {
    const newIndex = this.currentStoreIndex + delta;
    if (newIndex < 0 || newIndex >= this.totalStoreCount) return;
    this.currentStoreIndex = newIndex;
    this.isLoading = true;
    this.cdr.detectChanges();
    await this.generateResult();
    this.isLoading = false;
    this.showResult = true;
    this.cdr.detectChanges();
  }

  async generateResult() {
    this.aiInsightText = '分析中...';
    if (this.queryMode === 'address') {
      this.prediction = await this.predictionService.runPredictionByAddress(this.addressInput, this.selectedBrandName);
      if (!this.prediction.isSuccess) {
        alert(`無法取得地址「${this.addressInput}」的預測結果`);
        return;
      }
      this.displayDistrict = this.prediction.location?.district ?? '';
      this.displayNeighborhood = this.prediction.location?.neighborhood ?? '';
      this.currentBrandName = this.selectedBrandName;
      this.aiInsightText = this.prediction.aiInsight;
    } else {
      this.prediction = await this.predictionService.runPrediction(this.selectedCity, this.selectedDistrict, this.selectedNeighborhood, this.selectedBrand, this.currentStoreIndex);
      this.displayDistrict = this.selectedDistrict;
      this.displayNeighborhood = this.selectedNeighborhood;
      this.currentStoreIndex = this.prediction.storeIndex ?? 0;
      this.totalStoreCount = this.prediction.totalCount ?? 1;
      this.currentStoreLabel = this.prediction.storeLabel ?? '';
      this.currentBrandName = this.prediction.brandName ?? this.selectedBrand;
      if (!this.prediction.isSuccess) {
        alert(`${this.selectedCity} ${this.selectedDistrict} ${this.selectedNeighborhood} 無開設 ${this.selectedBrand} 紀錄`);
        return;
      }
      // 查表模式：串流 AI 洞察（方案 C）
      this.aiInsightText = 'AI洞察報告生成中......';
      this.predictionService.streamAiInsight(
        this.selectedCity, this.selectedDistrict, this.selectedNeighborhood, this.selectedBrand,
        (chunk, isFirst) => {
          if (isFirst) this.aiInsightText = chunk;
          else this.aiInsightText += chunk;
          this.cdr.detectChanges();
        },
        this.currentStoreIndex
      );
    }
    this.renderCharts();
  }

  getOperationClass() {
    if (this.selectedBrand === '便利商店') {
      if (this.prediction.operation.score >= 50) return { badge: 'bg-success', text: this.prediction.operation.report, color: '#198754' };
      return { badge: 'bg-danger', text: this.prediction.operation.report, color: '#dc3545' };
    } else {
      if (this.prediction.operation.score >= 70) return { badge: 'bg-success', text: this.prediction.operation.report, color: '#198754' };
      return { badge: 'bg-danger', text: this.prediction.operation.report, color: '#dc3545' };
    }
  }

  renderCharts() {
    const chartConfigs = [
      { id: 'popChart', type: 'bar' as const, data: [this.prediction.totalPopulation.neighborhood, this.prediction.totalPopulation.district], colors: ['#36A2EB', '#C8C8C8'], labels: [`${this.displayNeighborhood}人口數`, `${this.displayDistrict}人口數`] },
      { id: 'incomeChart', type: 'bar' as const, data: [this.prediction.medianIncome.neighborhood, this.prediction.medianIncome.district], colors: ['#4BC0C0', '#C8C8C8'], labels: [`${this.displayNeighborhood}收入中位數 (千元)`, `${this.displayDistrict}收入中位數 (千元)`] }
    ];

    chartConfigs.forEach(conf => {
      if (this.charts[conf.id]) this.charts[conf.id].destroy();
      const ctx = document.getElementById(conf.id) as HTMLCanvasElement;
      if (!ctx) return;
      this.charts[conf.id] = new Chart(ctx, {
        type: conf.type,
        data: {
          labels: conf.labels,
          datasets: [{ data: conf.data, backgroundColor: conf.colors, barThickness: 30 }]
        },
        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
      });
    });

    // 雷達圖
    if (this.charts['radarChart']) this.charts['radarChart'].destroy();
    const radarCtx = document.getElementById('radarChart') as HTMLCanvasElement;
    if (!radarCtx) return;
    this.charts['radarChart'] = new Chart(radarCtx, {
      type: 'radar',
      data: {
        labels: this.prediction.radar.labels,
        datasets: [{
          label: '選址評分維度',
          data: this.prediction.radar.values,
          backgroundColor: 'rgba(255, 99, 132, 0.2)',
          borderColor: 'rgb(255, 99, 132)'
        }]
      },
      options: { scales: { r: { suggestedMin: 0, suggestedMax: 5 } } }
    });
  }
}