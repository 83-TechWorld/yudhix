import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService, errorMessage } from '../../core/api.service';
import { Video } from '../../core/models';
import { IconComponent } from '../../shared/icon.component';
import { CompactPipe, EmptyStateComponent, PctPipe, RingComponent, SentimentBarComponent } from '../../shared/ui';

type Filter = 'all' | 'disputed' | 'accurate';

@Component({
  selector: 'y-videos',
  imports: [FormsModule, RouterLink, IconComponent, RingComponent, SentimentBarComponent, EmptyStateComponent, CompactPipe, PctPipe],
  template: `
    <div class="page">
      <header class="page-head">
        <div>
          <h1>Videos</h1>
          <p>Every analyzed video, with how accurate it is and how the audience reacted.</p>
        </div>
        <a class="btn btn-primary" routerLink="/analyze"><y-icon name="plus" /> Analyze a video</a>
      </header>

      <div class="toolbar">
        <div class="search grow">
          <y-icon name="search" />
          <input class="input" [ngModel]="q()" (ngModelChange)="q.set($event)" placeholder="Search title or channel" aria-label="Search videos" />
        </div>
        <div class="segmented" role="tablist">
          <button type="button" [class.active]="filter() === 'all'" (click)="filter.set('all')">All <span class="count">{{ videos()?.length ?? 0 }}</span></button>
          <button type="button" [class.active]="filter() === 'disputed'" (click)="filter.set('disputed')">Has disputed claims <span class="count">{{ disputedCount() }}</span></button>
          <button type="button" [class.active]="filter() === 'accurate'" (click)="filter.set('accurate')">Accurate</button>
        </div>
      </div>

      @if (error()) {
        <div class="callout callout-danger">{{ error() }}</div>
      } @else if (videos() === null) {
        <div class="grid-3">@for (i of [1, 2, 3, 4, 5, 6]; track i) { <div class="skeleton" style="height: 300px"></div> }</div>
      } @else if (shown().length === 0) {
        <div class="card"><y-empty icon="video" title="No matching videos" text="Try another filter, or analyze a new video." /></div>
      } @else {
        <div class="grid-3">
          @for (v of shown(); track v.id; let i = $index) {
            <a class="card card-interactive video enter" [style.--i]="i" [routerLink]="['/videos', v.videoId]">
              <div class="thumb-wrap">
                <img class="thumb" [src]="v.thumbnailUrl" alt="" loading="lazy" />
                @if (v.misleadingClaims) {
                  <span class="chip chip-warn overlay"><y-icon name="alert" [size]="13" />{{ v.misleadingClaims }} disputed</span>
                }
              </div>
              <div class="video-body">
                <div class="row top">
                  <div class="titles">
                    <strong class="clamp-2">{{ v.title }}</strong>
                    <span class="subtle truncate">{{ v.channel }}@if (v.publishedDate) { · {{ v.publishedDate }} }</span>
                  </div>
                  <y-ring [value]="v.factualAccuracy" [size]="50" label="Factual accuracy" />
                </div>
                <div class="facts subtle">
                  <span>{{ v.totalClaims }} claims</span>
                  <span>{{ v.comments | compact }} comments</span>
                  @if (v.comments) { <span>{{ v.linkedComments / v.comments | pct }} traced to a claim</span> }
                </div>
                @if (v.comments) {
                  <y-sentiment-bar [positive]="v.positiveComments" [negative]="v.negativeComments"
                    [neutral]="v.comments - v.positiveComments - v.negativeComments" />
                }
              </div>
            </a>
          }
        </div>
      }
    </div>
  `,
  styles: `
    .toolbar { display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; align-items: center; }
    .grow { flex: 1; min-width: 220px; }
    .video { display: flex; flex-direction: column; overflow: hidden; color: var(--text); text-decoration: none; }
    .video:hover { text-decoration: none; }
    .thumb-wrap { position: relative; padding: 10px 10px 0; }
    .thumb { transition: transform .4s var(--ease-out); }
    .thumb-wrap { overflow: hidden; border-radius: 12px; }
    @media (hover: hover) { .video:hover .thumb { transform: scale(1.03); } }
    .overlay { position: absolute; left: 20px; top: 20px; box-shadow: var(--shadow); }
    .video-body { padding: 12px 16px 16px; display: flex; flex-direction: column; gap: 10px; }
    .top { align-items: flex-start; }
    .titles { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
    .facts { display: flex; gap: 12px; flex-wrap: wrap; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class VideosPage {
  private api = inject(ApiService);
  protected readonly videos = signal<Video[] | null>(null);
  protected readonly error = signal('');
  protected readonly q = signal('');
  protected readonly filter = signal<Filter>('all');

  protected readonly disputedCount = computed(() => (this.videos() ?? []).filter((v) => v.misleadingClaims > 0).length);
  protected readonly shown = computed(() => {
    const q = this.q().trim().toLowerCase();
    return (this.videos() ?? []).filter((v) => {
      if (this.filter() === 'disputed' && !v.misleadingClaims) return false;
      if (this.filter() === 'accurate' && v.misleadingClaims) return false;
      return !q || v.title.toLowerCase().includes(q) || v.channel.toLowerCase().includes(q);
    });
  });

  constructor() {
    this.api.videos().subscribe({
      next: (r) => this.videos.set(r.videos),
      error: (e) => this.error.set(errorMessage(e)),
    });
  }
}
