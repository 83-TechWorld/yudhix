import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { Subscription, switchMap, takeWhile, timer } from 'rxjs';
import { ApiService, errorMessage } from '../../core/api.service';
import { Health, Job, Onboarding, Video } from '../../core/models';
import { SessionService } from '../../core/session.service';
import { IconComponent } from '../../shared/icon.component';
import { AgoPipe, CompactPipe, RingComponent, ToastService } from '../../shared/ui';

const STAGES = [
  { key: 'FETCHING_VIDEO', label: 'Read video' },
  { key: 'TRANSCRIBING', label: 'Transcript' },
  { key: 'EXTRACTING_CLAIMS', label: 'Find claims' },
  { key: 'FACT_CHECKING', label: 'Fact-check' },
  { key: 'INGESTING_COMMENTS', label: 'Comments' },
  { key: 'UNDERSTANDING', label: 'Read comments' },
  { key: 'ATTRIBUTING', label: 'Link reactions' },
];

@Component({
  selector: 'y-analyze',
  imports: [FormsModule, RouterLink, IconComponent, RingComponent, AgoPipe, CompactPipe],
  templateUrl: './analyze.page.html',
  styleUrl: './analyze.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AnalyzePage {
  private api = inject(ApiService);
  private router = inject(Router);
  private toast = inject(ToastService);
  private destroyRef = inject(DestroyRef);
  protected session = inject(SessionService);

  protected readonly stages = STAGES;
  protected url = '';
  protected transcript = '';
  protected readonly showTranscript = signal(false);
  protected readonly submitting = signal(false);
  protected readonly formError = signal('');
  protected readonly job = signal<Job | null>(null);
  protected readonly jobs = signal<Job[]>([]);
  protected readonly videos = signal<Video[] | null>(null);
  protected readonly health = signal<Health | null>(null);
  protected readonly onboarding = signal<Onboarding | null>(null);
  protected readonly checklistHidden = signal(this.readHidden());
  protected readonly showChecklist = computed(() => {
    const o = this.onboarding();
    return !!o && o.completed < o.total && !this.session.workspace()?.isDemo && !this.checklistHidden();
  });
  private poll?: Subscription;

  protected readonly stageIndex = computed(() => {
    const j = this.job();
    if (!j) return -1;
    if (j.status === 'COMPLETED') return STAGES.length;
    return STAGES.findIndex((s) => s.key === j.stage);
  });

  protected readonly recentVideos = computed(() => (this.videos() ?? []).slice(0, 6));

  constructor() {
    this.api.health().subscribe({ next: (h) => this.health.set(h), error: () => {} });
    this.api.onboarding().subscribe({ next: (o) => this.onboarding.set(o), error: () => {} });
    this.api.videos().subscribe({ next: (r) => this.videos.set(r.videos), error: () => this.videos.set([]) });
    this.api.jobs().subscribe({
      next: (r) => {
        this.jobs.set(r.jobs);
        const running = r.jobs.find((j) => j.kind !== 'COMMENTS' && (j.status === 'RUNNING' || j.status === 'QUEUED'));
        if (running) this.track(running);
      },
      error: () => {},
    });
    this.destroyRef.onDestroy(() => this.poll?.unsubscribe());
  }

  protected submit(): void {
    const url = this.url.trim();
    if (!url) {
      this.formError.set('Paste a YouTube link to get started.');
      return;
    }
    this.formError.set('');
    this.submitting.set(true);
    this.api.analyze({ video_url: url, transcript: this.transcript.trim() || null }).subscribe({
      next: (job) => {
        this.submitting.set(false);
        this.track(job);
      },
      error: (e) => {
        this.submitting.set(false);
        this.formError.set(errorMessage(e));
      },
    });
  }

  protected tryExample(): void {
    this.url = 'https://www.youtube.com/watch?v=PTblI6oYfSU';
    this.submit();
  }

  private track(job: Job): void {
    this.job.set(job);
    this.poll?.unsubscribe();
    this.poll = timer(0, 1500)
      .pipe(
        switchMap(() => this.api.job(job.id)),
        takeWhile((j) => j.status === 'QUEUED' || j.status === 'RUNNING', true),
      )
      .subscribe({
        next: (j) => {
          this.job.set(j);
          if (j.status === 'COMPLETED') {
            this.toast.show('Analysis complete. Opening the truth report.');
            setTimeout(() => this.router.navigate(['/videos', j.videoId]), 700);
          }
        },
        error: (e) => this.toast.error(errorMessage(e)),
      });
  }

  protected hideChecklist(): void {
    this.checklistHidden.set(true);
    try {
      localStorage.setItem(`yudhix.checklist.${this.session.workspaceId()}`, '1');
    } catch {
      /* ignore */
    }
  }

  private readHidden(): boolean {
    try {
      return localStorage.getItem(`yudhix.checklist.${inject(SessionService).workspaceId()}`) === '1';
    } catch {
      return false;
    }
  }

  protected reset(): void {
    this.poll?.unsubscribe();
    this.job.set(null);
    this.url = '';
    this.transcript = '';
  }
}
