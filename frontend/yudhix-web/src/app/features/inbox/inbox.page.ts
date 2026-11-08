import { DecimalPipe, NgTemplateOutlet, TitleCasePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { Subject, Subscription, debounceTime } from 'rxjs';
import { ApiService, errorMessage } from '../../core/api.service';
import { InboxItem, Intent, Priority, RootCause, Video } from '../../core/models';
import { SessionService } from '../../core/session.service';
import { IconComponent } from '../../shared/icon.component';
import {
  INTENT_LABEL,
  AgoPipe, CAUSE_META, CompactPipe, EmptyStateComponent, PRIORITY_CHIP, SENTIMENT_CHIP, STATUS_LABEL, ToastService,
  VERDICT_META, VerdictBadgeComponent,
} from '../../shared/ui';

const PAGE = 40;

@Component({
  selector: 'y-inbox',
  imports: [FormsModule, RouterLink, NgTemplateOutlet, DecimalPipe, TitleCasePipe, IconComponent, VerdictBadgeComponent, EmptyStateComponent, AgoPipe, CompactPipe],
  templateUrl: './inbox.page.html',
  styleUrl: './inbox.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InboxPage {
  private api = inject(ApiService);
  private router = inject(Router);
  private toast = inject(ToastService);
  protected session = inject(SessionService);

  /** Query params (bound by the router): ?video=…&cause=… */
  readonly video = input<string | undefined>();
  readonly cause = input<string | undefined>();
  /** ?intent=IDEA|PRAISE|BUY|… and ?fresh=1 (only comments added since the last full analysis). */
  readonly intent = input<string | undefined>();
  readonly fresh = input<string | undefined>();
  /** ?comment=<id> opens that comment (used by "Reply" on the Product impact panel). */
  readonly comment = input<string | undefined>();
  private deepLinkId: string | null = null;

  protected readonly causeMeta = CAUSE_META;
  protected readonly verdictMeta = VERDICT_META;
  protected readonly sentimentChip = SENTIMENT_CHIP;
  protected readonly priorityChip = PRIORITY_CHIP;
  protected readonly statusLabel = STATUS_LABEL;

  protected readonly videos = signal<Video[]>([]);
  protected readonly videoFilter = signal<string>('');
  protected readonly causeFilter = signal<RootCause | ''>('');
  protected readonly intentFilter = signal<Intent | ''>('');
  protected readonly freshFilter = signal(false);
  protected readonly intentLabels = INTENT_LABEL;
  protected readonly intentOptions = Object.keys(INTENT_LABEL) as Intent[];
  protected readonly priorityFilter = signal<Priority | ''>('');
  protected readonly statusFilter = signal<'OPEN' | 'REPLIED'>('OPEN');
  protected readonly q = signal('');

  protected readonly items = signal<InboxItem[] | null>(null);
  protected readonly total = signal(0);
  protected readonly loadingMore = signal(false);
  protected readonly error = signal('');

  protected readonly selectedId = signal<string | null>(null);
  protected readonly detail = signal<InboxItem | null>(null);
  protected readonly sheetOpen = signal(false);

  protected draft = '';
  protected readonly drafting = signal(false);
  protected readonly saving = signal(false);
  protected readonly citesFact = signal(false);

  protected readonly selectedVideoTitle = computed(
    () => this.videos().find((v) => v.videoId === this.videoFilter())?.title ?? '',
  );

  private search$ = new Subject<string>();
  private listSub?: Subscription;

  constructor() {
    const destroyRef = inject(DestroyRef);
    this.api.videos().subscribe({ next: (r) => this.videos.set(r.videos), error: () => {} });

    // Query params → filters
    effect(() => {
      const video = this.video() ?? '';
      const cause = (this.cause() ?? '') as RootCause | '';
      const comment = this.comment() ?? null;
      const intent = (this.intent() ?? '') as Intent | '';
      const fresh = this.fresh() === '1' || this.fresh() === 'true';
      untracked(() => {
        this.deepLinkId = comment;
        this.videoFilter.set(video);
        this.causeFilter.set(cause);
        this.intentFilter.set(intent in INTENT_LABEL ? intent : '');
        this.freshFilter.set(fresh);
        this.load();
      });
    });

    const sub = this.search$.pipe(debounceTime(300)).subscribe((q) => {
      this.q.set(q);
      this.load();
    });
    destroyRef.onDestroy(() => {
      sub.unsubscribe();
      this.listSub?.unsubscribe();
    });
  }

  private filters(offset = 0) {
    return {
      video_id: this.videoFilter() || null,
      cause: this.causeFilter() || null,
      intent: this.intentFilter() || null,
      fresh: this.freshFilter() ? 1 : null,
      priority: this.priorityFilter() || null,
      status: this.statusFilter(),
      q: this.q() || null,
      limit: PAGE,
      offset,
    };
  }

  protected load(): void {
    this.items.set(null);
    this.error.set('');
    this.listSub?.unsubscribe();
    this.listSub = this.api.inbox(this.filters()).subscribe({
      next: (page) => {
        this.items.set(page.items);
        this.total.set(page.total);
        const wide = window.matchMedia('(min-width: 1100px)').matches;
        const linked = this.deepLinkId;
        this.deepLinkId = null;
        if (linked) {
          // Open the linked comment even if the current filters hide it from the list.
          const inList = page.items.find((i) => i.id === linked);
          if (inList) this.select(inList, !wide);
          else this.selectById(linked, !wide);
        } else if (!page.items.some((i) => i.id === this.selectedId())) {
          // The selected comment no longer matches the filters: never show it next to a list it isn't in.
          if (wide && page.items.length) this.select(page.items[0], false);
          else this.clearSelection();
        }
      },
      error: (e) => this.error.set(errorMessage(e)),
    });
  }

  protected loadMore(): void {
    this.loadingMore.set(true);
    this.api.inbox(this.filters(this.items()?.length ?? 0)).subscribe({
      next: (page) => {
        this.items.update((list) => [...(list ?? []), ...page.items]);
        this.loadingMore.set(false);
      },
      error: (e) => {
        this.loadingMore.set(false);
        this.toast.error(errorMessage(e));
      },
    });
  }

  /** Filter changes are mirrored into the URL so links and the back button work. */
  protected setFilter(kind: 'video' | 'cause' | 'priority' | 'status' | 'intent' | 'fresh', value: string): void {
    if (kind === 'priority') {
      this.priorityFilter.set(value as Priority | '');
      this.load();
    } else if (kind === 'status') {
      this.statusFilter.set(value as 'OPEN' | 'REPLIED');
      this.load();
    } else {
      this.router.navigate([], {
        queryParams: { [kind]: value || null },
        queryParamsHandling: 'merge',
        replaceUrl: true,
      });
    }
  }

  protected onSearch(value: string): void {
    this.search$.next(value.trim());
  }

  protected select(item: InboxItem, openSheet = true): void {
    this.selectedId.set(item.id);
    this.detail.set(item);
    this.draft = '';
    this.citesFact.set(false);
    if (openSheet && !window.matchMedia('(min-width: 1100px)').matches) this.sheetOpen.set(true);
    this.api.inboxItem(item.id).subscribe({ next: (d) => this.detail.set(d), error: () => {} });
  }

  private selectById(id: string, openSheet: boolean): void {
    this.selectedId.set(id);
    this.draft = '';
    this.citesFact.set(false);
    this.api.inboxItem(id).subscribe({
      next: (d) => {
        this.detail.set(d);
        if (openSheet) this.sheetOpen.set(true);
      },
      error: () => this.clearSelection(),
    });
  }

  private clearSelection(): void {
    this.selectedId.set(null);
    this.detail.set(null);
    this.sheetOpen.set(false);
  }

  protected closeSheet(): void {
    this.sheetOpen.set(false);
  }

  protected suggest(): void {
    const d = this.detail();
    if (!d) return;
    this.drafting.set(true);
    this.api.suggest(d.id).subscribe({
      next: (r) => {
        this.draft = r.text;
        this.citesFact.set(r.citesOfficialFact);
        this.drafting.set(false);
      },
      error: (e) => {
        this.drafting.set(false);
        this.toast.error(errorMessage(e));
      },
    });
  }

  protected save(submit: boolean): void {
    const d = this.detail();
    if (!d || !this.draft.trim()) {
      this.toast.error('Write a reply first, or use "Draft with AI".');
      return;
    }
    this.saving.set(true);
    this.api.createReply(d.id, this.draft).subscribe({
      next: (reply) => {
        if (!submit) return this.afterSave(d.id, 'Draft saved. Find it under Approvals.');
        this.api.replyAction(reply.id, 'submit').subscribe({
          next: () => this.afterSave(d.id, 'Sent for approval.'),
          error: (e) => {
            this.saving.set(false);
            this.toast.error(errorMessage(e));
          },
        });
      },
      error: (e) => {
        this.saving.set(false);
        this.toast.error(errorMessage(e));
      },
    });
  }

  private afterSave(commentId: string, message: string): void {
    this.saving.set(false);
    this.draft = '';
    this.toast.show(message);
    this.api.inboxItem(commentId).subscribe((d) => {
      this.detail.set(d);
      this.items.update((list) => (list ?? []).map((i) => (i.id === d.id ? { ...i, replyStatus: d.replyStatus, replyId: d.replyId } : i)));
    });
  }
}
