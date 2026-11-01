import { ChangeDetectionStrategy, Component, Injectable, Pipe, PipeTransform, computed, input, signal } from '@angular/core';
import { IconComponent } from './icon.component';
import { Priority, RootCause, Sentiment, Verdict } from '../core/models';

// ------------------------------------------------------------------ labels

export const VERDICT_META: Record<Verdict, { label: string; chip: string; quote: string; icon: string; color: string }> = {
  FACTUALLY_CORRECT: { label: 'Accurate', chip: 'chip-ok', quote: 'quote-ok', icon: 'checkCircle', color: 'var(--ok)' },
  MISLEADING: { label: 'Misleading', chip: 'chip-warn', quote: 'quote-warn', icon: 'alert', color: 'var(--warn)' },
  FALSE: { label: 'False', chip: 'chip-danger', quote: 'quote-bad', icon: 'xCircle', color: 'var(--danger)' },
  UNVERIFIED_SPECULATION: { label: 'Unverified', chip: 'chip', quote: 'quote-muted', icon: 'help', color: 'var(--muted)' },
};

export const CAUSE_META: Record<RootCause, { label: string; short: string; chip: string; color: string; help: string }> = {
  MISINFORMATION: {
    label: 'Reacting to misinformation', short: 'Misinformation', chip: 'chip-warn', color: 'var(--warn)',
    help: 'Triggered by a misleading, false or unverified claim. Clarify the fact.',
  },
  VALID_CONCERN: {
    label: 'Valid product concern', short: 'Valid concern', chip: 'chip-info', color: 'var(--info)',
    help: 'Reacting to an accurate claim. A real issue to acknowledge or fix.',
  },
  UNLINKED: {
    label: 'General reaction', short: 'General', chip: 'chip', color: 'var(--muted)',
    help: 'Not tied to a specific claim in the video.',
  },
};

export const SENTIMENT_CHIP: Record<Sentiment, string> = {
  POSITIVE: 'chip-ok', NEGATIVE: 'chip-danger', NEUTRAL: 'chip', MIXED: 'chip-warn',
};

export const PRIORITY_CHIP: Record<Priority, string> = { P1: 'chip-danger', P2: 'chip-warn', P3: 'chip' };

export const STATUS_LABEL: Record<string, { label: string; chip: string }> = {
  DRAFT: { label: 'Draft', chip: 'chip' },
  IN_REVIEW: { label: 'In review', chip: 'chip-info' },
  REJECTED: { label: 'Changes requested', chip: 'chip-warn' },
  APPROVED: { label: 'Approved', chip: 'chip-ok' },
  POSTED: { label: 'Posted', chip: 'chip-brand' },
};

// ------------------------------------------------------------------ components

@Component({
  selector: 'y-verdict',
  imports: [IconComponent],
  template: `<span class="chip" [class]="meta().chip"><y-icon [name]="meta().icon" [size]="13" [stroke]="2.4" />{{ meta().label }}</span>`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class VerdictBadgeComponent {
  readonly verdict = input.required<Verdict>();
  protected readonly meta = computed(() => VERDICT_META[this.verdict()] ?? VERDICT_META.UNVERIFIED_SPECULATION);
}

/** Circular 0-100% gauge. */
@Component({
  selector: 'y-ring',
  template: `
    <svg [attr.width]="size()" [attr.height]="size()" viewBox="0 0 36 36" role="img" [attr.aria-label]="label() + ' ' + pct() + '%'">
      <circle cx="18" cy="18" r="15.5" fill="none" stroke="var(--surface-3)" stroke-width="3.2" />
      <circle cx="18" cy="18" r="15.5" fill="none" [attr.stroke]="color()" stroke-width="3.2" stroke-linecap="round"
        [attr.stroke-dasharray]="dash()" transform="rotate(-90 18 18)" />
      <text x="18" y="19.5" text-anchor="middle" dominant-baseline="middle" font-size="9" font-weight="700" fill="var(--text)">{{ pct() }}%</text>
    </svg>`,
  styles: `:host { display: inline-flex; }`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RingComponent {
  readonly value = input.required<number>(); // 0..1
  readonly size = input(56);
  readonly label = input('');
  readonly invert = input(false); // true when high = bad
  protected readonly pct = computed(() => Math.round(Math.max(0, Math.min(1, this.value())) * 100));
  protected readonly dash = computed(() => `${(this.pct() / 100) * 97.4} 97.4`);
  protected readonly color = computed(() => {
    const good = this.invert() ? 1 - this.value() : this.value();
    return good >= 0.7 ? 'var(--ok)' : good >= 0.4 ? 'var(--warn)' : 'var(--danger)';
  });
}

/** Stacked positive / neutral / negative bar with optional legend. */
@Component({
  selector: 'y-sentiment-bar',
  template: `
    <div class="bar" role="img" [attr.aria-label]="aria()">
      <span class="bar-bad" [style.width.%]="p().neg"></span>
      <span class="bar-neutral" [style.width.%]="p().neu"></span>
      <span class="bar-ok" [style.width.%]="p().pos"></span>
    </div>
    @if (legend()) {
      <div class="legend subtle">
        <span><i class="dot" style="background:var(--danger)"></i>{{ negative() }} negative</span>
        <span><i class="dot" style="background:var(--muted);opacity:.5"></i>{{ neutral() }} neutral</span>
        <span><i class="dot" style="background:var(--ok)"></i>{{ positive() }} positive</span>
      </div>
    }`,
  styles: `.legend { display: flex; gap: 14px; margin-top: 8px; flex-wrap: wrap; } .legend span { display: inline-flex; align-items: center; gap: 6px; }`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SentimentBarComponent {
  readonly positive = input(0);
  readonly negative = input(0);
  readonly neutral = input(0);
  readonly legend = input(false);
  protected readonly p = computed(() => {
    const t = this.positive() + this.negative() + this.neutral() || 1;
    return { pos: (this.positive() / t) * 100, neg: (this.negative() / t) * 100, neu: (this.neutral() / t) * 100 };
  });
  protected readonly aria = computed(
    () => `${this.negative()} negative, ${this.neutral()} neutral, ${this.positive()} positive`,
  );
}

@Component({
  selector: 'y-empty',
  imports: [IconComponent],
  template: `
    <div class="empty">
      <div class="empty-icon"><y-icon [name]="icon()" [size]="22" /></div>
      <h3>{{ title() }}</h3>
      @if (text()) { <p>{{ text() }}</p> }
      <ng-content />
    </div>`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EmptyStateComponent {
  readonly icon = input('inbox');
  readonly title = input.required<string>();
  readonly text = input('');
}

// ------------------------------------------------------------------ toasts

export interface Toast { id: number; text: string; kind: 'info' | 'error'; }

@Injectable({ providedIn: 'root' })
export class ToastService {
  readonly toasts = signal<Toast[]>([]);
  private seq = 0;

  show(text: string, kind: 'info' | 'error' = 'info'): void {
    const id = ++this.seq;
    this.toasts.update((t) => [...t, { id, text, kind }]);
    setTimeout(() => this.dismiss(id), kind === 'error' ? 6000 : 3500);
  }
  error(text: string): void {
    this.show(text, 'error');
  }
  dismiss(id: number): void {
    this.toasts.update((t) => t.filter((x) => x.id !== id));
  }
}

// ------------------------------------------------------------------ pipes

@Pipe({ name: 'ago' })
export class AgoPipe implements PipeTransform {
  transform(value: string | null | undefined): string {
    if (!value) return '';
    const secs = Math.max(0, (Date.now() - new Date(value).getTime()) / 1000);
    if (secs < 60) return 'just now';
    if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
    if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
    if (secs < 86400 * 30) return `${Math.floor(secs / 86400)}d ago`;
    return new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
  }
}

@Pipe({ name: 'due' })
export class DuePipe implements PipeTransform {
  transform(value: string | null | undefined): string {
    if (!value) return '';
    const secs = (new Date(value).getTime() - Date.now()) / 1000;
    const abs = Math.abs(secs);
    const span = abs < 3600 ? `${Math.max(1, Math.round(abs / 60))}m` : abs < 86400 ? `${Math.round(abs / 3600)}h` : `${Math.round(abs / 86400)}d`;
    return secs >= 0 ? `due in ${span}` : `overdue by ${span}`;
  }
}

@Pipe({ name: 'compact' })
export class CompactPipe implements PipeTransform {
  transform(value: number | null | undefined): string {
    if (value === null || value === undefined) return '–';
    return new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 }).format(value);
  }
}

@Pipe({ name: 'pct' })
export class PctPipe implements PipeTransform {
  transform(value: number | null | undefined): string {
    return value === null || value === undefined ? '–' : `${Math.round(value * 100)}%`;
  }
}

/** Seconds offset → YouTube deep link. */
export function youtubeAt(videoId: string, seconds: number): string {
  return `https://www.youtube.com/watch?v=${videoId}&t=${Math.max(0, Math.floor(seconds))}s`;
}
