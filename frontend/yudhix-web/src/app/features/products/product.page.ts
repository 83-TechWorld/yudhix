import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService, errorMessage } from '../../core/api.service';
import { Channel, Job, Listing, ProductComment, ProductOverview, Sentiment } from '../../core/models';
import { SessionService } from '../../core/session.service';
import { IconComponent } from '../../shared/icon.component';
import { AgoPipe, CompactPipe, ToastService } from '../../shared/ui';

type ChannelFilter = 'ALL' | Channel;

const SERIES = [
  { key: 'negative', label: 'Negative', color: 'var(--chart-neg)' },
  { key: 'neutral', label: 'Neutral', color: 'var(--chart-neu)' },
  { key: 'positive', label: 'Positive', color: 'var(--chart-pos)' },
] as const;

/**
 * One product across channels: sentiment by channel (YouTube vs Amazon), what each channel talks
 * about, the positive and negative voices from either channel, and the sources (videos, Amazon listings).
 */
@Component({
  selector: 'y-product',
  imports: [FormsModule, RouterLink, IconComponent, CompactPipe, AgoPipe],
  template: `
    <div class="page">
      <a routerLink="/products" class="back"><y-icon name="arrowLeft" [size]="16" /> Products</a>
      @if (error()) {
        <div class="callout callout-danger">{{ error() }}</div>
      } @else if (!data()) {
        <div class="skeleton" style="height: 160px; margin-bottom: 16px"></div><div class="skeleton" style="height: 320px"></div>
      } @else {
        @let d = data()!;
        <header class="page-head">
          <div>
            <span class="eyebrow">{{ d.category || 'Product' }}</span>
            <h1>{{ d.name }}</h1>
            <p>{{ d.headline }}</p>
          </div>
        </header>

        <!-- Totals -->
        <section class="grid-4 tiles">
          <div class="card stat"><div class="stat-label"><y-icon name="message" [size]="15" /> Comments and reviews</div><div class="stat-value">{{ d.totals.comments | compact }}</div>
            <div class="stat-note">{{ d.channels.YOUTUBE.comments | compact }} YouTube · {{ d.channels.AMAZON.comments | compact }} Amazon</div></div>
          <div class="card stat"><div class="stat-label"><y-icon name="thumbsUp" [size]="15" /> Positive</div><div class="stat-value">{{ d.totals.positive | compact }}</div>
            <div class="stat-note">{{ pct(d.totals.positive / (d.totals.comments || 1)) }} of all</div></div>
          <div class="card stat"><div class="stat-label"><y-icon name="alert" [size]="15" /> Negative</div><div class="stat-value">{{ d.totals.negative | compact }}</div>
            <div class="stat-note">{{ pct(d.totals.negative / (d.totals.comments || 1)) }} of all</div></div>
          <div class="card stat"><div class="stat-label"><y-icon name="card" [size]="15" /> Amazon rating</div>
            <div class="stat-value">{{ rating() ?? '–' }}@if (rating()) {<span class="of">/5</span>}</div>
            <div class="stat-note">{{ ratingsCount() ? (ratingsCount()! | compact) + ' ratings on Amazon' : 'Add a listing to see it' }}</div></div>
        </section>

        <!-- Sentiment by channel -->
        <section class="card card-pad block">
          <div class="row-wrap">
            <h2 class="grow">Sentiment by channel</h2>
            <div class="segmented" role="radiogroup" aria-label="Measure">
              <button type="button" role="radio" [attr.aria-checked]="!byReach()" [class.active]="!byReach()" (click)="byReach.set(false)">By count</button>
              <button type="button" role="radio" [attr.aria-checked]="byReach()" [class.active]="byReach()" (click)="byReach.set(true)">By reach</button>
            </div>
          </div>
          <div class="legend" aria-hidden="true">@for (s of series; track s.key) { <span><i [style.background]="s.color"></i>{{ s.label }}</span> }</div>
          @for (row of channelRows(); track row.channel) {
            <div class="crow">
              <div class="row clabel"><y-icon [name]="row.channel === 'YOUTUBE' ? 'play' : 'card'" [size]="15" /><strong>{{ row.label }}</strong>
                <span class="subtle">{{ row.comments | compact }} {{ row.channel === 'AMAZON' ? 'reviews' : 'comments' }}</span></div>
              @if (row.comments) {
                <div class="bar" role="img" [attr.aria-label]="row.label + ': ' + row.aria">
                  @for (s of row.segments; track s.key) {
                    @if (s.value) {
                      <span class="seg" tabindex="0" [style.flex-grow]="s.value" [style.background]="s.color"
                            [attr.title]="s.label + ': ' + pct(s.share) + ' (' + s.value + ')'"></span>
                    }
                  }
                </div>
                <div class="vals subtle">@for (s of row.segments; track s.key) { <span><b>{{ pct(s.share) }}</b> {{ s.label.toLowerCase() }}</span> }</div>
              } @else {
                <div class="bar empty"><span class="subtle">{{ row.channel === 'AMAZON' ? 'No reviews yet. Add the Amazon listing below.' : 'No YouTube comments yet. Analyze a video for this product.' }}</span></div>
              }
            </div>
          }
        </section>

        <!-- Topics per channel -->
        @if (d.channels.YOUTUBE.topics.length || d.channels.AMAZON.topics.length) {
          <section class="card card-pad block">
            <h2>What each channel talks about</h2>
            <div class="two">
              @for (row of channelRows(); track row.channel) {
                <div>
                  <h3 class="row"><y-icon [name]="row.channel === 'YOUTUBE' ? 'play' : 'card'" [size]="14" /> {{ row.label }}</h3>
                  @for (t of d.channels[row.channel].topics; track t.topic) {
                    <div class="topic">
                      <span class="tl">{{ t.label }}</span>
                      <div class="bar thin" [style.width.%]="(t.comments / maxTopic(row.channel)) * 100">
                        @if (t.negative) { <span [style.flex-grow]="t.negative" style="background: var(--chart-neg)"></span> }
                        @if (t.neutral) { <span [style.flex-grow]="t.neutral" style="background: var(--chart-neu)"></span> }
                        @if (t.positive) { <span [style.flex-grow]="t.positive" style="background: var(--chart-pos)"></span> }
                      </div>
                      <span class="tn subtle">{{ t.comments }}</span>
                    </div>
                  } @empty { <p class="subtle">No topics yet.</p> }
                </div>
              }
            </div>
          </section>
        }

        <!-- Voices: positive and negative, per channel -->
        <section class="block">
          <div class="row-wrap">
            <h2 class="grow">What people say</h2>
            <div class="segmented" role="radiogroup" aria-label="Channel">
              @for (c of channelFilters; track c.key) {
                <button type="button" role="radio" [attr.aria-checked]="channel() === c.key" [class.active]="channel() === c.key" (click)="setChannel(c.key)">{{ c.label }}</button>
              }
            </div>
          </div>
          <div class="voices">
            @for (col of columns; track col.sentiment) {
              <div class="card voice-col">
                <div class="voice-head row">
                  <i class="sw" [style.background]="col.color"></i><strong>{{ col.label }}</strong>
                  <span class="subtle">{{ voices()[col.sentiment].total | compact }}</span>
                </div>
                @for (c of voices()[col.sentiment].items; track c.id) {
                  <article class="voice">
                    <div class="row-wrap meta">
                      @if (c.channel === 'AMAZON') {
                        <span class="chip chip-outline"><y-icon name="card" [size]="12" /> Amazon</span>
                        @if (c.rating) { <span class="stars" [attr.aria-label]="c.rating + ' out of 5 stars'">{{ stars(c.rating) }}</span> }
                        @if (c.verified) { <span class="subtle">Verified purchase</span> }
                      } @else {
                        <span class="chip chip-outline"><y-icon name="play" [size]="12" /> YouTube</span>
                      }
                      @if (c.isNew) { <span class="chip chip-brand">New</span> }
                    </div>
                    <p class="clamp-3">{{ c.text }}</p>
                    <div class="row-wrap subtle foot">
                      <span><y-icon name="thumbsUp" [size]="12" /> {{ c.likes | compact }}{{ c.channel === 'AMAZON' ? ' helpful' : '' }}</span>
                      @if (c.createdAt) { <span>· {{ c.createdAt | ago }}</span> }
                      @if (c.source) {
                        <span class="src">·
                          @if (c.channel === 'YOUTUBE' && c.sourceId) { <a [routerLink]="['/videos', c.sourceId]">{{ c.source }}</a> }
                          @else if (c.url) { <a [href]="c.url" target="_blank" rel="noopener">{{ c.source }}</a> }
                          @else { {{ c.source }} }
                        </span>
                      }
                      <span class="spacer"></span>
                      <a class="btn btn-sm btn-ghost" routerLink="/inbox" [queryParams]="{ comment: c.id }">Respond</a>
                    </div>
                  </article>
                } @empty {
                  <p class="subtle empty-col">No {{ col.label.toLowerCase() }} comments {{ channel() === 'ALL' ? '' : 'on ' + channelLabel() }} yet.</p>
                }
                @if (voices()[col.sentiment].items.length < voices()[col.sentiment].total) {
                  <button class="btn btn-sm more" type="button" (click)="more(col.sentiment)">Show more</button>
                }
              </div>
            }
          </div>
        </section>

        <!-- Sources -->
        <section class="card card-pad block">
          <h2>Sources</h2>
          <div class="two">
            <div>
              <h3 class="row"><y-icon name="play" [size]="14" /> YouTube videos</h3>
              @for (v of d.videos; track v.videoId) {
                <a class="src-row" [routerLink]="['/videos', v.videoId]">
                  <img [src]="v.thumbnailUrl" alt="" />
                  <span class="grow"><strong class="clamp-2">{{ v.title || v.videoId }}</strong><span class="subtle">{{ v.channel }} · {{ v.comments | compact }} comments</span></span>
                </a>
              } @empty { <p class="subtle">No videos yet. <a routerLink="/analyze">Analyze one</a>.</p> }
            </div>
            <div>
              <h3 class="row"><y-icon name="card" [size]="14" /> Amazon listings</h3>
              @for (l of d.listings; track l.id) {
                <div class="src-row">
                  @if (l.imageUrl) { <img class="contain" [src]="l.imageUrl" alt="" /> } @else { <span class="ph"><y-icon name="card" [size]="18" /></span> }
                  <span class="grow">
                    <a [href]="l.url" target="_blank" rel="noopener"><strong class="clamp-2">{{ l.title || l.asin }}</strong></a>
                    <span class="subtle">{{ l.marketplace }} · @if (l.rating) { ★ {{ l.rating }} · } {{ l.reviewsStored }} reviews stored
                      @if (l.checkedAt) { · checked {{ l.checkedAt | ago }} }</span>
                    @if (l.status === 'BLOCKED' || l.status === 'FAILED') { <span class="err">{{ l.lastError }}</span> }
                  </span>
                  @if (session.can('content.write')) {
                    <button class="btn btn-sm" type="button" (click)="checkListing(l)" [disabled]="!!running()">
                      <y-icon name="refresh" [size]="14" [class.spin]="running()?.videoId === l.asin" /> {{ running()?.videoId === l.asin ? (running()!.message || 'Checking…') : 'Check now' }}
                    </button>
                    <button class="btn btn-sm btn-ghost btn-icon" type="button" (click)="removeListing(l)" [attr.aria-label]="'Stop tracking ' + (l.title || l.asin)"><y-icon name="trash" [size]="15" /></button>
                  }
                </div>
              }
              @if (session.can('content.write')) {
                <form class="add" (ngSubmit)="addListing()">
                  <input class="input" name="amz" [(ngModel)]="newUrl" placeholder="Paste an Amazon product link" aria-label="Amazon product link" />
                  <button class="btn btn-primary btn-sm" type="submit" [disabled]="!!running() || !newUrl.trim()">Add listing</button>
                </form>
                <p class="subtle hint">Reviews are checked again on the workspace schedule (Settings → Workspace).</p>
              }
            </div>
          </div>
        </section>
      }
    </div>
  `,
  styles: `
    .back { display: inline-flex; align-items: center; gap: 6px; margin-bottom: 12px; color: var(--muted-text); }
    .tiles { margin-bottom: 16px; }
    .of { font-size: 16px; color: var(--muted-text); margin-left: 2px; }
    .block { margin-bottom: 16px; display: flex; flex-direction: column; gap: 14px; h2 { margin: 0; font-size: 16px; } }
    .grow { flex: 1; min-width: 0; }
    .legend { display: flex; gap: 16px; font-size: 12px; color: var(--muted-text); margin-top: -4px;
      span { display: inline-flex; align-items: center; gap: 6px; } i { width: 10px; height: 10px; border-radius: 3px; display: inline-block; } }
    .crow { display: flex; flex-direction: column; gap: 6px; }
    .clabel { gap: 8px; font-size: 14px; y-icon { color: var(--muted-text); } }
    .bar { display: flex; gap: 2px; height: 16px; border-radius: 4px; overflow: hidden;
      span { display: block; min-width: 3px; flex-basis: 0; } .seg:hover, .seg:focus-visible { filter: brightness(1.12); } }
    .bar.thin { height: 10px; min-width: 6px; }
    .bar.empty { background: var(--muted-soft); height: 30px; align-items: center; padding: 0 10px; font-size: 12.5px; border-radius: 6px; }
    .vals { display: flex; gap: 14px; font-size: 12px; b { color: var(--text); } }
    .two { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 28px;
      h3 { font-size: 14px; margin: 0 0 10px; gap: 6px; } }
    .topic { display: grid; grid-template-columns: 150px minmax(0, 1fr) 36px; gap: 10px; align-items: center; font-size: 13px; margin-bottom: 8px;
      .tl { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } .tn { text-align: right; font-size: 12px; } }
    .voices { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
    .voice-col { padding: 6px 18px 14px; display: flex; flex-direction: column; }
    .voice-head { gap: 8px; padding: 12px 0; border-bottom: 1px solid var(--border); font-size: 14px; }
    .sw { width: 10px; height: 10px; border-radius: 3px; display: inline-block; }
    .voice { padding: 12px 0; border-bottom: 1px solid var(--border);
      p { margin: 6px 0; font-size: 14px; line-height: 1.5; }
      .meta { gap: 6px; font-size: 12px; } .foot { font-size: 12px; gap: 4px; align-items: center; } }
    .stars { color: var(--warn); letter-spacing: 1px; font-size: 13px; }
    .src { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 260px; }
    .empty-col { padding: 16px 0; }
    .more { align-self: center; margin-top: 10px; }
    .src-row { display: flex; gap: 12px; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border); color: var(--text); text-decoration: none;
      img { width: 96px; height: 54px; object-fit: cover; border-radius: 8px; flex: none; background: var(--muted-soft); }
      img.contain { object-fit: contain; background: #fff; }
      .grow { display: flex; flex-direction: column; gap: 2px; font-size: 13.5px; } .subtle { font-size: 12px; }
      .err { font-size: 12px; color: var(--danger-text); } }
    .ph { width: 96px; height: 54px; border-radius: 8px; background: var(--muted-soft); display: grid; place-items: center; flex: none; }
    .add { display: flex; gap: 8px; margin-top: 12px; .input { flex: 1; } }
    .hint { font-size: 12px; margin: 6px 0 0; }
    @media (max-width: 900px) { .two, .voices { grid-template-columns: 1fr; } }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProductPage {
  private api = inject(ApiService);
  private toast = inject(ToastService);
  protected session = inject(SessionService);

  readonly productId = input.required<string>();
  /** ?channel=AMAZON|YOUTUBE preselects the channel filter. */
  readonly channelParam = input<string | undefined>(undefined, { alias: 'channel' });

  protected readonly series = SERIES;
  protected readonly channelFilters: { key: ChannelFilter; label: string }[] = [
    { key: 'ALL', label: 'All channels' }, { key: 'YOUTUBE', label: 'YouTube' }, { key: 'AMAZON', label: 'Amazon' },
  ];
  protected readonly columns: { sentiment: Sentiment; label: string; color: string }[] = [
    { sentiment: 'POSITIVE', label: 'Positive', color: 'var(--chart-pos)' },
    { sentiment: 'NEGATIVE', label: 'Negative', color: 'var(--chart-neg)' },
  ];

  protected readonly data = signal<ProductOverview | null>(null);
  protected readonly error = signal('');
  protected readonly byReach = signal(false);
  protected readonly channel = signal<ChannelFilter>('ALL');
  protected readonly voices = signal<Record<string, { items: ProductComment[]; total: number }>>({
    POSITIVE: { items: [], total: 0 }, NEGATIVE: { items: [], total: 0 },
  });
  protected readonly running = signal<Job | null>(null);
  protected newUrl = '';
  private timer: ReturnType<typeof setTimeout> | null = null;

  protected readonly rating = computed(() => {
    const r = (this.data()?.listings ?? []).map((l) => l.rating).filter((x): x is number => x !== null);
    return r.length ? Math.round((r.reduce((a, b) => a + b, 0) / r.length) * 10) / 10 : null;
  });
  protected readonly ratingsCount = computed(() => (this.data()?.listings ?? []).reduce((n, l) => n + (l.ratingsCount ?? 0), 0) || null);
  protected readonly channelLabel = computed(() => (this.channel() === 'AMAZON' ? 'Amazon' : 'YouTube'));

  protected readonly channelRows = computed(() => {
    const d = this.data();
    if (!d) return [];
    return (['YOUTUBE', 'AMAZON'] as Channel[]).map((ch) => {
      const c = d.channels[ch];
      const split = this.byReach() ? c.sentimentByReach : c.sentiment;
      const total = split.positive + split.neutral + split.negative || 1;
      const segments = SERIES.map((s) => ({ ...s, value: split[s.key], share: split[s.key] / total }));
      return { channel: ch, label: c.label, comments: c.comments, segments,
               aria: segments.map((s) => `${this.pct(s.share)} ${s.label.toLowerCase()}`).join(', ') };
    });
  });

  constructor() {
    effect(() => {
      const id = this.productId();
      const ch = (this.channelParam() || '').toUpperCase();
      untracked(() => {
        if (ch === 'AMAZON' || ch === 'YOUTUBE') this.channel.set(ch);
        this.load(id);
      });
    });
    inject(DestroyRef).onDestroy(() => this.timer && clearTimeout(this.timer));
  }

  private load(id: string): void {
    this.api.productOverview(id).subscribe({
      next: (d) => this.data.set(d),
      error: (e) => this.error.set(errorMessage(e)),
    });
    this.loadVoices();
  }

  private loadVoices(): void {
    for (const col of this.columns) this.fetchVoices(col.sentiment, 0);
  }

  private fetchVoices(sentiment: Sentiment, offset: number): void {
    const channel = this.channel() === 'ALL' ? null : this.channel();
    this.api.productComments(this.productId(), { channel, sentiment, limit: 8, offset }).subscribe({
      next: (r) => this.voices.update((v) => ({
        ...v, [sentiment]: { items: offset ? [...v[sentiment].items, ...r.items] : r.items, total: r.total },
      })),
      error: () => {},
    });
  }

  protected setChannel(c: ChannelFilter): void {
    this.channel.set(c);
    this.loadVoices();
  }

  protected more(sentiment: Sentiment): void {
    this.fetchVoices(sentiment, this.voices()[sentiment].items.length);
  }

  protected maxTopic(ch: Channel): number {
    return Math.max(1, ...(this.data()?.channels[ch].topics ?? []).map((t) => t.comments));
  }

  protected pct(share: number): string {
    return `${Math.round(share * 100)}%`;
  }

  protected stars(rating: number): string {
    const full = Math.round(rating);
    return '★'.repeat(full) + '☆'.repeat(Math.max(0, 5 - full));
  }

  protected addListing(): void {
    this.api.analyzeAmazon({ url: this.newUrl.trim(), product_id: this.productId() }).subscribe({
      next: (job) => {
        this.newUrl = '';
        this.follow(job);
      },
      error: (e) => this.toast.error(errorMessage(e)),
    });
  }

  protected checkListing(l: Listing): void {
    this.api.checkListing(l.id).subscribe({ next: (job) => this.follow(job), error: (e) => this.toast.error(errorMessage(e)) });
  }

  protected removeListing(l: Listing): void {
    if (!confirm(`Stop tracking "${l.title || l.asin}"? Its reviews are hidden, not deleted.`)) return;
    this.api.removeListing(l.id).subscribe({
      next: () => {
        this.toast.show('Listing removed.');
        this.load(this.productId());
      },
      error: (e) => this.toast.error(errorMessage(e)),
    });
  }

  /** Poll a review check until it finishes, then refresh the page. */
  private follow(job: Job): void {
    this.running.set(job);
    if (this.timer) clearTimeout(this.timer);
    this.timer = setTimeout(() => {
      this.api.job(job.id).subscribe({
        next: (j) => {
          if (j.status === 'QUEUED' || j.status === 'RUNNING') return this.follow(j);
          this.running.set(null);
          if (j.status === 'FAILED') this.toast.error(j.message || "Couldn't read the reviews.");
          else this.toast.show(j.message ? `${j.message}.` : 'Reviews checked.');
          this.load(this.productId());
        },
        error: () => this.follow(job),
      });
    }, 1500);
  }
}
