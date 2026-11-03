import { ChangeDetectionStrategy, Component, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService, errorMessage } from '../../core/api.service';
import { ImpactLevel, ImpactTrend, ProductImpact, RootCause, SentimentSplit } from '../../core/models';
import { IconComponent } from '../../shared/icon.component';
import { CompactPipe } from '../../shared/ui';

/** One sentiment / cause segment as drawn in a stacked bar. */
interface Segment { key: string; label: string; color: string; value: number; share: number }

const SENTIMENT_SERIES = [
  { key: 'negative', label: 'Negative', color: 'var(--chart-neg)' },
  { key: 'neutral', label: 'Neutral', color: 'var(--chart-neu)' },
  { key: 'positive', label: 'Positive', color: 'var(--chart-pos)' },
] as const;

const CAUSE_SERIES: Record<RootCause, { label: string; color: string; fix: string }> = {
  MISINFORMATION: { label: 'Disputed claims', color: 'var(--chart-misinfo)', fix: 'Fix with a creator note and replies that cite the fact' },
  VALID_CONCERN: { label: 'Real product concerns', color: 'var(--chart-valid)', fix: 'Accurate claims: send to the product team' },
  UNLINKED: { label: 'General negativity', color: 'var(--chart-general)', fix: 'Not tied to a claim: reply to the most-liked ones' },
};

const LEVEL: Record<ImpactLevel, { label: string; chip: string; icon: string }> = {
  HIGH: { label: 'High impact', chip: 'chip-danger', icon: 'alert' },
  MEDIUM: { label: 'Medium impact', chip: 'chip-warn', icon: 'info' },
  LOW: { label: 'Low impact', chip: 'chip-ok', icon: 'checkCircle' },
};

const TREND: Record<ImpactTrend, { label: string; icon: string }> = {
  RISING: { label: 'Negative comments rising this week', icon: 'trendUp' },
  STEADY: { label: 'Negative comments steady', icon: 'minus' },
  FADING: { label: 'Negative comments fading', icon: 'trendDown' },
  QUIET: { label: 'Few new comments in the last 2 weeks', icon: 'clock' },
};

/**
 * Product impact panel: how a video's comments affect the product.
 * Sentiment by comments vs by reach, what can fix the negativity, topics, trend over time and
 * the most-liked negative comments. All charts are plain HTML/CSS with hover tooltips and a table view.
 */
@Component({
  selector: 'y-product-impact',
  imports: [RouterLink, IconComponent, CompactPipe],
  templateUrl: './product-impact.component.html',
  styleUrl: './product-impact.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProductImpactComponent {
  private api = inject(ApiService);

  readonly videoId = input.required<string>();
  /** Bump to reload (e.g. after "Re-link"). */
  readonly version = input(0);

  protected readonly data = signal<ProductImpact | null>(null);
  protected readonly error = signal('');
  protected readonly tip = signal<{ x: number; y: number; title: string; lines: string[] } | null>(null);

  protected readonly sentimentSeries = SENTIMENT_SERIES;
  protected readonly causeSeries = CAUSE_SERIES;
  protected readonly levelMeta = LEVEL;
  protected readonly trendMeta = TREND;

  protected readonly sentimentRows = computed(() => {
    const d = this.data();
    if (!d) return [];
    return [
      { label: 'By comments', hint: 'every comment counts once', segments: this.split(d.sentiment.byComments) },
      { label: 'By reach', hint: 'weighted by likes and replies', segments: this.split(d.sentiment.byReach) },
    ];
  });

  protected readonly causeSegments = computed<(Segment & { cause: RootCause; comments: number; fix: string })[]>(() =>
    (this.data()?.negativeByCause ?? []).map((c) => ({
      key: c.cause, cause: c.cause, label: CAUSE_SERIES[c.cause].label, color: CAUSE_SERIES[c.cause].color,
      value: c.reach, share: c.share, comments: c.comments, fix: CAUSE_SERIES[c.cause].fix,
    })),
  );

  protected readonly topicRows = computed(() => {
    const topics = this.data()?.topics ?? [];
    const max = Math.max(1, ...topics.map((t) => t.comments));
    return topics.map((t) => ({
      ...t,
      width: (t.comments / max) * 100,
      segments: this.split({ positive: t.positive, neutral: t.neutral, negative: t.negative }),
    }));
  });

  protected readonly timeline = computed(() => {
    const tl = this.data()?.timeline;
    if (!tl?.points.length) return null;
    const totals = tl.points.map((p) => p.positive + p.neutral + p.negative);
    const max = Math.max(1, ...totals);
    const step = niceStep(max);
    const top = Math.ceil(max / step) * step;
    const fmt = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' });
    const columns = tl.points.map((p, i) => ({
      date: p.date,
      label: (tl.bucket === 'week' ? 'Week of ' : '') + fmt.format(new Date(p.date + 'T00:00:00')),
      total: totals[i],
      height: (totals[i] / top) * 100,
      segments: this.split(p),
    }));
    const ticks = Array.from({ length: Math.round(top / step) + 1 }, (_, i) => i * step);
    // About 5 labels on wide screens, never one right before the last (that would collide with it).
    const labelEvery = Math.max(1, Math.ceil(columns.length / 5));
    return { bucket: tl.bucket, columns, top, ticks, labelEvery };
  });

  constructor() {
    effect(() => {
      const id = this.videoId();
      this.version();
      untracked(() => this.load(id));
    });
  }

  private load(id: string): void {
    this.error.set('');
    this.api.productImpact(id).subscribe({
      next: (d) => this.data.set(d),
      error: (e) => this.error.set(errorMessage(e)),
    });
  }

  /** Stacked segments in fixed series order (negative, neutral, positive). */
  private split(s: SentimentSplit): Segment[] {
    const total = s.positive + s.neutral + s.negative || 1;
    return SENTIMENT_SERIES.map((x) => ({ ...x, value: s[x.key], share: s[x.key] / total }));
  }

  protected showTip(event: Event, title: string, lines: string[]): void {
    const el = event.currentTarget as HTMLElement;
    const target = (el.querySelector('.tl-bar') as HTMLElement | null) ?? el; // columns: anchor on the bar itself
    const host = target.closest('.pi') as HTMLElement | null;
    if (!host) return;
    const t = target.getBoundingClientRect();
    const h = host.getBoundingClientRect();
    this.tip.set({ x: t.left - h.left + t.width / 2, y: t.top - h.top, title, lines });
  }

  protected hideTip(): void {
    this.tip.set(null);
  }

  private readonly numFmt = new Intl.NumberFormat();
  protected num(n: number): string {
    return this.numFmt.format(n);
  }

  protected pct(share: number): string {
    return `${Math.round(share * 100)}%`;
  }
}

/** 1, 2 or 5 x 10^n so the y-axis has 3-5 gridlines. */
function niceStep(max: number): number {
  const raw = max / 4;
  const pow = Math.pow(10, Math.floor(Math.log10(raw || 1)));
  const n = raw / pow;
  return Math.max(1, (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * pow);
}
