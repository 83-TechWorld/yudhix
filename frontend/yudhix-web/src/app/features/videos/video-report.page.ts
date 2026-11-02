import { ChangeDetectionStrategy, Component, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { LowerCasePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService, errorMessage } from '../../core/api.service';
import { Claim, ClaimComment, Impact, OutreachNote, RootCause, Verdict, Video } from '../../core/models';
import { SessionService } from '../../core/session.service';
import { IconComponent } from '../../shared/icon.component';
import {
  AgoPipe, CAUSE_META, CompactPipe, PctPipe, PRIORITY_CHIP, RingComponent, SENTIMENT_CHIP, SentimentBarComponent,
  ToastService, VERDICT_META, VerdictBadgeComponent, youtubeAt,
} from '../../shared/ui';

type Tab = 'claims' | 'impact' | 'outreach';
type VerdictFilter = 'all' | 'disputed' | Verdict;

@Component({
  selector: 'y-video-report',
  imports: [
    FormsModule, RouterLink, IconComponent, RingComponent, VerdictBadgeComponent, SentimentBarComponent,
    CompactPipe, PctPipe, AgoPipe, LowerCasePipe,
  ],
  templateUrl: './video-report.page.html',
  styleUrl: './video-report.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class VideoReportPage {
  private api = inject(ApiService);
  private toast = inject(ToastService);
  protected session = inject(SessionService);

  readonly videoId = input.required<string>();
  /** ?tab=claims|impact|outreach deep-links straight to a tab. */
  readonly initialTab = input<string | undefined>(undefined, { alias: 'tab' });

  protected readonly verdictMeta = VERDICT_META;
  protected readonly causeMeta = CAUSE_META;
  protected readonly sentimentChip = SENTIMENT_CHIP;
  protected readonly priorityChip = PRIORITY_CHIP;
  protected readonly youtubeAt = youtubeAt;

  protected readonly tab = signal<Tab>('claims');
  protected readonly video = signal<(Video & { claims: Claim[] }) | null>(null);
  protected readonly error = signal('');
  protected readonly impact = signal<Impact | null>(null);
  protected readonly notes = signal<OutreachNote[] | null>(null);
  protected readonly verdictFilter = signal<VerdictFilter>('all');
  protected readonly recomputing = signal(false);

  // Linked-comments sheet
  protected readonly sheetClaim = signal<Claim | null>(null);
  protected readonly sheetComments = signal<ClaimComment[] | null>(null);

  // Creator note composer
  protected readonly selectedClaims = signal<Set<string>>(new Set());
  protected readonly generating = signal(false);

  protected readonly claims = computed(() => this.video()?.claims ?? []);
  protected readonly verdictCounts = computed(() => {
    const counts: Record<string, number> = { FACTUALLY_CORRECT: 0, MISLEADING: 0, FALSE: 0, UNVERIFIED_SPECULATION: 0 };
    for (const c of this.claims()) counts[c.verdict] = (counts[c.verdict] ?? 0) + 1;
    return counts;
  });
  protected readonly filteredClaims = computed(() => {
    const f = this.verdictFilter();
    return this.claims().filter((c) => (f === 'all' ? true : f === 'disputed' ? c.isMisinformation : c.verdict === f));
  });
  protected readonly causes = computed(() => {
    const i = this.impact();
    if (!i) return [];
    const total = i.rootCauses.reduce((s, c) => s + c.total, 0) || 1;
    return i.rootCauses.map((c) => ({ ...c, share: c.total / total, meta: CAUSE_META[c.cause as RootCause] }));
  });
  protected readonly maxLinked = computed(() => Math.max(1, ...(this.impact()?.claims ?? []).map((c) => c.linkedComments)));

  constructor() {
    effect(() => {
      const id = this.videoId();
      this.video.set(null);
      this.impact.set(null);
      this.notes.set(null);
      this.error.set('');
      this.api.video(id).subscribe({
        next: (v) => {
          this.video.set(v);
          this.selectedClaims.set(new Set(v.claims.filter((c) => c.isMisinformation).map((c) => c.id)));
        },
        error: (e) => this.error.set(errorMessage(e)),
      });
      this.loadImpact();
    });
    effect(() => {
      const t = this.initialTab();
      if (t === 'claims' || t === 'impact' || t === 'outreach') untracked(() => this.setTab(t));
    });
  }

  protected setTab(tab: Tab): void {
    this.tab.set(tab);
    if (tab === 'outreach' && this.notes() === null) this.loadNotes();
  }

  private loadImpact(): void {
    this.api.impact(this.videoId()).subscribe({ next: (i) => this.impact.set(i), error: () => {} });
  }

  private loadNotes(): void {
    this.api.outreach(this.videoId()).subscribe({ next: (r) => this.notes.set(r.notes), error: () => this.notes.set([]) });
  }

  protected recompute(): void {
    this.recomputing.set(true);
    this.api.reattribute(this.videoId()).subscribe({
      next: () => {
        this.recomputing.set(false);
        this.toast.show('Reactions re-linked to claims.');
        this.loadImpact();
        this.api.video(this.videoId()).subscribe((v) => this.video.set(v));
      },
      error: (e) => {
        this.recomputing.set(false);
        this.toast.error(errorMessage(e));
      },
    });
  }

  protected openClaim(claim: Claim): void {
    this.sheetClaim.set(claim);
    this.sheetComments.set(null);
    this.api.claimComments(claim.id).subscribe({
      next: (r) => this.sheetComments.set(r.comments),
      error: (e) => {
        this.sheetComments.set([]);
        this.toast.error(errorMessage(e));
      },
    });
  }

  protected closeSheet(): void {
    this.sheetClaim.set(null);
  }

  protected toggleClaim(id: string): void {
    this.selectedClaims.update((s) => {
      const next = new Set(s);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  protected generateNote(): void {
    const ids = [...this.selectedClaims()];
    if (!ids.length) {
      this.toast.error('Pick at least one claim to clarify.');
      return;
    }
    this.generating.set(true);
    this.api.createOutreach(this.videoId(), ids).subscribe({
      next: (note) => {
        this.generating.set(false);
        this.notes.update((n) => [note, ...(n ?? [])]);
        this.toast.show('Draft note created. Edit it before sending.');
      },
      error: (e) => {
        this.generating.set(false);
        this.toast.error(errorMessage(e));
      },
    });
  }

  protected saveNote(note: OutreachNote, status?: 'SENT'): void {
    this.api.updateOutreach(note.id, { subject: note.subject, body: note.body, ...(status ? { status } : {}) }).subscribe({
      next: (n) => {
        this.notes.update((list) => (list ?? []).map((x) => (x.id === n.id ? n : x)));
        this.toast.show(status === 'SENT' ? 'Marked as sent.' : 'Note saved.');
      },
      error: (e) => this.toast.error(errorMessage(e)),
    });
  }

  protected async copy(text: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(text);
      this.toast.show('Copied to clipboard.');
    } catch {
      this.toast.error("Couldn't copy. Select the text and copy it manually.");
    }
  }

  protected methodLabel(method: string | null): string {
    return method === 'LLM' ? 'AI-checked' : method === 'HEURISTIC' ? 'Rule-based' : 'Curated';
  }
}
