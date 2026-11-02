import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { ROLE_INFO, SessionService } from '../../core/session.service';
import { IconComponent } from '../../shared/icon.component';

@Component({
  selector: 'y-settings',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, IconComponent],
  template: `
    <div class="page page-narrow">
      <header class="page-head">
        <div>
          <h1>Settings</h1>
          <p>You're {{ roleInfo[session.role()].label }} in this workspace.</p>
        </div>
      </header>
      <nav class="tabs" aria-label="Settings sections">
        <a routerLink="workspace" routerLinkActive="active"><y-icon name="building" [size]="16" /> Workspace</a>
        <a routerLink="team" routerLinkActive="active"><y-icon name="users" [size]="16" /> Team</a>
        <a routerLink="billing" routerLinkActive="active"><y-icon name="card" [size]="16" /> Plan & billing</a>
      </nav>
      <router-outlet />
    </div>
  `,
  styles: `
    .tabs a { padding: 12px 14px; font-weight: 600; font-size: 14px; color: var(--text-2); border-bottom: 2px solid transparent; margin-bottom: -1px;
              display: flex; gap: 6px; align-items: center; white-space: nowrap; transition: color var(--dur-2) ease, border-color var(--dur-2) ease; }
    .tabs a:hover { text-decoration: none; color: var(--text); }
    .tabs a.active { color: var(--text); border-bottom-color: var(--brand); }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SettingsLayout {
  protected session = inject(SessionService);
  protected readonly roleInfo = ROLE_INFO;
}
