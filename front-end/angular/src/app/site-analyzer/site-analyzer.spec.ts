import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SiteAnalyzerComponent } from './site-analyzer';

describe('SiteAnalyzerComponent', () => {
  let component: SiteAnalyzerComponent;
  let fixture: ComponentFixture<SiteAnalyzerComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SiteAnalyzerComponent]
    })
      .compileComponents();

    fixture = TestBed.createComponent(SiteAnalyzerComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
