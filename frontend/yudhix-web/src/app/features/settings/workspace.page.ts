import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService, errorMessage } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { Country, WorkspaceDetail } from '../../core/models';
import { SessionService } from '../../core/session.service';
import { IconComponent } from '../../shared/icon.component';
import { AgoPipe, ToastService } from '../../shared/ui';

@Component({
  selector: 'y-workspace-settings',
  imports: [FormsModule, IconComponent, AgoPipe],
  template: `
    @if (!ws()) {
      <div class="skeleton" style="height: 320px"></div>
    } @else {
      @let w = ws()!;
      <div class="stack-lg">
        <section class="card card-pad stack enter">
          <h2>Workspace</h2>
          <form class="stack" (ngSubmit)="save()">
            <div class="field">
              <label for="n">Name</label>
              <input id="n" name="name" class="input" [(ngModel)]="form.name" [disabled]="!canManage" />
            </div>
            <div class="grid-2">
              <div class="field">
                <label for="c">Headquarters</label>
                <select id="c" name="country" class="select input" [(ngModel)]="form.country" [disabled]="!canManage">
                  @for (c of countries(); track c.code) { <option [value]="c.code">{{ c.name }}</option> }
                </select>
              </div>
              <div class="field">
                <label for="i">Industry</label>
                <input id="i" name="industry" class="input" [(ngModel)]="form.industry" [disabled]="!canManage" />
              </div>
            </div>
            <dl class="facts">
              <div><dt>Workspace ID</dt><dd class="mono">{{ w.id }}</dd></div>
              <div><dt>Address</dt><dd class="mono">{{ w.slug }}</dd></div>
              <div><dt>Data region</dt><dd>{{ w.dataRegion }}</dd></div>
              <div><dt>Created</dt><dd>{{ w.createdAt | ago }}</dd></div>
            </dl>
            @if (canManage) {
              <div><button class="btn btn-primary" type="submit" [disabled]="saving()">{{ saving() ? 'Saving…' : 'Save changes' }}</button></div>
            } @else {
              <p class="subtle">Only admins can change workspace settings.</p>
            }
          </form>
        </section>

        <section class="card card-pad stack enter" style="--i: 1">
          <h2>Your account</h2>
          <p class="muted">Signed in as <strong>{{ session.user()?.email }}</strong>. Password, two-factor authentication and active sessions are managed in your account.</p>
          <div class="row-wrap">
            <a class="btn" [href]="auth.accountUrl()"><y-icon name="lock" [size]="16" /> Account & security</a>
            <button class="btn" type="button" (click)="signOut()"><y-icon name="logout" [size]="16" /> Sign out</button>
          </div>
        </section>

        <section class="card card-pad stack danger enter" style="--i: 2">
          <h2>Danger zone</h2>
          <div class="danger-row">
            <div><strong>Leave workspace</strong><p class="subtle">You'll lose access until someone invites you again.</p></div>
            <button class="btn btn-danger" type="button" (click)="leave()">Leave</button>
          </div>
          @if (canManage && !w.isDemo) {
            <hr class="divider" />
            <div class="stack">
              <div><strong>Delete workspace</strong><p class="subtle">Removes access for everyone and cancels the subscription. Type <strong>{{ w.name }}</strong> to confirm.</p></div>
              <div class="row-wrap">
                <input class="input grow" [(ngModel)]="confirmName" [placeholder]="w.name" aria-label="Type the workspace name to confirm" />
                <button class="btn btn-danger" type="button" (click)="remove()" [disabled]="confirmName !== w.name">Delete workspace</button>
              </div>
            </div>
          }
        </section>
      </div>
    }
  `,
  styles: `
    .facts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px 24px; margin: 4px 0; }
    .facts dt { font-size: 12.5px; color: var(--text-3); }
    .facts dd { margin: 2px 0 0; overflow-wrap: anywhere; }
    @media (max-width: 560px) { .facts { grid-template-columns: 1fr; } }
    .danger { border-color: color-mix(in srgb, var(--danger) 35%, var(--border)); }
    .danger-row { display: flex; gap: 16px; align-items: center; justify-content: space-between; flex-wrap: wrap; }
    .grow { flex: 1 1 220px; }
    select.input { padding: 0 12px; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkspaceSettingsPage {
  private api = inject(ApiService);
  private router = inject(Router);
  private toast = inject(ToastService);
  protected auth = inject(AuthService);
  protected session = inject(SessionService);

  protected readonly ws = signal<WorkspaceDetail | null>(null);
  protected readonly countries = signal<Country[]>([]);
  protected readonly saving = signal(false);
  protected readonly canManage = this.session.can('workspace.manage');
  protected form = { name: '', country: '', industry: '' };
  protected confirmName = '';

  constructor() {
    this.api.countries().subscribe({ next: (r) => this.countries.set(r.countries), error: () => {} });
    this.api.workspace().subscribe({
      next: (w) => {
        this.ws.set(w);
        this.form = { name: w.name, country: w.country, industry: w.industry ?? '' };
      },
      error: (e) => this.toast.error(errorMessage(e)),
    });
  }

  protected save(): void {
    this.saving.set(true);
    this.api.updateWorkspace({ name: this.form.name, country: this.form.country, industry: this.form.industry }).subscribe({
      next: async (w) => {
        this.saving.set(false);
        this.ws.set(w);
        await this.session.refresh();
        this.toast.show('Workspace saved.');
      },
      error: (e) => {
        this.saving.set(false);
        this.toast.error(errorMessage(e));
      },
    });
  }

  protected leave(): void {
    if (!confirm(`Leave ${this.ws()?.name}?`)) return;
    this.api.leaveWorkspace().subscribe({ next: () => this.afterExit('You left the workspace.'), error: (e) => this.toast.error(errorMessage(e)) });
  }

  protected remove(): void {
    this.api.deleteWorkspace(this.confirmName).subscribe({
      next: () => this.afterExit('Workspace deleted.'),
      error: (e) => this.toast.error(errorMessage(e)),
    });
  }

  private async afterExit(message: string): Promise<void> {
    this.toast.show(message);
    this.session.workspaceId.set(null);
    const me = await this.session.refresh();
    this.router.navigateByUrl(me.workspaces.length ? '/analyze' : '/onboarding');
  }

  protected signOut(): void {
    this.session.clear();
    this.auth.logout();
  }
}
