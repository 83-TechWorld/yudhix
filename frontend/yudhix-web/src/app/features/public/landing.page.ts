import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth.service';
import { IconComponent } from '../../shared/icon.component';
import { PublicFooterComponent, PublicHeaderComponent } from './public-chrome';

@Component({
  selector: 'y-landing',
  imports: [RouterLink, IconComponent, PublicHeaderComponent, PublicFooterComponent],
  template: `
    <y-public-header />
    <main>
      <!-- Hero -->
      <section class="hero wrap">
        <div class="hero-copy">
          <span class="eyebrow enter">Truth-first social intelligence</span>
          <h1 class="enter" style="--i: 1">Is the backlash about your product, or about what someone <em>said</em> about it?</h1>
          <p class="lead enter" style="--i: 2">
            Yudhix checks what creators claim in their videos against your official documents, traces every angry
            comment back to the claim that triggered it, and helps your team respond with approved, fact-based replies.
          </p>
          <div class="row-wrap enter" style="--i: 3">
            @if (auth.authenticated()) {
              <a class="btn btn-primary btn-lg" routerLink="/analyze">Open Yudhix <y-icon name="arrowRight" /></a>
            } @else {
              <button class="btn btn-primary btn-lg" type="button" (click)="auth.register()" [disabled]="auth.unavailable()">Start your 14-day free trial</button>
            }
            <a class="btn btn-lg" routerLink="/pricing">See pricing</a>
          </div>
          <p class="subtle enter" style="--i: 4">No credit card. Set up in minutes: paste a video link and see the report.</p>
        </div>

        <!-- Illustrative report -->
        <div class="mock card enter" style="--i: 3" aria-label="Example truth report">
          <div class="mock-head">
            <span class="eyebrow">Example truth report</span>
            <strong>"They're ending physical discs"</strong>
            <span class="subtle">4 claims · 2,662 comments</span>
          </div>
          <div class="mock-claim">
            <span class="ts">01:14</span><span class="chip chip-warn">Misleading</span>
            <p>"Discs need a constant online check to play."</p>
            <div class="mini-bar"><span style="width: 62%; background: var(--warn)"></span></div>
          </div>
          <div class="mock-claim">
            <span class="ts">05:08</span><span class="chip chip-danger">False</span>
            <p>"Cloud saves are wiped the day your plan lapses."</p>
            <div class="mini-bar"><span style="width: 41%; background: var(--danger)"></span></div>
          </div>
          <div class="mock-claim">
            <span class="ts">08:45</span><span class="chip chip-ok">Accurate</span>
            <p>"The disc drive is sold separately."</p>
            <div class="mini-bar"><span style="width: 78%; background: var(--ok)"></span></div>
          </div>
          <div class="mock-foot"><y-icon name="target" [size]="15" /> Most negative comments react to the 01:14 claim, not to a product fault.</div>
        </div>
      </section>

      <!-- Problem -->
      <section class="wrap problem">
        <div class="card card-pad pcard enter"><y-icon name="message" [size]="20" /><h3>Comments don't happen in a vacuum</h3><p>Thousands of angry comments often trace back to one sentence in one video.</p></div>
        <div class="card card-pad pcard enter" style="--i: 1"><y-icon name="alert" [size]="20" /><h3>Sentiment alone misleads</h3><p>"Negative" doesn't tell you if your product failed or if a creator got the facts wrong.</p></div>
        <div class="card card-pad pcard enter" style="--i: 2"><y-icon name="clock" [size]="20" /><h3>Replies go out slow, or wrong</h3><p>Teams scramble without the official facts, and nobody measures if replies actually helped.</p></div>
      </section>

      <!-- How it works -->
      <section class="wrap section" id="how">
        <span class="eyebrow">How it works</span>
        <h2>From a video link to a turnaround, in four steps</h2>
        <ol class="steps">
          @for (s of steps; track s.title; let i = $index) {
            <li class="card card-pad enter" [style.--i]="i">
              <span class="n">{{ i + 1 }}</span>
              <h3>{{ s.title }}</h3>
              <p>{{ s.text }}</p>
            </li>
          }
        </ol>
      </section>

      <!-- Features -->
      <section class="wrap section" id="features">
        <span class="eyebrow">Features</span>
        <h2>Built for brand, social and comms teams</h2>
        <div class="features">
          @for (f of features; track f.title; let i = $index) {
            <div class="feature enter" [style.--i]="i">
              <span class="ficon"><y-icon [name]="f.icon" [size]="20" /></span>
              <div><h3>{{ f.title }}</h3><p>{{ f.text }}</p></div>
            </div>
          }
        </div>
      </section>

      <!-- Agencies -->
      <section class="wrap section split" id="agencies">
        <div>
          <span class="eyebrow">For agencies</span>
          <h2>One login, every brand you manage</h2>
          <p class="lead">Each brand gets its own workspace with its own team, roles, knowledge base and billing. Switch between them in one click; data never crosses between clients.</p>
          <ul class="checks">
            <li><y-icon name="check" [size]="16" [stroke]="3" /> Per-workspace roles: admin, approver, agent, analyst</li>
            <li><y-icon name="check" [size]="16" [stroke]="3" /> Invite client stakeholders as approvers or read-only analysts</li>
            <li><y-icon name="check" [size]="16" [stroke]="3" /> Separate plans, usage and invoices per brand</li>
          </ul>
        </div>
        <div class="card card-pad switcher-mock" aria-hidden="true">
          <div class="menu-label">Workspaces</div>
          @for (w of brands; track w.name) {
            <div class="sw-item" [class.on]="w.on"><span class="sw-logo">{{ w.name.slice(0, 2).toUpperCase() }}</span><span><strong>{{ w.name }}</strong><small>{{ w.role }}</small></span>@if (w.on) { <y-icon name="check" [size]="16" /> }</div>
          }
        </div>
      </section>

      <!-- Security -->
      <section class="wrap section" id="security">
        <span class="eyebrow">Security & privacy</span>
        <h2>Enterprise-ready from day one</h2>
        <div class="features">
          @for (f of security; track f.title; let i = $index) {
            <div class="feature enter" [style.--i]="i">
              <span class="ficon"><y-icon [name]="f.icon" [size]="20" /></span>
              <div><h3>{{ f.title }}</h3><p>{{ f.text }}</p></div>
            </div>
          }
        </div>
      </section>

      <!-- CTA -->
      <section class="wrap">
        <div class="cta card">
          <div>
            <h2>See what's really driving the conversation</h2>
            <p>Start a 14-day Professional trial. Bring one video; leave with a truth report.</p>
          </div>
          <div class="row-wrap">
            @if (auth.authenticated()) {
              <a class="btn btn-primary btn-lg" routerLink="/analyze">Open Yudhix</a>
            } @else {
              <button class="btn btn-primary btn-lg" type="button" (click)="auth.register()" [disabled]="auth.unavailable()">Start free trial</button>
            }
            <a class="btn btn-lg" routerLink="/pricing">Compare plans</a>
          </div>
        </div>
      </section>
    </main>
    <y-public-footer />
  `,
  styles: `
    :host { display: block; background: var(--bg); }
    .wrap { max-width: 1180px; margin: 0 auto; padding: 0 var(--gutter); }
    .hero { display: grid; grid-template-columns: 1.15fr .85fr; gap: 48px; align-items: center; padding-top: 72px; padding-bottom: 56px; }
    .hero-copy { display: flex; flex-direction: column; gap: 18px; }
    .hero h1 { font-size: clamp(32px, 4.6vw, 52px); line-height: 1.08; letter-spacing: -0.035em; font-weight: 750; }
    .hero h1 em { font-style: normal; background: linear-gradient(90deg, var(--brand), #7c3aed); -webkit-background-clip: text; background-clip: text; color: transparent; }
    .lead { font-size: 18px; color: var(--text-2); max-width: 620px; line-height: 1.55; }
    @media (max-width: 900px) { .hero { grid-template-columns: 1fr; padding-top: 40px; gap: 32px; } .lead { font-size: 16px; } }

    .mock { padding: 18px; display: flex; flex-direction: column; gap: 12px; box-shadow: var(--shadow-lg); }
    .mock-head { display: flex; flex-direction: column; gap: 2px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
    .mock-claim { display: grid; grid-template-columns: auto auto 1fr; gap: 6px 8px; align-items: center; }
    .mock-claim p { grid-column: 1 / -1; font-size: 14px; }
    .ts { font-family: var(--mono); font-size: 12px; font-weight: 600; padding: 2px 7px; border-radius: 6px; background: var(--surface-2); }
    .mini-bar { grid-column: 1 / -1; height: 6px; border-radius: 6px; background: var(--surface-3); overflow: hidden; }
    .mini-bar span { display: block; height: 100%; border-radius: 6px; animation: grow-x 1s var(--ease-out) backwards .4s; transform-origin: left; }
    .mock-foot { display: flex; gap: 8px; align-items: center; font-size: 13px; color: var(--brand-text); background: var(--brand-soft); padding: 10px 12px; border-radius: 10px; }

    .problem { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
    .pcard { display: flex; flex-direction: column; gap: 8px; color: var(--text-2); }
    .pcard y-icon { color: var(--brand-text); }
    .pcard h3 { color: var(--text); }
    @media (max-width: 760px) { .problem { grid-template-columns: 1fr; } }

    .section { padding-top: 88px; display: flex; flex-direction: column; gap: 10px; scroll-margin-top: 72px; }
    .section h2 { font-size: clamp(24px, 3vw, 34px); letter-spacing: -0.025em; margin-bottom: 18px; max-width: 720px; }
    .steps { list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
    .steps li { display: flex; flex-direction: column; gap: 8px; color: var(--text-2); }
    .steps h3 { color: var(--text); }
    .n { width: 30px; height: 30px; border-radius: 9px; display: grid; place-items: center; background: var(--brand-soft); color: var(--brand-text); font-weight: 750; }
    @media (max-width: 900px) { .steps { grid-template-columns: 1fr 1fr; } }
    @media (max-width: 520px) { .steps { grid-template-columns: 1fr; } }

    .features { display: grid; grid-template-columns: repeat(3, 1fr); gap: 28px 32px; }
    .feature { display: flex; gap: 14px; color: var(--text-2); }
    .feature h3 { color: var(--text); margin-bottom: 4px; }
    .ficon { width: 40px; height: 40px; border-radius: 12px; flex: none; display: grid; place-items: center; background: var(--surface); border: 1px solid var(--border); color: var(--brand-text); }
    @media (max-width: 900px) { .features { grid-template-columns: 1fr 1fr; } }
    @media (max-width: 560px) { .features { grid-template-columns: 1fr; } }

    .split { display: grid; grid-template-columns: 1fr 1fr; gap: 48px; align-items: center; }
    .split > div:first-child { display: flex; flex-direction: column; gap: 10px; }
    .split h2 { margin-bottom: 4px; }
    .checks { list-style: none; padding: 0; margin: 8px 0 0; display: flex; flex-direction: column; gap: 10px; }
    .checks li { display: flex; gap: 10px; align-items: center; }
    .checks y-icon { color: var(--ok); }
    .switcher-mock { display: flex; flex-direction: column; gap: 4px; max-width: 380px; justify-self: center; width: 100%; box-shadow: var(--shadow-lg); }
    .menu-label { font-size: 11.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: var(--text-3); padding: 0 8px 6px; }
    .sw-item { display: flex; gap: 10px; align-items: center; padding: 8px; border-radius: 10px; }
    .sw-item.on { background: var(--brand-soft); }
    .sw-item span:nth-child(2) { display: flex; flex-direction: column; flex: 1; line-height: 1.3; }
    .sw-item small { color: var(--text-3); }
    .sw-logo { width: 30px; height: 30px; border-radius: 9px; display: grid; place-items: center; background: linear-gradient(135deg, var(--brand), #7c3aed); color: #fff; font-weight: 800; font-size: 12px; }
    @media (max-width: 860px) { .split { grid-template-columns: 1fr; } }

    .cta { margin-top: 96px; padding: 36px; display: flex; gap: 24px; align-items: center; justify-content: space-between; flex-wrap: wrap;
           background: linear-gradient(135deg, var(--brand-soft), var(--surface)); }
    .cta h2 { font-size: 26px; letter-spacing: -0.02em; }
    .cta p { color: var(--text-2); margin-top: 6px; }
    @media (max-width: 640px) { .cta { padding: 24px; } .cta .btn { flex: 1; } }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LandingPage {
  protected auth = inject(AuthService);

  protected readonly steps = [
    { title: 'Paste a video', text: 'Drop in a YouTube link. Yudhix reads the transcript and pulls out every checkable claim, with timestamps.' },
    { title: 'Check the facts', text: 'Each claim is checked against your official specs and policies: accurate, misleading, false or unverified.' },
    { title: 'Trace the reaction', text: 'Every comment is linked to the claim it reacts to, so you see what is misinformation and what is a real issue.' },
    { title: 'Respond & measure', text: 'Draft fact-based replies, get them approved, send creators a clarification note, and track the turnaround.' },
  ];

  protected readonly features = [
    { icon: 'file', title: 'Claim extraction', text: 'Timestamped, atomic claims from captions, Whisper transcripts or a pasted script.' },
    { icon: 'book', title: 'Your knowledge, your truth', text: 'Verdicts cite your own documents, never the open web.' },
    { icon: 'target', title: 'Outrage attribution', text: 'See exactly which sentence drove the negativity, with the words that link each comment.' },
    { icon: 'shield', title: 'Approval workflow', text: 'Nothing posts without an approver. Separation of duties is enforced, not suggested.' },
    { icon: 'mail', title: 'Creator clarification notes', text: 'Polite, sourced notes that ask creators to add context, without legal threats.' },
    { icon: 'trendUp', title: 'Turnaround analytics', text: 'Measure whether replies changed the conversation, not just how many you sent.' },
  ];

  protected readonly security = [
    { icon: 'lock', title: 'PII masked before AI', text: 'Names, phones, emails and government IDs are masked before any model sees a comment.' },
    { icon: 'users', title: 'SSO-ready sign-in', text: 'Keycloak-based identity: MFA, password policy, and SAML / OIDC single sign-on for Enterprise.' },
    { icon: 'layers', title: 'Strict workspace isolation', text: 'Every request is checked against your workspace membership and role.' },
    { icon: 'file', title: 'Tamper-evident audit log', text: 'Every approval, post and change is recorded in a hash-chained ledger.' },
    { icon: 'globe', title: 'Regional compliance', text: 'Policy packs for India DPDP and US CCPA, with data kept in your region.' },
    { icon: 'building', title: 'Built for procurement', text: 'Invoice billing, role-based access and audit exports your security team will ask for.' },
  ];

  protected readonly brands = [
    { name: 'Northwind Audio', role: 'Admin', on: true },
    { name: 'Contoso Gaming', role: 'Approver', on: false },
    { name: 'Fabrikam Mobile', role: 'Agent', on: false },
  ];
}
