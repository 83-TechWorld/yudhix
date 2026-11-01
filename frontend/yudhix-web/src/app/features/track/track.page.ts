import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { ApiService, errorMessage } from '../../core/api.service';
import { LeaderboardRow, Summary, TrendPoint, Video } from '../../core/models';
import { IconComponent } from '../../shared/icon.component';
import { CompactPipe, PctPipe, RingComponent, ToastService } from '../../shared/ui';

@Component({
  selector: 'y-track',
  imports: [FormsModule, RouterLink, IconComponent, RingComponent, CompactPipe, PctPipe],
  templateUrl: './track.page.html',
  styleUrl: './track.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TrackPage {
  private api = inject(ApiService);
  private toast = inject(ToastService);

  protected readonly videos = signal<Video[]>([]);
  protected readonly videoId = signal('');
  protected readonly summary = signal<Summary | null>(null);
  protected readonly trend = signal<TrendPoint[]>([]);
  protected readonly board = signal<LeaderboardRow[]>([]);
  protected readonly error = signal('');
  protected readonly checking = signal(false);

  protected readonly trendMax = computed(() => Math.max(1, ...this.trend().map((p) => p.positive + p.negative + p.neutral)));
  protected readonly trendLabels = computed(() => {
    const t = this.trend();
    if (!t.length) return [];
    const fmt = (d: string) => new Date(d).toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
    return [fmt(t[0].day), fmt(t[Math.floor(t.length / 2)].day), fmt(t[t.length - 1].day)];
  });
  protected readonly pipeline = computed(() => {
    const r = this.summary()?.replies;
    if (!r) return [];
    const steps = [
      { label: 'Drafts', value: r.draft + r.rejected, icon: 'edit' },
      { label: 'In review', value: r.in_review, icon: 'shield' },
      { label: 'Approved', value: r.approved, icon: 'check' },
      { label: 'Posted', value: r.posted, icon: 'send' },
    ];
    const max = Math.max(1, ...steps.map((s) => s.value));
    return steps.map((s) => ({ ...s, width: (s.value / max) * 100 }));
  });
  protected readonly outcomeTotal = computed(() => {
    const o = this.summary()?.outcomes;
    return o ? o.improved + o.neutral + o.worsened : 0;
  });

  constructor() {
    this.api.videos().subscribe({ next: (r) => this.videos.set(r.videos), error: () => {} });
    this.load();
  }

  protected load(): void {
    const vid = this.videoId() || null;
    this.summary.set(null);
    forkJoin({ s: this.api.summary(vid), t: this.api.trend(vid), b: this.api.leaderboard() }).subscribe({
      next: ({ s, t, b }) => {
        this.summary.set(s);
        this.trend.set(t.points);
        this.board.set(b.videos);
      },
      error: (e) => this.error.set(errorMessage(e)),
    });
  }

  protected selectVideo(id: string): void {
    this.videoId.set(id);
    this.load();
  }

  protected checkOutcomes(): void {
    this.checking.set(true);
    this.api.checkOutcomes().subscribe({
      next: (r) => {
        this.checking.set(false);
        if (!r.youtubeConnected) {
          this.toast.show(`No YouTube connection yet. ${r.simulatedReplies} simulated replies need outcomes recorded by hand under Approvals → Posted.`);
        } else {
          this.toast.show(`Checked threads: ${r.checked} outcomes found, ${r.awaitingFollowUp} still waiting.`);
        }
        this.load();
      },
      error: (e) => {
        this.checking.set(false);
        this.toast.error(errorMessage(e));
      },
    });
  }

  protected barY(p: TrendPoint, part: 'negative' | 'neutral' | 'positive'): number {
    const max = this.trendMax();
    const neg = (p.negative / max) * 100;
    const neu = (p.neutral / max) * 100;
    const pos = (p.positive / max) * 100;
    if (part === 'negative') return 100 - neg;
    if (part === 'neutral') return 100 - neg - neu;
    return 100 - neg - neu - pos;
  }

  protected barH(p: TrendPoint, part: 'negative' | 'neutral' | 'positive'): number {
    return (p[part] / this.trendMax()) * 100;
  }
}
