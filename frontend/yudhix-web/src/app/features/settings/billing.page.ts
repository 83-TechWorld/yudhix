import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { environment } from '../../../environments/environment';
import { ApiService, errorMessage } from '../../core/api.service';
import { BillingSummary, Invoice, Meter, Plan } from '../../core/models';
import { SessionService } from '../../core/session.service';
import { IconComponent } from '../../shared/icon.component';
import { EmptyStateComponent, MoneyPipe, ToastService } from '../../shared/ui';
import { quota } from '../public/pricing.page';

@Component({
  selector: 'y-billing',
  imports: [RouterLink, MoneyPipe, DatePipe, IconComponent, EmptyStateComponent],
  template: `
    @if (!summary()) {
      <div class="stack"><div class="skeleton" style="height: 160px"></div><div class="skeleton" style="height: 260px"></div></div>
    } @else {
      @let s = summary()!;
      <div class="stack-lg">
        <!-- Status -->
        <section class="card card-pad plan-card enter">
          <div class="plan-top">
            <div>
              <span class="eyebrow">Current plan</span>
              <h2>{{ s.plan.name }}
                @switch (s.status) {
                  @case ('TRIALING') { <span class="chip chip-brand">Trial · {{ daysLeft() }} days left</span> }
                  @case ('TRIAL_EXPIRED') { <span class="chip chip-danger">Trial ended</span> }
                  @case ('CANCELED') { <span class="chip chip-danger">Canceled</span> }
                  @default { <span class="chip chip-ok">Active</span> }
                }
              </h2>
              @if (s.status === 'ACTIVE') {
                <p class="muted">{{ s.plan.price | money: s.plan.currency : 0 }} / {{ s.plan.interval === 'YEAR' ? 'year' : 'month' }} · renews {{ s.periodEnd | date: 'mediumDate' }}</p>
              } @else if (s.status === 'TRIALING') {
                <p class="muted">Your trial ends {{ s.trialEndsAt | date: 'mediumDate' }}. Pick a plan any time; your data stays as it is.</p>
              } @else {
                <p class="muted">Reports stay readable. New analyses and posting are paused until you pick a plan.</p>
              }
            </div>
          </div>
          <div class="callout callout-info"><y-icon name="info" [size]="16" /><span>Billed in {{ s.plan.currency === 'INR' ? 'Indian rupees (₹), plus 18% GST' : 'US dollars ($)' }} · invoice billing, net 30. Online card payments aren't connected yet.</span></div>
        </section>

        <!-- Usage -->
        <section class="card card-pad stack enter" style="--i: 1">
          <div class="row"><h2>Usage this period</h2><span class="spacer"></span><span class="subtle">{{ s.periodStart | date: 'd MMM' }} – {{ s.periodEnd | date: 'd MMM y' }}</span></div>
          <div class="meters">
            @for (m of s.meters; track m.metric) {
              <div class="meter">
                <div class="row"><span>{{ m.label }}</span><span class="spacer"></span>
                  <strong>{{ m.used.toLocaleString() }}</strong><span class="subtle">/ {{ m.quota === null ? 'Unlimited' : m.quota.toLocaleString() }}</span>
                </div>
                <div class="bar"><span [class]="barClass(m)" [style.width.%]="m.percent === null ? 3 : Math.min(100, m.percent * 100)"></span></div>
                @if (m.percent !== null && m.percent >= 1) {
                  <span class="note bad">{{ m.hardLimit ? 'Limit reached: upgrade to continue.' : 'Over quota: billed as overage.' }}</span>
                } @else if (m.percent !== null && m.percent >= 0.8) {
                  <span class="note warn">{{ (m.percent * 100).toFixed(0) }}% used</span>
                }
              </div>
            }
          </div>
        </section>

        @if (s.upcoming) {
          <section class="card card-pad stack enter" style="--i: 2">
            <div class="row"><h2>Next invoice</h2><span class="spacer"></span><span class="subtle">{{ s.upcoming.date | date: 'mediumDate' }}</span></div>
            <table class="lines">
              @for (l of s.upcoming.lines; track l.description) {
                <tr><td>{{ l.description }}</td><td class="num">{{ l.amount | money: s.plan.currency : 2 }}</td></tr>
              }
              <tr class="sub"><td>{{ s.upcoming.taxLabel }}</td><td class="num">{{ s.upcoming.tax | money: s.plan.currency : 2 }}</td></tr>
              <tr class="total"><td>Estimated total</td><td class="num">{{ s.upcoming.total | money: s.plan.currency : 2 }}</td></tr>
            </table>
          </section>
        }

        <!-- Plans -->
        <section class="stack enter" style="--i: 3">
          <div class="row-wrap">
            <h2>Plans</h2><span class="spacer"></span>
            <div class="segmented">
              <button type="button" [class.active]="interval() === 'MONTH'" (click)="interval.set('MONTH')">Monthly</button>
              <button type="button" [class.active]="interval() === 'YEAR'" (click)="interval.set('YEAR')">Yearly · 2 months free</button>
            </div>
          </div>
          @if (!canManage) { <p class="subtle">Only workspace admins can change the plan.</p> }
          <div class="plans">
            @for (p of plans(); track p.id) {
              @let current = isCurrent(p);
              <div class="card card-pad plan" [class.current]="current">
                <div class="row"><strong>{{ p.name }}</strong>@if (current) { <span class="chip chip-ok">Current</span> }</div>
                <div class="price">{{ priceOf(p) | money: p.currency : 0 }}<span class="subtle"> / {{ interval() === 'YEAR' ? 'year' : 'month' }}</span></div>
                <ul class="subtle">
                  <li>{{ q(p.quotas.videos) }} video analyses</li>
                  <li>{{ q(p.quotas.comments) }} comments</li>
                  <li>{{ q(p.quotas.seats) }} team members</li>
                </ul>
                @if (canManage && !current) {
                  @if (confirming() === p.id) {
                    <div class="confirm stack enter-fade">
                      <span class="subtle">Switch now? You'll get an invoice for {{ priceOf(p) | money: p.currency : 0 }}@if (s.status === 'ACTIVE') {, minus credit for unused time on {{ s.plan.name }}}.</span>
                      <div class="row-wrap">
                        <button class="btn btn-primary btn-sm" type="button" (click)="change(p)" [disabled]="changing()">{{ changing() ? 'Switching…' : 'Confirm' }}</button>
                        <button class="btn btn-sm" type="button" (click)="confirming.set(null)">Cancel</button>
                      </div>
                    </div>
                  } @else if (p.id === 'ENTERPRISE') {
                    <div class="row-wrap">
                      <button class="btn btn-sm" type="button" (click)="confirming.set(p.id)">Switch</button>
                      <a class="btn btn-ghost btn-sm" [href]="salesHref">Talk to sales</a>
                    </div>
                  } @else {
                    <button class="btn btn-sm" [class.btn-primary]="p.highlighted" type="button" (click)="confirming.set(p.id)">{{ s.status === 'ACTIVE' ? 'Switch' : 'Choose' }} {{ p.name }}</button>
                  }
                }
              </div>
            }
          </div>
        </section>

        <!-- Invoices -->
        @if (canManage) {
          <section class="card enter" style="--i: 4">
            <div class="card-head"><h2>Invoices</h2></div>
            <div class="list">
              @for (i of invoices(); track i.id) {
                <a class="list-item clickable inv" [routerLink]="['/settings/billing/invoices', i.id]">
                  <y-icon name="file" [size]="18" />
                  <div class="grow"><strong>{{ i.number }}</strong><span class="subtle"> · {{ i.issuedAt | date: 'mediumDate' }}</span></div>
                  <span class="chip" [class.chip-ok]="i.status === 'PAID'" [class.chip-warn]="i.status === 'OPEN'">{{ i.status === 'OPEN' ? 'Due ' + (i.dueAt | date: 'd MMM') : i.status }}</span>
                  <strong class="num">{{ i.total | money: i.currency : 2 }}</strong>
                </a>
              } @empty {
                <y-empty icon="file" title="No invoices yet" text="Your first invoice appears when you choose a plan." />
              }
            </div>
          </section>
        }
      </div>
    }
  `,
  styles: `
    .plan-card { display: flex; flex-direction: column; gap: 14px; }
    .plan-card h2 { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; font-size: 22px; margin: 4px 0; }
    .meters { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px 28px; }
    @media (max-width: 640px) { .meters { grid-template-columns: 1fr; } }
    .meter { display: flex; flex-direction: column; gap: 6px; font-size: 14px; }
    .meter .row { gap: 6px; }
    .note { font-size: 12.5px; font-weight: 600; }
    .note.bad { color: var(--danger-text); }
    .note.warn { color: var(--warn-text); }
    .lines { width: 100%; border-collapse: collapse; font-size: 14px; }
    .lines td { padding: 8px 0; border-bottom: 1px solid var(--border); }
    .num { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
    .lines .sub td { color: var(--text-2); }
    .lines .total td { font-weight: 700; border-bottom: 0; }
    .plans { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
    @media (max-width: 760px) { .plans { grid-template-columns: 1fr; } }
    .plan { display: flex; flex-direction: column; gap: 10px; }
    .plan.current { border: 2px solid var(--ok); }
    .price { font-size: 24px; font-weight: 700; }
    .plan ul { margin: 0; padding-left: 18px; font-size: 13.5px; }
    .confirm { background: var(--surface-2); padding: 10px; border-radius: 10px; }
    .inv { align-items: center; color: var(--text); text-decoration: none; }
    .inv:hover { text-decoration: none; }
    .grow { flex: 1; min-width: 0; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BillingPage {
  private api = inject(ApiService);
  private toast = inject(ToastService);
  private session = inject(SessionService);
  protected readonly Math = Math;
  protected readonly canManage = this.session.can('billing.manage');
  protected readonly salesHref = `mailto:${environment.salesEmail}?subject=${encodeURIComponent('Yudhix Enterprise')}`;

  protected readonly summary = signal<BillingSummary | null>(null);
  protected readonly plans = signal<Plan[]>([]);
  protected readonly invoices = signal<Invoice[]>([]);
  protected readonly interval = signal<'MONTH' | 'YEAR'>('MONTH');
  protected readonly confirming = signal<string | null>(null);
  protected readonly changing = signal(false);
  protected readonly q = (n: number) => quota(n);

  protected readonly daysLeft = computed(() => {
    const end = this.summary()?.trialEndsAt;
    return end ? Math.max(0, Math.ceil((new Date(end).getTime() - Date.now()) / 86_400_000)) : 0;
  });

  constructor() {
    this.load();
  }

  private load(): void {
    this.api.billing().subscribe({
      next: (s) => {
        this.summary.set(s);
        if (s.status === 'ACTIVE') this.interval.set(s.plan.interval);
        // Plans in this workspace's billing currency (INR for India, USD elsewhere)
        if (this.plans()[0]?.currency !== s.plan.currency) {
          this.api.plans(s.plan.currency).subscribe({ next: (r) => this.plans.set(r.plans), error: () => {} });
        }
      },
      error: (e) => this.toast.error(errorMessage(e)),
    });
    if (this.canManage) this.api.invoices().subscribe({ next: (r) => this.invoices.set(r.invoices), error: () => {} });
  }

  protected isCurrent(p: Plan): boolean {
    const s = this.summary();
    return !!s && s.status === 'ACTIVE' && s.plan.id === p.id && s.plan.interval === this.interval();
  }

  protected priceOf(p: Plan): number {
    return this.interval() === 'YEAR' && p.yearlyPrice !== null ? p.yearlyPrice : p.monthlyPrice;
  }

  protected barClass(m: Meter): string {
    if (m.percent === null) return 'bar-ok';
    return m.percent >= 1 ? 'bar-bad' : m.percent >= 0.8 ? 'bar-warn' : 'bar-brand';
  }

  protected change(p: Plan): void {
    this.changing.set(true);
    this.api.changePlan(p.id, this.interval()).subscribe({
      next: async (s) => {
        this.changing.set(false);
        this.confirming.set(null);
        this.summary.set(s);
        this.toast.show(`You're on ${p.name}. An invoice was issued.`);
        this.load();
        await this.session.refresh();
      },
      error: (e) => {
        this.changing.set(false);
        this.toast.error(errorMessage(e));
      },
    });
  }
}
