import { NgTemplateOutlet } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, HostListener, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter, interval } from 'rxjs';
import { ApiService, errorMessage } from '../core/api.service';
import { AuthService } from '../core/auth.service';
import { AppNotification, Health, WorkspaceSummary } from '../core/models';
import { ROLE_INFO, SessionService, initials, trialDaysLeft } from '../core/session.service';
import { IconComponent } from '../shared/icon.component';
import { AgoPipe, ToastService } from '../shared/ui';

interface NavItem { path: string; label: string; icon: string; mobile: boolean; }
type Menu = 'workspace' | 'user' | 'notifications' | null;

@Component({
  selector: 'y-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, NgTemplateOutlet, IconComponent, AgoPipe],
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
    { path: '/inbox', label: 'Inbox', icon: 'inbox', mobile: true },
    { path: '/approvals', label: 'Approvals', icon: 'shield', mobile: true },
    { path: '/track', label: 'Track', icon: 'chart', mobile: true },
    { path: '/knowledge', label: 'Knowledge', icon: 'book', mobile: false },
    { path: '/settings', label: 'Settings', icon: 'settings', mobile: false },
  ];

  protected readonly health = signal<Health | null>(null);
  protected readonly apiDown = signal(false);
  protected readonly inReview = signal(0);
  protected readonly title = signal('');
  protected readonly menu = signal<Menu>(null);
  /** Which copy of the menu to render: next to the sidebar button or the mobile top-bar button. */
  protected readonly menuAt = signal<'side' | 'top'>('side');
  protected readonly notes = signal<AppNotification[]>([]);
  protected readonly unread = signal(0);

  protected readonly themeIcon = computed(() => ({ system: 'monitor', light: 'sun', dark: 'moon' })[this.session.theme()]);
  protected readonly trialDays = computed(() => trialDaysLeft(this.session.workspace()));
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
    this.session.select(ws.id);
    this.toasts.show(`Switched to ${ws.name}.`);
    this.refreshCounts();
    if (/^\/videos\/./.test(this.router.url)) this.router.navigateByUrl('/videos');
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
