import { ChangeDetectionStrategy, Component, effect, inject, input, signal, untracked } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { ApiService, errorMessage } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { InvitePreview } from '../../core/models';
import { ROLE_INFO, SessionService } from '../../core/session.service';
import { IconComponent } from '../../shared/icon.component';
import { ToastService } from '../../shared/ui';

/** /invite/:token: show who invited you, then sign in (or sign up) and join. */
@Component({
  selector: 'y-invite',
  imports: [RouterLink, IconComponent],
  template: `
    <main class="center">
      <a routerLink="/" class="logo"><span class="mark">Y</span><strong>Yudhix</strong></a>
      <section class="card card-pad box enter">
        @if (error()) {
          <div class="icon bad"><y-icon name="alert" [size]="22" /></div>
          <h1>Invitation unavailable</h1>
          <p class="muted">{{ error() }}</p>
          <a class="btn" routerLink="/">Go to Yudhix</a>
        } @else if (!preview()) {
          <div class="skeleton" style="height: 24px; width: 60%"></div>
          <div class="skeleton" style="height: 80px"></div>
        } @else {
          @let p = preview()!;
          <div class="icon"><y-icon name="userPlus" [size]="22" /></div>
          <h1>Join {{ p.workspace }}</h1>
          <p class="muted"><strong>{{ p.invitedBy }}</strong> invited <strong>{{ p.email }}</strong> to join as <strong>{{ p.roleLabel }}</strong>.</p>
          <p class="subtle">{{ roleInfo[p.role].description }}</p>
          @if (auth.authenticated()) {
            <button class="btn btn-primary btn-lg btn-block" type="button" (click)="accept()" [disabled]="busy()">
              {{ busy() ? 'Joining…' : 'Accept and join' }}
            </button>
            <p class="subtle">Signed in as {{ email() }}. Wrong account? <button class="link" type="button" (click)="switchAccount()">Sign in with another</button></p>
          } @else {
            <button class="btn btn-primary btn-lg btn-block" type="button" (click)="auth.register(here())">Create an account to join</button>
            <button class="btn btn-lg btn-block" type="button" (click)="auth.login(here())">I already have an account</button>
            <p class="subtle">Use the email address the invitation was sent to.</p>
          }
        }
      </section>
    </main>
  `,
  styles: `
    .center { min-height: 100vh; min-height: 100dvh; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 24px; padding: 24px var(--gutter); }
    .logo { display: flex; align-items: center; gap: 10px; color: var(--text); font-size: 18px; }
    .logo:hover { text-decoration: none; }
    .mark { width: 32px; height: 32px; border-radius: 10px; display: grid; place-items: center; background: linear-gradient(135deg, var(--brand), #7c3aed); color: #fff; font-weight: 800; }
    .box { width: min(460px, 100%); display: flex; flex-direction: column; gap: 14px; text-align: center; align-items: center; }
    .box h1 { font-size: 22px; }
    .icon { width: 48px; height: 48px; border-radius: 14px; display: grid; place-items: center; background: var(--brand-soft); color: var(--brand-text); }
    .icon.bad { background: var(--danger-soft); color: var(--danger-text); }
    .link { border: 0; background: none; color: var(--brand-text); padding: 0; cursor: pointer; font: inherit; text-decoration: underline; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InvitePage {
  private api = inject(ApiService);
  private router = inject(Router);
  private toast = inject(ToastService);
  private session = inject(SessionService);
  protected auth = inject(AuthService);
  protected readonly roleInfo = ROLE_INFO;

  readonly token = input.required<string>();
  protected readonly preview = signal<InvitePreview | null>(null);
  protected readonly error = signal('');
  protected readonly busy = signal(false);
  protected readonly email = signal('');

  constructor() {
    effect(() => {
      const token = this.token();
      untracked(() => {
        this.api.invitePreview(token).subscribe({
          next: (p) => this.preview.set(p),
          error: (e) => this.error.set(errorMessage(e)),
        });
        if (this.auth.authenticated()) {
          this.session.refresh().then((me) => this.email.set(me.user.email)).catch(() => {});
        }
      });
    });
  }

  protected here(): string {
    return `/invite/${this.token()}`;
  }

  protected accept(): void {
    this.busy.set(true);
    this.api.acceptInvite(this.token()).subscribe({
      next: async (ws) => {
        await this.session.refresh();
        this.session.select(ws.id);
        this.toast.show(`Welcome to ${ws.name}.`);
        this.router.navigateByUrl('/analyze');
      },
      error: (e) => {
        this.busy.set(false);
        this.error.set(errorMessage(e));
      },
    });
  }

  protected switchAccount(): void {
    this.session.clear();
    this.auth.logout(this.here());
  }
}
