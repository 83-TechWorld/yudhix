import { ChangeDetectionStrategy, Component, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ApiService, errorMessage } from '../../core/api.service';
import { Idea, IdeaStatus } from '../../core/models';
import { SessionService } from '../../core/session.service';
import { IconComponent } from '../../shared/icon.component';
import { AgoPipe, CompactPipe, EmptyStateComponent, IDEA_STATUS, IDEA_STATUSES, ToastService } from '../../shared/ui';

type Filter = 'ALL' | IdeaStatus;

/**
 * Product ideas: feature requests from comments, grouped by theme across every video.
 * The product team moves each idea through New -> Reviewing -> Planned -> Shipped (or Declined)
 * and keeps a note; the comments that asked for it stay attached as evidence.
 */
@Component({
  selector: 'y-ideas',
  imports: [FormsModule, RouterLink, IconComponent, EmptyStateComponent, AgoPipe, CompactPipe],
  template: `
    <div class="page page-narrow">
      <header class="page-head">
        <div>
          <h1>Product ideas</h1>
          <p>What customers ask for in comments, grouped by theme across all your videos. Most-supported first.</p>
        </div>
      </header>

      <div class="segmented filter" role="tablist" aria-label="Filter by status">
        <button type="button" [class.active]="filter() === 'ALL'" (click)="filter.set('ALL')">All <span class="count">{{ items()?.length ?? 0 }}</span></button>
        @for (s of statuses; track s) {
          <button type="button" [class.active]="filter() === s" (click)="filter.set(s)">{{ statusMeta[s].label }} <span class="count">{{ counts()[s] }}</span></button>
        }
      </div>

      @if (items() === null) {
        <div class="stack">@for (i of [1, 2, 3]; track i) { <div class="skeleton" style="height: 96px"></div> }</div>
      } @else if (!filtered().length) {
        <div class="card">
          @if (items()!.length) {
            <y-empty icon="layers" title="No ideas with this status" text="Pick another status above." />
          } @else {
            <y-empty icon="layers" title="No product ideas yet"
                     text="When commenters ask for a feature or a change, the AI names the request and groups similar ones here. Analyze a video or fetch its new comments to start." />
          }
        </div>
      } @else {
        <div class="stack">
          @for (i of filtered(); track i.id; let n = $index) {
            <button type="button" class="card card-pad card-lift idea enter" [style.--i]="n" (click)="open(i.id)">
              <div class="row-wrap">
                <h3>{{ i.title }}</h3>
                <span class="chip {{ statusMeta[i.status].chip }}">{{ statusMeta[i.status].label }}</span>
                @if (i.topicLabel) { <span class="chip chip-outline">{{ i.topicLabel }}</span> }
              </div>
              <div class="row-wrap subtle meta">
                <span><strong>{{ i.comments }}</strong> comment{{ i.comments === 1 ? '' : 's' }}</span>
                <span>· {{ i.reach | compact }} reach</span>
                <span>· {{ i.videos }} video{{ i.videos === 1 ? '' : 's' }}</span>
                @if (i.lastCommentAt) { <span>· last asked {{ i.lastCommentAt | ago }}</span> }
              </div>
              @if (i.note) { <p class="note clamp-2"><y-icon name="edit" [size]="13" /> {{ i.note }}</p> }
            </button>
          }
        </div>
      }
    </div>

    @if (selected(); as s) {
      <div class="sheet-backdrop" (click)="close()"></div>
      <aside class="sheet" role="dialog" aria-modal="true" aria-labelledby="idea-title">
        <div class="sheet-head">
          <h2 id="idea-title" style="flex: 1">{{ s.title }}</h2>
          <button class="btn btn-ghost btn-icon" type="button" (click)="close()" aria-label="Close"><y-icon name="x" /></button>
        </div>
        <div class="sheet-body stack">
          <div class="row-wrap subtle">
            <span><strong>{{ s.comments }}</strong> comment{{ s.comments === 1 ? '' : 's' }}</span>
            <span>· {{ s.reach | compact }} reach</span>
            <span>· {{ s.videos }} video{{ s.videos === 1 ? '' : 's' }}</span>
            @if (s.topicLabel) { <span>· {{ s.topicLabel }}</span> }
          </div>

          <div class="field">
            <label>Status</label>
            <div class="segmented status" role="radiogroup" aria-label="Status">
              @for (st of statuses; track st) {
                <button type="button" role="radio" [attr.aria-checked]="draftStatus() === st" [class.active]="draftStatus() === st"
                        [disabled]="!canEdit()" (click)="draftStatus.set(st)" [title]="statusMeta[st].hint">{{ statusMeta[st].label }}</button>
              }
            </div>
            <span class="hint">{{ statusMeta[draftStatus()].hint }}</span>
          </div>

          <div class="field">
            <label for="idea-note">Note for the team</label>
            <textarea id="idea-note" class="input" rows="3" [ngModel]="draftNote()" (ngModelChange)="draftNote.set($event)"
                      [disabled]="!canEdit()" placeholder="e.g. Planned for the spring firmware update"></textarea>
          </div>

          <div>
            <h3 class="eyebrow">Comments asking for this</h3>
            @if (!s.commentList) {
              <div class="skeleton" style="height: 120px"></div>
            } @else {
              <ul class="comments">
                @for (c of s.commentList; track c.id) {
                  <li>
                    <p>{{ c.text }}</p>
                    <div class="row-wrap subtle">
                      <span><y-icon name="thumbsUp" [size]="12" /> {{ c.likes | compact }}</span>
                      @if (c.createdAt) { <span>· {{ c.createdAt | ago }}</span> }
                      @if (c.videoId) { <span>· <a [routerLink]="['/videos', c.videoId]">{{ c.videoTitle || c.videoId }}</a></span> }
                      <span class="spacer"></span>
                      @if (c.active) {
                        <a class="btn btn-sm btn-ghost" routerLink="/inbox" [queryParams]="{ video: c.videoId, comment: c.id }">Reply</a>
                      } @else {
                        <span class="chip chip-outline" title="Not in this video's current comment sample">Archived</span>
                      }
                    </div>
                  </li>
                }
              </ul>
            }
          </div>
        </div>
        @if (canEdit()) {
          <div class="sheet-foot">
            <button class="btn btn-primary" type="button" (click)="save()" [disabled]="saving() || !dirty()">
              {{ saving() ? 'Saving…' : 'Save' }}
            </button>
            <button class="btn" type="button" (click)="close()">Cancel</button>
          </div>
        }
      </aside>
    }
  `,
  styles: `
    .filter { margin-bottom: 16px; overflow-x: auto; max-width: 100%; }
    .idea { display: block; width: 100%; text-align: left; font: inherit; color: inherit; cursor: pointer;
      h3 { margin: 0; font-size: 16px; } }
    .meta { margin-top: 6px; font-size: 13px; gap: 4px; }
    .note { margin: 8px 0 0; font-size: 13px; color: var(--muted-text); }
    .status { flex-wrap: wrap; }
    .hint { font-size: 12px; color: var(--muted-text); }
    .comments { list-style: none; margin: 8px 0 0; padding: 0;
      li { padding: 12px 0; border-top: 1px solid var(--border); }
      li:first-child { border-top: 0; padding-top: 4px; }
      p { margin: 0 0 6px; font-size: 14px; line-height: 1.5; }
      .row-wrap { font-size: 12px; gap: 4px; align-items: center; } }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class IdeasPage {
  private api = inject(ApiService);
  private toast = inject(ToastService);
  private router = inject(Router);
  protected session = inject(SessionService);

  /** ?idea=<id> opens that idea. */
  readonly ideaParam = input<string | undefined>(undefined, { alias: 'idea' });

  protected readonly statusMeta = IDEA_STATUS;
  protected readonly statuses = IDEA_STATUSES;

  protected readonly items = signal<Idea[] | null>(null);
  protected readonly filter = signal<Filter>('ALL');
  protected readonly selected = signal<Idea | null>(null);
  protected readonly draftStatus = signal<IdeaStatus>('NEW');
  protected readonly draftNote = signal('');
  protected readonly saving = signal(false);

  protected readonly canEdit = computed(() => this.session.can('content.write'));
  protected readonly filtered = computed(() => {
    const f = this.filter();
    return (this.items() ?? []).filter((i) => f === 'ALL' || i.status === f);
  });
  protected readonly counts = computed(() => {
    const c = Object.fromEntries(IDEA_STATUSES.map((s) => [s, 0])) as Record<IdeaStatus, number>;
    for (const i of this.items() ?? []) c[i.status]++;
    return c;
  });
  protected readonly dirty = computed(() => {
    const s = this.selected();
    return !!s && (s.status !== this.draftStatus() || (s.note ?? '') !== this.draftNote());
  });

  constructor() {
    this.load();
    effect(() => {
      const id = this.ideaParam();
      untracked(() => (id ? this.show(id) : this.selected.set(null)));
    });
  }

  private load(): void {
    this.api.ideas().subscribe({
      next: (r) => this.items.set(r.ideas),
      error: (e) => {
        this.items.set([]);
        this.toast.error(errorMessage(e));
      },
    });
  }

  protected open(id: string): void {
    this.router.navigate([], { queryParams: { idea: id } });
  }

  protected close(): void {
    this.router.navigate([], { queryParams: { idea: null } });
  }

  private show(id: string): void {
    const known = this.items()?.find((i) => i.id === id);
    if (known) this.select(known);
    this.api.idea(id).subscribe({
      next: (idea) => this.select(idea),
      error: (e) => {
        this.toast.error(errorMessage(e));
        this.close();
      },
    });
  }

  private select(idea: Idea): void {
    this.selected.set(idea);
    this.draftStatus.set(idea.status);
    this.draftNote.set(idea.note ?? '');
  }

  protected save(): void {
    const s = this.selected();
    if (!s) return;
    this.saving.set(true);
    this.api.updateIdea(s.id, { status: this.draftStatus(), note: this.draftNote() }).subscribe({
      next: (idea) => {
        this.saving.set(false);
        this.select(idea);
        this.items.update((list) => (list ?? []).map((i) => (i.id === idea.id ? { ...i, ...idea, commentList: undefined } : i)));
        this.toast.show(`Saved: ${IDEA_STATUS[idea.status].label}.`);
      },
      error: (e) => {
        this.saving.set(false);
        this.toast.error(errorMessage(e));
      },
    });
  }
}
