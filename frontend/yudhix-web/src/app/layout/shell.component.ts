import { NgTemplateOutlet } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, HostListener, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter, interval } from 'rxjs';
import { ApiService, errorMessage } from '../core/api.service';
import { AuthService } from '../core/auth.service';
import { AiStatus, AppNotification, Health, WorkspaceSummary } from '../core/models';
import { ROLE_INFO, SessionService, initials, trialDaysLeft } from '../core/session.service';
import { BotState, BotStatusComponent } from '../shared/bot-status.component';
import { IconComponent } from '../shared/icon.component';
import { AgoPipe, ToastService } from '../shared/ui';

interface NavItem { path: string; label: string; icon: string; mobile: boolean; }
interface NavGroup { label: string; items: NavItem[]; }
type Menu = 'workspace' | 'user' | 'notifications' | null;

/**
 * After a workspace switch, IDs in the URL (a video, product, idea, invoice, an inbox filter) belong to the
 * old workspace. Go to the same section without them, so the page never shows "not found" or empty filters.
 */
export function workspaceSafeUrl(url: string): string {
  const path = url.split(/[?#]/)[0];
  const parts = path.split('/').filter(Boolean);
  if (parts[0] === 'settings') return parts[1] === 'billing' ? '/settings/billing' : path;
  return parts.length ? `/${parts[0]}` : '/';
}

@Component({
  selector: 'y-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, NgTemplateOutlet, IconComponent, BotStatusComponent, AgoPipe],
  templateUrl: './shell.component.html',
  styleUrl: './shell.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ShellComponent {
  private api = inject(ApiService);
  private router = inject(Router);
  protected auth = inject(AuthService);
  protected session = inject(SessionService);
  protected toasts = inject(ToastService);
  protected readonly roleInfo = ROLE_INFO;
  protected readonly initials = initials;

  protected readonly nav: NavItem[] = [
    { path: '/analyze', label: 'Analyze', icon: 'scan', mobile: true },
    { path: '/videos', label: 'Videos', icon: 'video', mobile: true },
    { path: '/products', label: 'Products', icon: 'card', mobile: false },
    { path: '/inbox', label: 'Inbox', icon: 'inbox', mobile: true },
    { path: '/approvals', label: 'Approvals', icon: 'shield', mobile: true },
    { path: '/track', label: 'Track', icon: 'chart', mobile: true },
    { path: '/ideas', label: 'Ideas', icon: 'layers', mobile: false },
    { path: '/knowledge', label: 'Knowledge', icon: 'book', mobile: false },
    { path: '/settings', label: 'Settings', icon: 'settings', mobile: false },
  ];
  protected readonly groups: NavGroup[] = [
    { label: 'Workflow', items: this.nav.slice(0, 7) },
    { label: 'Workspace', items: this.nav.slice(7) },
  ];
  protected readonly mobileNav = this.nav.filter((n) => n.mobile);

  protected readonly health = signal<Health | null>(null);
  /** Which AI answers in this workspace: cloud provider, local model, or rules. */
  protected readonly ai = signal<AiStatus | null>(null);
  protected readonly apiDown = signal(false);
  protected readonly inReview = signal(0);
  protected readonly title = signal('');
  protected readonly menu = signal<Menu>(null);
  /** Which copy of the menu to render: next to the sidebar button or the mobile top-bar button. */
  protected readonly menuAt = signal<'side' | 'top'>('side');
  protected readonly notes = signal<AppNotification[]>([]);
  protected readonly unread = signal(0);

  /** Robot in the app bar: awake when the AI model is available, asleep in rule-based mode. */
  protected readonly botState = computed<BotState>(() => {
    if (this.apiDown()) return 'offline';
    const h = this.health();
    if (!h) return 'connecting';
    const ai = this.ai();
    if (ai) return ai.mode === 'RULES' ? 'asleep' : 'awake';
    return h.capabilities.llm ? 'awake' : 'asleep';
  });
  protected readonly botLabel = computed(() => {
    const ai = this.ai();
    if (this.apiDown() || !ai) return null;
    return ai.mode === 'CLOUD' ? `AI: ${ai.label} · ${ai.model}` : ai.mode === 'LOCAL' ? `AI: local model ${ai.model}`
      : 'No AI model: using fact retrieval and rules';
  });
  protected readonly themeIcon = computed(() => ({ system: 'monitor', light: 'sun', dark: 'moon' })[this.session.theme()]);
  protected readonly trialDays = computed(() => trialDaysLeft(this.session.workspace()));
  /** How much of the 14-day trial is used, for the sidebar progress bar. */
  protected readonly trialProgress = computed(() => {
    const left = this.trialDays();
    return left === null ? 0 : Math.min(100, Math.max(4, ((14 - left) / 14) * 100));
  });
  protected readonly status = computed(() => this.session.workspace()?.subscriptionStatus ?? null);
  /** Re-creates the routed page when the workspace changes, so no data from the old brand lingers. */
  protected readonly outletKeys = computed(() => [this.session.workspaceId() ?? 'none']);

  constructor() {
    const destroyRef = inject(DestroyRef);
    this.refreshHealth();
    this.refreshCounts();
    this.router.events
      .pipe(filter((e) => e instanceof NavigationEnd), takeUntilDestroyed(destroyRef))
      .subscribe((e) => {
        const url = (e as NavigationEnd).urlAfterRedirects;
        this.title.set(this.nav.find((n) => url.startsWith(n.path))?.label ?? 'Yudhix');
        this.menu.set(null);
        this.refreshCounts();
      });
    interval(45_000).pipe(takeUntilDestroyed(destroyRef)).subscribe(() => this.loadNotifications());
  }

  @HostListener('document:keydown.escape')
  closeMenus(): void {
    this.menu.set(null);
  }

  protected toggle(menu: Menu, at: 'side' | 'top' = 'side'): void {
    this.menuAt.set(at);
    this.menu.update((m) => (m === menu ? null : menu));
    if (menu === 'notifications' && this.menu() === 'notifications') this.loadNotifications();
  }

  protected refreshHealth(): void {
    this.api.health().subscribe({
      next: (h) => {
        this.health.set(h);
        this.apiDown.set(false);
      },
      error: () => this.apiDown.set(true),
    });
    this.api.aiStatus().subscribe({ next: (a) => this.ai.set(a), error: () => this.ai.set(null) });
  }

  private refreshCounts(): void {
    this.api.summary().subscribe({ next: (s) => this.inReview.set(s.replies.in_review), error: () => {} });
    this.loadNotifications();
  }

  private loadNotifications(): void {
    this.api.notifications().subscribe({
      next: (n) => {
        this.notes.set(n.items);
        this.unread.set(n.unread);
      },
      error: () => {},
    });
  }

  protected openNotification(n: AppNotification): void {
    if (!n.read) {
      this.api.markRead([n.id]).subscribe(() => this.loadNotifications());
    }
    this.menu.set(null);
    if (n.link) this.router.navigateByUrl(n.link);
  }

  protected markAllRead(): void {
    this.api.markRead().subscribe(() => this.loadNotifications());
  }

  protected switchTo(ws: WorkspaceSummary): void {
    this.menu.set(null);
    if (ws.id === this.session.workspaceId()) return;
    // Leave pages tied to the old workspace first, so they never load with the new workspace's data.
    const next = workspaceSafeUrl(this.router.url);
    const go = next !== this.router.url ? this.router.navigateByUrl(next) : Promise.resolve(true);
    go.then(() => {
      this.session.select(ws.id);
      this.toasts.show(`Switched to ${ws.name}.`);
      this.refreshCounts();
      this.refreshHealth(); // the AI engine is chosen per workspace
    });
  }

  protected joinDemo(): void {
    this.menu.set(null);
    this.api.joinDemo().subscribe({
      next: async (ws) => {
        await this.session.refresh();
        this.session.select(ws.id);
        this.toasts.show('Opened the PlayStation demo workspace.');
        this.router.navigateByUrl('/videos');
      },
      error: (e) => this.toasts.error(errorMessage(e)),
    });
  }

  protected readonly hasDemo = computed(() => this.session.workspaces().some((w) => w.isDemo));

  protected signOut(): void {
    this.session.clear();
    this.auth.logout();
  }
}
