import { ChangeDetectionStrategy, Component, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService, errorMessage } from '../../core/api.service';
import { Growth, GrowthLevel, Intent } from '../../core/models';
import { IconComponent } from '../../shared/icon.component';
import { CompactPipe, IDEA_STATUS } from '../../shared/ui';

const LEVEL: Record<GrowthLevel, { label: string; chip: string; icon: string }> = {
  STRONG: { label: 'Strong signal', chip: 'chip-ok', icon: 'trendUp' },
  MODERATE: { label: 'Moderate signal', chip: 'chip-info', icon: 'minus' },
  LOW: { label: 'Weak signal', chip: 'chip-outline', icon: 'trendDown' },
};

/** What each intent means for the product team, shown under the bar chart. */
const INTENT_HINT: Record<Intent, string> = {
  IDEA: 'asks for a feature or a change',
  PRAISE: 'likes something',
  BUY: 'bought it or plans to',
  QUESTION: 'asks a question',
  COMPLAINT: 'complains',
  LEAVE: 'returning, cancelling or switching',
  OTHER: 'anything else',
};

/**
 * Product growth panel: the positive side of a video's comments.
 * What people want (by intent), what they love (topics), feature requests grouped into
 * product ideas, buying signals and praise. Single-series bars with hover tooltips and a table view.
 */
@Component({
  selector: 'y-product-growth',
  imports: [RouterLink, IconComponent, CompactPipe],
  templateUrl: './product-growth.component.html',
  styleUrls: ['./product-impact.component.scss', './product-growth.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProductGrowthComponent {
  private api = inject(ApiService);

  readonly videoId = input.required<string>();
  /** Bump to reload (after new comments arrive or a re-link). */
  readonly version = input(0);

  protected readonly data = signal<Growth | null>(null);
  protected readonly error = signal('');
  protected readonly tip = signal<{ x: number; y: number; title: string; lines: string[] } | null>(null);

  protected readonly levelMeta = LEVEL;
  protected readonly statusMeta = IDEA_STATUS;
  protected readonly intentHint = INTENT_HINT;

  protected readonly intentRows = computed(() => {
    const d = this.data();
    if (!d) return [];
    const max = Math.max(1, ...d.intents.map((i) => i.comments));
    const total = d.totals.comments || 1;
    return d.intents.filter((i) => i.comments).map((i) => ({ ...i, width: (i.comments / max) * 100, share: i.comments / total }));
  });

  protected readonly lovedRows = computed(() => {
    const loved = this.data()?.loved ?? [];
    const max = Math.max(1, ...loved.map((t) => t.reach));
    return loved.map((t) => ({ ...t, width: (t.reach / max) * 100 }));
  });

  /** Feature requests the AI hasn't named and grouped yet. */
  protected readonly unthemed = computed(() => {
    const d = this.data();
    return d ? d.ideaComments - d.ideas.reduce((n, i) => n + i.comments, 0) : 0;
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
    this.api.growth(id).subscribe({
      next: (d) => this.data.set(d),
      error: (e) => this.error.set(errorMessage(e)),
    });
  }

  protected showTip(event: Event, title: string, lines: string[]): void {
    const target = event.currentTarget as HTMLElement;
    const host = target.closest('.pi') as HTMLElement | null;
    if (!host) return;
    const t = target.getBoundingClientRect();
    const h = host.getBoundingClientRect();
    this.tip.set({ x: t.left - h.left + t.width / 2, y: t.top - h.top, title, lines });
  }

  protected hideTip(): void {
    this.tip.set(null);
  }

  protected pct(share: number): string {
    return `${Math.round(share * 100)}%`;
  }
}
