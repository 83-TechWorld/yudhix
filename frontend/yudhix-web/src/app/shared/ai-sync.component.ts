import { ChangeDetectionStrategy, Component, DestroyRef, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService, errorMessage } from '../core/api.service';
import { AiSync } from '../core/models';
import { SessionService } from '../core/session.service';
import { IconComponent } from './icon.component';
import { AgoPipe, ToastService } from './ui';

/**
 * Knowledge base <-> AI sync status for the workspace: which AI index is in use, how many facts are
 * synced, what is pending (e.g. uploaded while AI was off), and a "Sync now" button.
 * Polls while a sync is running.
 */
@Component({
  selector: 'y-ai-sync',
  imports: [RouterLink, IconComponent, AgoPipe],
  template: `
    @if (sync(); as s) {
      <section class="card card-pad sync" [class.compact]="compact()" aria-label="Knowledge base sync with AI">
        <div class="row-wrap head">
          <y-icon [name]="s.canSync ? (s.pending ? 'refresh' : 'checkCircle') : 'info'" [size]="17" [class.ok]="s.canSync && !s.pending" [class.spin]="s.running" />
          <strong class="grow">
            @if (!s.canSync) { Knowledge base not synced with AI }
            @else if (s.running) { Syncing the knowledge base with {{ s.engine.label }}… }
            @else if (s.pending) { {{ s.pending }} of {{ s.total }} facts waiting to sync }
            @else { Knowledge base synced with {{ s.engine.label }} }
          </strong>
          @if (s.canSync && session.can('content.write')) {
            <button class="btn btn-sm" type="button" (click)="syncNow()" [disabled]="s.running || starting()">
              <y-icon name="refresh" [size]="14" /> Sync now
            </button>
          }
        </div>
        @if (s.canSync) {
          <div class="bar" role="img" [attr.aria-label]="s.synced + ' of ' + s.total + ' facts synced'">
            <span [style.width.%]="s.total ? (s.synced / s.total) * 100 : 100"></span>
          </div>
          <p class="subtle meta">
            {{ s.synced }} / {{ s.total }} facts in this workspace's index for <span class="mono">{{ s.model }}</span>.
            @if (s.lastRun?.finishedAt) { Last sync {{ s.lastRun!.finishedAt | ago }}@if (s.lastRun!.embedded) { ({{ s.lastRun!.embedded }} added)}. }
            @if (s.lastRun?.status === 'FAILED') { <span class="err">{{ s.lastRun!.error }}</span> }
          </p>
          @if (!compact() && otherIndexes(s).length) {
            <p class="subtle meta">Also kept, for when you switch back:
              @for (i of otherIndexes(s); track i.model; let last = $last) { <span class="mono">{{ i.model }}</span> ({{ i.facts }}){{ last ? '.' : ', ' }} }
            </p>
          }
        } @else {
          <p class="subtle meta">{{ s.reason }} @if (s.engine.mode === 'RULES') { <a routerLink="/settings/ai">Connect AI</a> }</p>
        }
      </section>
    }
  `,
  styles: `
    .sync { display: flex; flex-direction: column; gap: 8px; }
    .head { gap: 10px; align-items: center; y-icon { color: var(--muted-text); } y-icon.ok { color: var(--ok); } }
    .grow { flex: 1; font-size: 14px; }
    .bar { height: 6px; border-radius: 4px; background: var(--muted-soft); overflow: hidden;
      span { display: block; height: 100%; background: var(--chart-valid); border-radius: 4px; transition: width .4s ease; } }
    .meta { font-size: 12.5px; margin: 0; line-height: 1.5; }
    .err { color: var(--danger-text); }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AiSyncComponent {
  private api = inject(ApiService);
  private toast = inject(ToastService);
  protected session = inject(SessionService);

  /** Smaller card (Knowledge page): hides the list of other indexes. */
  readonly compact = input(false);

  protected readonly sync = signal<AiSync | null>(null);
  protected readonly starting = signal(false);
  private timer: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    this.refresh();
    inject(DestroyRef).onDestroy(() => this.timer && clearTimeout(this.timer));
  }

  /** Re-read the status (call after uploads); keeps polling while a sync runs. */
  refresh(delay = 0): void {
    if (this.timer) clearTimeout(this.timer);
    this.timer = setTimeout(() => {
      this.api.aiSync().subscribe({
        next: (s) => {
          this.sync.set(s);
          if (s.running) this.refresh(2500);
        },
        error: () => {},
      });
    }, delay);
  }

  protected syncNow(): void {
    this.starting.set(true);
    this.api.syncNow().subscribe({
      next: (s) => {
        this.starting.set(false);
        this.sync.set(s);
        this.refresh(1500);
      },
      error: (e) => {
        this.starting.set(false);
        this.toast.error(errorMessage(e));
      },
    });
  }

  protected otherIndexes(s: AiSync) {
    return s.indexes.filter((i) => !i.current);
  }
}
