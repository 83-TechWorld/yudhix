import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService, errorMessage } from '../../core/api.service';
import { Outcome, Reply } from '../../core/models';
import { SessionService } from '../../core/session.service';
import { IconComponent } from '../../shared/icon.component';
import { AgoPipe, DuePipe, EmptyStateComponent, PRIORITY_CHIP, STATUS_LABEL, ToastService } from '../../shared/ui';

type Lane = 'review' | 'changes' | 'approved' | 'posted';

const LANES: { key: Lane; label: string; statuses: string }[] = [
  { key: 'review', label: 'Needs review', statuses: 'IN_REVIEW' },
  { key: 'changes', label: 'Drafts & changes', statuses: 'DRAFT,REJECTED' },
  { key: 'approved', label: 'Ready to post', statuses: 'APPROVED' },
  { key: 'posted', label: 'Posted', statuses: 'POSTED' },
];

@Component({
  selector: 'y-approvals',
  imports: [FormsModule, RouterLink, IconComponent, EmptyStateComponent, AgoPipe, DuePipe],
  templateUrl: './approvals.page.html',
  styleUrl: './approvals.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ApprovalsPage {
  private api = inject(ApiService);
  private toast = inject(ToastService);
  protected session = inject(SessionService);

  protected readonly lanes = LANES;
  protected readonly statusLabel = STATUS_LABEL;
  protected readonly priorityChip = PRIORITY_CHIP;
  protected readonly lane = signal<Lane>('review');
  protected readonly all = signal<Reply[] | null>(null);
  protected readonly busy = signal<string | null>(null);

  // Per-card inline state
  protected readonly rejecting = signal<string | null>(null);
  protected rejectReason = '';
  protected readonly editing = signal<string | null>(null);
  protected editText = '';
  protected readonly recording = signal<string | null>(null);
  protected followUp = '';

  protected readonly counts = computed(() => {
    const out: Record<Lane, number> = { review: 0, changes: 0, approved: 0, posted: 0 };
    for (const r of this.all() ?? []) {
      const lane = LANES.find((l) => l.statuses.split(',').includes(r.status));
      if (lane) out[lane.key]++;
    }
    return out;
  });
  protected readonly shown = computed(() => {
    const statuses = LANES.find((l) => l.key === this.lane())!.statuses.split(',');
    return (this.all() ?? []).filter((r) => statuses.includes(r.status));
  });

  constructor() {
    // Reload when the acting role changes (separation of duties changes what you can do).
    effect(() => {
      this.session.role();
      this.load();
    });
  }

  protected load(): void {
    this.api.replies().subscribe({
      next: (r) => this.all.set(r.replies),
      error: (e) => {
        this.all.set([]);
        this.toast.error(errorMessage(e));
      },
    });
  }

  protected canReview(r: Reply): boolean {
    return this.session.role() === 'approver' && r.authorId !== this.session.user().id;
  }

  private act(r: Reply, call: ReturnType<ApiService['replyAction']>, message: string): void {
    this.busy.set(r.id);
    call.subscribe({
      next: (updated) => {
        this.busy.set(null);
        this.all.update((list) => (list ?? []).map((x) => (x.id === updated.id ? updated : x)));
        this.rejecting.set(null);
        this.editing.set(null);
        this.recording.set(null);
        this.toast.show(message);
      },
      error: (e) => {
        this.busy.set(null);
        this.toast.error(errorMessage(e));
      },
    });
  }

  protected approve(r: Reply): void {
    this.act(r, this.api.replyAction(r.id, 'approve'), 'Approved. An agent can post it now.');
  }

  protected startReject(r: Reply): void {
    this.rejectReason = '';
    this.rejecting.set(r.id);
  }

  protected reject(r: Reply): void {
    if (!this.rejectReason.trim()) {
      this.toast.error('Add a short reason so the agent knows what to change.');
      return;
    }
    this.act(r, this.api.replyAction(r.id, 'reject', this.rejectReason.trim()), 'Sent back with your notes.');
  }

  protected startEdit(r: Reply): void {
    this.editText = r.text;
    this.editing.set(r.id);
  }

  protected saveEdit(r: Reply, submit: boolean): void {
    this.busy.set(r.id);
    this.api.editReply(r.id, this.editText).subscribe({
      next: (updated) => {
        if (submit) this.act(updated, this.api.replyAction(r.id, 'submit'), 'Submitted for approval.');
        else this.act(updated, this.api.reply(r.id), 'Saved.');
      },
      error: (e) => {
        this.busy.set(null);
        this.toast.error(errorMessage(e));
      },
    });
  }

  protected submit(r: Reply): void {
    this.act(r, this.api.replyAction(r.id, 'submit'), 'Submitted for approval.');
  }

  protected post(r: Reply): void {
    this.act(r, this.api.replyAction(r.id, 'post'), 'Posted (simulated until the YouTube connection is set up).');
  }

  protected startOutcome(r: Reply): void {
    this.followUp = '';
    this.recording.set(r.id);
  }

  protected saveOutcome(r: Reply, outcome?: Outcome): void {
    if (!outcome && !this.followUp.trim()) {
      this.toast.error('Paste the customer\'s follow-up, or pick an outcome.');
      return;
    }
    this.act(
      r,
      this.api.recordOutcome(r.id, outcome ? { outcome } : { follow_up_text: this.followUp.trim() }),
      'Outcome recorded.',
    );
  }
}
