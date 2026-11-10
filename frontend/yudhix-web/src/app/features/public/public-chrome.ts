import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth.service';
import { IconComponent } from '../../shared/icon.component';

/** Header for the public site: logo, links, and sign-in / free-trial (or "Open app" when signed in). */
@Component({
  selector: 'y-public-header',
  imports: [RouterLink, IconComponent],
  template: `
    <header class="pub-header" [class.open]="open()">
      <div class="pub-inner">
        <a routerLink="/" class="pub-logo" (click)="open.set(false)"><span class="mark">Y</span><strong>Yudhix</strong></a>
        <nav class="pub-links" aria-label="Site">
          <a routerLink="/" fragment="how" (click)="open.set(false)">How it works</a>
          <a routerLink="/" fragment="features" (click)="open.set(false)">Features</a>
          <a routerLink="/" fragment="agencies" (click)="open.set(false)">For agencies</a>
          <a routerLink="/pricing" (click)="open.set(false)">Pricing</a>
        </nav>
        <span class="spacer"></span>
        <div class="pub-cta">
          @if (auth.authenticated()) {
            <a class="btn btn-primary" routerLink="/analyze">Open app <y-icon name="arrowRight" [size]="16" /></a>
          } @else {
            <button class="btn btn-ghost" type="button" (click)="auth.login()" [disabled]="auth.unavailable()">Sign in</button>
            <button class="btn btn-primary" type="button" (click)="auth.register()" [disabled]="auth.unavailable()">Start free trial</button>
          }
        </div>
        <button class="btn btn-ghost btn-icon menu-btn" type="button" (click)="open.set(!open())" [attr.aria-expanded]="open()" aria-label="Menu">
          <y-icon [name]="open() ? 'x' : 'menu'" />
        </button>
      </div>
    </header>
  `,
  styles: `
    .pub-header { position: sticky; top: 0; z-index: 30; background: color-mix(in srgb, var(--bg) 85%, transparent); backdrop-filter: saturate(180%) blur(14px); border-bottom: 1px solid var(--border); padding-top: var(--safe-top); }
    .pub-inner { max-width: 1180px; margin: 0 auto; padding: 0 var(--gutter); height: 64px; display: flex; align-items: center; gap: 28px; }
    .pub-logo { display: flex; align-items: center; gap: 10px; color: var(--text); text-decoration: none; font-size: 18px; letter-spacing: -0.02em; }
    .pub-logo:hover { text-decoration: none; }
    .mark { width: 32px; height: 32px; border-radius: 10px; display: grid; place-items: center; background: linear-gradient(135deg, var(--brand), #7c3aed); color: #fff; font-weight: 800; }
    .pub-links { display: flex; gap: 22px; }
    .pub-links a { color: var(--text-2); font-weight: 600; font-size: 14.5px; }
    .pub-links a:hover { color: var(--text); text-decoration: none; }
    .pub-cta { display: flex; gap: 8px; }
    .menu-btn { display: none; }
    @media (max-width: 860px) {
      .pub-links { display: none; position: absolute; top: calc(64px + var(--safe-top)); left: 0; right: 0; flex-direction: column; gap: 0; background: var(--surface); border-bottom: 1px solid var(--border); padding: 8px var(--gutter) 16px; }
      .pub-links a { padding: 12px 0; border-bottom: 1px solid var(--border); }
      .open .pub-links { display: flex; }
      .menu-btn { display: inline-flex; }
      .pub-inner { gap: 8px; }
      .pub-cta .btn-ghost { display: none; }
    }
    @media (max-width: 420px) { .pub-cta .btn-primary { padding: 0 12px; font-size: 13px; } }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PublicHeaderComponent {
  protected auth = inject(AuthService);
  protected readonly open = signal(false);
}

@Component({
  selector: 'y-public-footer',
  imports: [RouterLink],
  template: `
    <footer class="pub-footer">
      <div class="pub-inner">
        <div class="col brand">
          <strong>Yudhix</strong>
          <p>Truth-first social comment intelligence for enterprise brands and agencies.</p>
        </div>
        <div class="col">
          <span class="h">Product</span>
          <a routerLink="/" fragment="how">How it works</a>
          <a routerLink="/" fragment="features">Features</a>
          <a routerLink="/pricing">Pricing</a>
        </div>
        <div class="col">
          <span class="h">Trust</span>
          <a routerLink="/" fragment="security">Security & privacy</a>
          <span>India DPDP · US CCPA</span>
          <span>PII masked before AI</span>
        </div>
      </div>
      <div class="pub-inner legal">© {{ year }} Yudhix. All rights reserved.</div>
    </footer>
  `,
  styles: `
    .pub-footer { border-top: 1px solid var(--border); background: var(--surface); padding: 40px 0 calc(24px + var(--safe-bottom)); margin-top: 40px; }
    .pub-inner { max-width: 1180px; margin: 0 auto; padding: 0 var(--gutter); display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 24px; }
    .col { display: flex; flex-direction: column; gap: 8px; font-size: 14px; color: var(--text-2); }
    .col a { color: var(--text-2); }
    .brand p { max-width: 340px; }
    .h { font-weight: 700; color: var(--text); font-size: 13px; text-transform: uppercase; letter-spacing: .05em; }
    .legal { display: block; margin-top: 28px; font-size: 13px; color: var(--text-3); }
    @media (max-width: 640px) { .pub-inner { grid-template-columns: 1fr 1fr; } .brand { grid-column: 1 / -1; } }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PublicFooterComponent {
  protected readonly year = new Date().getFullYear();
}
