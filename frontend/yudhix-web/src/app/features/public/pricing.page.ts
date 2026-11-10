import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { environment } from '../../../environments/environment';
import { ApiService, errorMessage } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { Plan } from '../../core/models';
import { IconComponent } from '../../shared/icon.component';
import { MoneyPipe, detectCurrency } from '../../shared/ui';
import { SessionService } from '../../core/session.service';
import { PublicFooterComponent, PublicHeaderComponent } from './public-chrome';

export function quota(n: number, unit = ''): string {
  return n < 0 ? 'Unlimited' : `${n.toLocaleString()}${unit}`;
}

@Component({
  selector: 'y-pricing',
  imports: [RouterLink, MoneyPipe, IconComponent, PublicHeaderComponent, PublicFooterComponent],
  template: `
    <y-public-header />
    <main class="wrap">
      <header class="head enter">
        <span class="eyebrow">Pricing</span>
        <h1>Simple plans that grow with your brands</h1>
        <p class="lead">Every plan starts with a 14-day Professional trial. No credit card needed.</p>
        <div class="toggles">
          <div class="segmented" role="radiogroup" aria-label="Billing period">
            <button type="button" [class.active]="interval() === 'MONTH'" (click)="interval.set('MONTH')">Monthly</button>
            <button type="button" [class.active]="interval() === 'YEAR'" (click)="interval.set('YEAR')">Yearly <span class="save">2 months free</span></button>
          </div>
          @if (currencies().length > 1) {
            <div class="segmented" role="radiogroup" aria-label="Currency">
              @for (c of currencies(); track c) {
                <button type="button" [class.active]="currency() === c" (click)="setCurrency(c)">{{ currencyLabel(c) }}</button>
              }
            </div>
          }
        </div>
      </header>

      @if (error()) {
        <div class="callout callout-danger">{{ error() }}</div>
      } @else if (!plans()) {
        <div class="plans">@for (i of [1, 2, 3]; track i) { <div class="skeleton" style="height: 460px"></div> }</div>
      } @else {
        <div class="plans">
          @for (p of plans(); track p.id; let i = $index) {
            <article class="card plan enter" [style.--i]="i" [class.featured]="p.highlighted">
              @if (p.highlighted) { <span class="badge-pop">Most popular</span> }
              <h2>{{ p.name }}</h2>
              <p class="subtle tag">{{ p.tagline }}</p>
              <div class="price">
                <strong>{{ price(p) | money: p.currency : 0 }}</strong>
                <span class="subtle">/ month{{ interval() === 'YEAR' ? ', billed yearly' : '' }}</span>
              </div>
              @if (p.id === 'ENTERPRISE') {
                <a class="btn btn-block" [href]="salesHref">Talk to sales</a>
              } @else if (auth.authenticated()) {
                <a class="btn btn-block" [class.btn-primary]="p.highlighted" routerLink="/settings/billing">Choose in billing</a>
              } @else {
                <button class="btn btn-block" [class.btn-primary]="p.highlighted" type="button" (click)="auth.register()">Start free trial</button>
              }
              <ul>
                @for (f of p.features; track f) { <li><y-icon name="check" [size]="16" [stroke]="3" /> {{ f }}</li> }
              </ul>
            </article>
          }
        </div>

        <section class="compare">
          <h2>Compare plans</h2>
          <div class="table-wrap card">
            <table>
              <thead><tr><th scope="col">Included each month</th>@for (p of plans(); track p.id) { <th scope="col">{{ p.name }}</th> }</tr></thead>
              <tbody>
                <tr><th scope="row">Video analyses</th>@for (p of plans(); track p.id) { <td>{{ q(p.quotas.videos) }}</td> }</tr>
                <tr><th scope="row">Comments analyzed</th>@for (p of plans(); track p.id) { <td>{{ q(p.quotas.comments) }}</td> }</tr>
                <tr><th scope="row">AI drafts & checks</th>@for (p of plans(); track p.id) { <td>{{ q(p.quotas.aiCalls) }}</td> }</tr>
                <tr><th scope="row">Replies posted</th>@for (p of plans(); track p.id) { <td>{{ q(p.quotas.replies) }}</td> }</tr>
                <tr><th scope="row">Team members</th>@for (p of plans(); track p.id) { <td>{{ q(p.quotas.seats) }}</td> }</tr>
                <tr><th scope="row">Approval workflow & audit log</th>@for (p of plans(); track p.id) { <td><y-icon name="check" [size]="16" [stroke]="3" class="yes" /></td> }</tr>
                <tr><th scope="row">Creator clarification notes</th>@for (p of plans(); track p.id) { <td>@if (p.id !== 'STARTER') { <y-icon name="check" [size]="16" [stroke]="3" class="yes" /> } @else { – }</td> }</tr>
                <tr><th scope="row">SSO (SAML / OIDC)</th>@for (p of plans(); track p.id) { <td>@if (p.id === 'ENTERPRISE') { <y-icon name="check" [size]="16" [stroke]="3" class="yes" /> } @else { – }</td> }</tr>
              </tbody>
            </table>
          </div>
          @if (plans()?.[0]; as first) {
            <p class="subtle">
              @if (currency() === 'INR') { Prices in Indian rupees, excluding 18% GST. }
              @else { Prices in US dollars, excluding applicable taxes. }
              Extra comments beyond your plan are billed at {{ first.overagePer1000 | money: first.currency }} per 1,000.
              @if (currency() === 'INR') { Rupee pricing applies to workspaces based in India. }
              @else if (currencies().includes('INR')) { India-based workspaces are billed in rupees. }
            </p>
          }
        </section>
      }

      <section class="faq">
        <h2>Questions</h2>
        @for (f of faq; track f.q) {
          <details class="card">
            <summary>{{ f.q }}<y-icon name="chevronDown" [size]="18" /></summary>
            <p>{{ f.a }}</p>
          </details>
        }
      </section>
    </main>
    <y-public-footer />
  `,
  styles: `
    :host { display: block; background: var(--bg); }
    .wrap { max-width: 1180px; margin: 0 auto; padding: 0 var(--gutter); }
    .head { text-align: center; display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 56px 0 36px; }
    .head h1 { font-size: clamp(28px, 4vw, 44px); letter-spacing: -0.03em; }
    .lead { color: var(--text-2); font-size: 17px; }
    .toggles { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; }
    .save { font-size: 11.5px; color: var(--ok-text); background: var(--ok-soft); padding: 1px 6px; border-radius: 6px; }
    .plans { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; align-items: start; }
    @media (max-width: 900px) { .plans { grid-template-columns: 1fr; max-width: 480px; margin: 0 auto; } }
    .plan { padding: 26px; display: flex; flex-direction: column; gap: 14px; position: relative; }
    .plan.featured { border: 2px solid var(--brand); box-shadow: var(--shadow-lg); }
    .badge-pop { position: absolute; top: -12px; left: 26px; background: var(--brand); color: #fff; font-size: 12px; font-weight: 700; padding: 3px 10px; border-radius: 999px; }
    .tag { min-height: 40px; }
    .price { display: flex; align-items: baseline; gap: 6px; flex-wrap: wrap; }
    .price strong { font-size: 40px; letter-spacing: -0.03em; }
    .plan ul { list-style: none; padding: 0; margin: 6px 0 0; display: flex; flex-direction: column; gap: 10px; font-size: 14.5px; }
    .plan li { display: flex; gap: 8px; align-items: flex-start; }
    .plan li y-icon, .yes { color: var(--ok); margin-top: 2px; }
    .compare, .faq { margin-top: 72px; display: flex; flex-direction: column; gap: 16px; }
    .compare h2, .faq h2 { font-size: 26px; letter-spacing: -0.02em; }
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 14.5px; min-width: 560px; }
    th, td { padding: 13px 18px; border-bottom: 1px solid var(--border); text-align: left; }
    thead th { font-size: 13px; color: var(--text-3); text-transform: uppercase; letter-spacing: .04em; }
    tbody th { font-weight: 600; }
    tr:last-child th, tr:last-child td { border-bottom: 0; }
    .faq { max-width: 820px; }
    details { padding: 0; }
    summary { padding: 16px 20px; cursor: pointer; font-weight: 650; list-style: none; display: flex; justify-content: space-between; gap: 12px; align-items: center; }
    summary::-webkit-details-marker { display: none; }
    details[open] summary y-icon { transform: rotate(180deg); }
    summary y-icon { transition: transform var(--dur-2) var(--ease-out); color: var(--text-3); }
    details p { padding: 0 20px 18px; color: var(--text-2); }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PricingPage {
  private api = inject(ApiService);
  protected auth = inject(AuthService);
  protected readonly plans = signal<Plan[] | null>(null);
  protected readonly error = signal('');
  private session = inject(SessionService);
  protected readonly interval = signal<'MONTH' | 'YEAR'>('MONTH');
  protected readonly currency = signal<string>('USD');
  protected readonly currencies = signal<string[]>([]);
  protected readonly salesHref = `mailto:${environment.salesEmail}?subject=${encodeURIComponent('Yudhix Enterprise')}`;
  protected readonly q = (n: number) => quota(n);
  protected readonly price = (p: Plan) =>
    this.interval() === 'YEAR' && p.yearlyPrice ? p.yearlyPrice / 12 : p.monthlyPrice;

  protected readonly faq = [
    { q: 'How does the free trial work?', a: 'New workspaces get 14 days of Professional, with no card. When it ends, reports stay readable; pick a plan to keep analyzing and posting.' },
    { q: 'Can I manage several brands?', a: 'Yes. Each brand is its own workspace with its own team, roles, plan and invoices. Switch between them from the workspace menu.' },
    { q: 'How do you bill enterprises?', a: 'Plans are invoiced at the start of each period with net-30 terms. Online card payments are coming soon; Enterprise can always pay by invoice.' },
    { q: 'What counts as a video analysis?', a: 'Each time you analyze a video (or re-analyze it), one analysis is used. Comments pulled for that video count towards your comment quota.' },
    { q: 'Where is our data stored?', a: 'In the region chosen for your workspace. Personal details in comments are masked before any AI model sees them, and author IDs are pseudonymized.' },
    { q: 'Do you support SSO?', a: 'Sign-in runs on Keycloak. Enterprise workspaces can connect SAML or OIDC single sign-on and enforce MFA.' },
  ];

  constructor() {
    // ?currency=INR wins; signed-in users see their workspace's currency; otherwise guess from the browser.
    const fromUrl = new URLSearchParams(location.search).get('currency');
    this.load(fromUrl || detectCurrency());
    if (!fromUrl && this.auth.authenticated()) {
      this.session.refresh().then(() => {
        const country = this.session.workspace()?.country;
        if (country) this.load(country === 'IN' ? 'INR' : 'USD');
      }).catch(() => {});
    }
  }

  protected setCurrency(code: string): void {
    this.load(code);
  }

  protected currencyLabel(code: string): string {
    return code === 'INR' ? '₹ INR' : code === 'USD' ? '$ USD' : code;
  }

  private load(currency: string): void {
    this.api.plans(currency).subscribe({
      next: (r) => {
        this.currency.set(r.currency);
        this.currencies.set([...r.currencies].sort((a, b) => (a === 'USD' ? -1 : b === 'USD' ? 1 : a.localeCompare(b))));
        this.plans.set(r.plans);
      },
      error: (e) => this.error.set(errorMessage(e)),
    });
  }
}
