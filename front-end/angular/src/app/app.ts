import { Component, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SiteAnalyzerComponent } from './site-analyzer/site-analyzer';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, SiteAnalyzerComponent],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected readonly title = signal('angular');
}
