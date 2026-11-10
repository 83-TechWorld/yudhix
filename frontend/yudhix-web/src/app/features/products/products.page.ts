import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService, errorMessage } from '../../core/api.service';
import { Channel, ProductSummary } from '../../core/models';
import { IconComponent } from '../../shared/icon.component';
import { CompactPipe, EmptyStateComponent, ToastService } from '../../shared/ui';

/** Every product with its comments split by channel: YouTube comments and Amazon reviews. */
@Component({
  selector: 'y-products',
  imports: [RouterLink, IconComponent, CompactPipe, EmptyStateComponent],
  template: `
    <div class="page">
      <header class="page-head">
        <div>
          <h1>Products</h1>
          <p>What people say about each product, on YouTube and on Amazon.</p>
        </div>
        <a class="btn btn-primary" routerLink="/analyze"><y-icon name="plus" /> Add a video or listing</a>
      </header>

      <div class="legend" aria-hidden="true">
        <span><i style="background: var(--chart-neg)"></i>Negative</span>
        <span><i style="background: var(--chart-neu)"></i>Neutral</span>
        <span><i style="background: var(--chart-pos)"></i>Positive</span>
      </div>

      @if (items() === null) {
        <div class="grid">@for (i of [1, 2, 3, 4]; track i) { <div class="skeleton" style="height: 220px"></div> }</div>
      } @else if (!items()!.length) {
        <div class="card"><y-empty icon="layers" title="No products yet" text="Add your products in onboarding, then analyze videos and Amazon listings for them." /></div>
      } @else {
        <div class="grid">
          @for (p of items(); track p.id; let i = $index) {
            <a class="card card-pad card-lift product enter" [style.--i]="i" [routerLink]="['/products', p.id]">
              <div class="row-wrap head">
                <h3>{{ p.name }}</h3>
                @if (p.amazonRating) { <span class="chip chip-outline" title="Average Amazon rating">★ {{ p.amazonRating }}</span> }
              </div>
              @if (p.category) { <p class="subtle cat">{{ p.category }}</p> }
              @for (ch of channels; track ch) {
                @let c = p.channels[ch];
                <div class="ch">
                  <div class="row ch-label">
                    <y-icon [name]="ch === 'YOUTUBE' ? 'play' : 'card'" [size]="14" />
                    <strong>{{ c.label }}</strong>
                    <span class="subtle">{{ c.comments | compact }} {{ ch === 'AMAZON' ? 'reviews' : 'comments' }}</span>
                    <span class="spacer"></span>
                    @if (c.comments) { <span class="subtle num"><b class="neg">{{ pct(c.negativeShare) }}</b> neg · <b class="pos">{{ pct(c.positiveShare) }}</b> pos</span> }
                  </div>
                  @if (c.comments) {
                    <div class="bar" role="img" [attr.aria-label]="c.label + ': ' + pct(c.negativeShare) + ' negative, ' + pct(c.positiveShare) + ' positive'">
                      @if (c.sentiment.negative) { <span [style.flex-grow]="c.sentiment.negative" style="background: var(--chart-neg)"></span> }
                      @if (c.sentiment.neutral) { <span [style.flex-grow]="c.sentiment.neutral" style="background: var(--chart-neu)"></span> }
                      @if (c.sentiment.positive) { <span [style.flex-grow]="c.sentiment.positive" style="background: var(--chart-pos)"></span> }
                    </div>
                  } @else {
                    <div class="bar empty"><span class="subtle">{{ ch === 'AMAZON' ? 'No Amazon listing yet' : 'No videos yet' }}</span></div>
                  }
                </div>
              }
              <p class="subtle foot">{{ p.videos }} video{{ p.videos === 1 ? '' : 's' }} · {{ p.listings }} Amazon listing{{ p.listings === 1 ? '' : 's' }}</p>
            </a>
          }
        </div>
      }
    </div>
  `,
  styles: `
    .legend { display: flex; gap: 16px; font-size: 12px; color: var(--muted-text); margin: -4px 0 14px;
      span { display: inline-flex; align-items: center; gap: 6px; } i { width: 10px; height: 10px; border-radius: 3px; display: inline-block; } }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; }
    .product { display: flex; flex-direction: column; gap: 12px; color: var(--text); text-decoration: none; }
    .head { gap: 8px; h3 { margin: 0; font-size: 16px; flex: 1; } }
    .cat { margin: -8px 0 0; font-size: 13px; }
    .ch { display: flex; flex-direction: column; gap: 6px; }
    .ch-label { gap: 6px; font-size: 13px; y-icon { color: var(--muted-text); } .num { font-size: 12px; font-variant-numeric: tabular-nums; } }
    .neg, .pos { color: var(--text); }
    .bar { display: flex; gap: 2px; height: 12px; border-radius: 4px; overflow: hidden;
      span { display: block; min-width: 3px; flex-basis: 0; } }
    .bar.empty { background: var(--muted-soft); height: 22px; align-items: center; padding: 0 8px; font-size: 12px; border-radius: 6px; }
    .foot { font-size: 12.5px; margin: 0; }
    @media (max-width: 420px) { .grid { grid-template-columns: 1fr; } }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProductsPage {
  private api = inject(ApiService);
  private toast = inject(ToastService);
  protected readonly items = signal<ProductSummary[] | null>(null);
  protected readonly channels: Channel[] = ['YOUTUBE', 'AMAZON'];

  constructor() {
    this.api.catalogProducts().subscribe({
      next: (r) => this.items.set(r.products),
      error: (e) => {
        this.items.set([]);
        this.toast.error(errorMessage(e));
      },
    });
  }

  protected pct(share: number): string {
    return `${Math.round(share * 100)}%`;
  }
}
