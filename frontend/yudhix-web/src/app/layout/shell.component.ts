import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';
import { ApiService } from '../core/api.service';
import { Health } from '../core/models';
import { SessionService } from '../core/session.service';
import { IconComponent } from '../shared/icon.component';
import { ToastService } from '../shared/ui';

interface NavItem { path: string; label: string; icon: string; hint: string; mobile: boolean; }

@Component({
  selector: 'y-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, IconComponent],
  templateUrl: './shell.component.html',
  styleUrl: './shell.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ShellComponent {
  private api = inject(ApiService);
  private router = inject(Router);
  protected session = inject(SessionService);
  protected toasts = inject(ToastService);

  protected readonly nav: NavItem[] = [
    { path: '/analyze', label: 'Analyze', icon: 'scan', hint: 'Check a video', mobile: true },
    { path: '/videos', label: 'Videos', icon: 'video', hint: 'Truth reports', mobile: true },
    { path: '/inbox', label: 'Inbox', icon: 'inbox', hint: 'Respond', mobile: true },
    { path: '/approvals', label: 'Approvals', icon: 'shield', hint: 'Review replies', mobile: true },
    { path: '/track', label: 'Track', icon: 'chart', hint: 'Outcomes & KPIs', mobile: true },
    { path: '/knowledge', label: 'Knowledge', icon: 'book', hint: 'Official facts', mobile: false },
  ];

  protected readonly health = signal<Health | null>(null);
  protected readonly apiDown = signal(false);
  protected readonly inReview = signal(0);
  protected readonly title = signal('');

  protected readonly themeIcon = computed(() =>
    ({ system: 'monitor', light: 'sun', dark: 'moon' })[this.session.theme()],
  );

  constructor() {
    const destroyRef = inject(DestroyRef);
    this.refresh();
    this.router.events
      .pipe(filter((e) => e instanceof NavigationEnd), takeUntilDestroyed(destroyRef))
      .subscribe((e) => {
        const url = (e as NavigationEnd).urlAfterRedirects;
        this.title.set(this.nav.find((n) => url.startsWith(n.path))?.label ?? 'Yudhix');
        this.refreshCounts();
      });
  }

  protected refresh(): void {
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
  }

  protected switchRole(): void {
    this.session.toggleRole();
    this.toasts.show(`You're now acting as ${this.session.user().name} (${this.session.user().title}).`);
    this.refreshCounts();
  }
}
