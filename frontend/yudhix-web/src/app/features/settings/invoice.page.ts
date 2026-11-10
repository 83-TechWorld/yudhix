import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, effect, inject, input, signal, untracked } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService, errorMessage } from '../../core/api.service';
import { Invoice } from '../../core/models';
import { IconComponent } from '../../shared/icon.component';
import { MoneyPipe } from '../../shared/ui';

/** Printable invoice. "Download PDF" uses the browser's print-to-PDF. */
@Component({
  selector: 'y-invoice',
  imports: [RouterLink, MoneyPipe, DatePipe, IconComponent],
  template: `
    <div class="page page-narrow">
      <div class="row-wrap no-print toolbar">
        <a routerLink="/settings/billing" class="back"><y-icon name="arrowLeft" [size]="16" /> Billing</a>
        <span class="spacer"></span>
        <button class="btn" type="button" (click)="print()"><y-icon name="printer" [size]="16" /> Print / save PDF</button>
      </div>
      @if (error()) {
        <div class="callout callout-danger">{{ error() }}</div>
      } @else if (!inv()) {
        <div class="skeleton" style="height: 520px"></div>
      } @else {
        @let i = inv()!;
        <article class="card invoice">
          <header class="inv-head">
            <div>
              <div class="brand"><span class="mark">Y</span> Yudhix</div>
              <p class="subtle">Truth-first social intelligence</p>
            </div>
            <div class="meta">
              <h1>Invoice</h1>
              <div class="mono">{{ i.number }}</div>
              <span class="chip" [class.chip-ok]="i.status === 'PAID'" [class.chip-warn]="i.status === 'OPEN'">{{ i.status === 'OPEN' ? 'Payment due' : i.status }}</span>
            </div>
          </header>
          <section class="parties">
            <div><span class="label">Billed to</span><strong>{{ i.billTo?.name }}</strong><span>{{ i.billTo?.country }}</span></div>
            <div><span class="label">Issued</span><span>{{ i.issuedAt | date: 'mediumDate' }}</span></div>
            <div><span class="label">Due</span><span>{{ i.dueAt | date: 'mediumDate' }}</span></div>
            <div><span class="label">Service period</span><span>{{ i.periodStart | date: 'mediumDate' }} – {{ i.periodEnd | date: 'mediumDate' }}</span></div>
          </section>
          <table>
            <thead><tr><th>Description</th><th class="num">Qty</th><th class="num">Unit price</th><th class="num">Amount</th></tr></thead>
            <tbody>
              @for (l of i.lines; track $index) {
                <tr><td>{{ l.description }}</td><td class="num">{{ l.quantity }}</td><td class="num">{{ l.unitPrice | money: i.currency : 2 }}</td><td class="num">{{ l.amount | money: i.currency : 2 }}</td></tr>
              }
            </tbody>
            <tfoot>
              <tr><td colspan="3">Subtotal</td><td class="num">{{ i.subtotal | money: i.currency : 2 }}</td></tr>
              <tr><td colspan="3">{{ i.taxLabel }}</td><td class="num">{{ i.tax | money: i.currency : 2 }}</td></tr>
              <tr class="total"><td colspan="3">Total due</td><td class="num">{{ i.total | money: i.currency : 2 }}</td></tr>
            </tfoot>
          </table>
          <p class="subtle foot">Payment terms: net 30. Questions about this invoice? Reply to your billing email or contact your account manager.</p>
        </article>
      }
    </div>
  `,
  styles: `
    .toolbar { margin-bottom: 16px; }
    .back { display: inline-flex; gap: 6px; align-items: center; color: var(--text-2); font-weight: 600; }
    .invoice { padding: 40px; display: flex; flex-direction: column; gap: 28px; }
    @media (max-width: 640px) { .invoice { padding: 20px; } }
    .inv-head { display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
    .brand { display: flex; align-items: center; gap: 8px; font-weight: 800; font-size: 20px; }
    .mark { width: 30px; height: 30px; border-radius: 9px; display: grid; place-items: center; background: linear-gradient(135deg, var(--brand), #7c3aed); color: #fff; font-size: 15px; }
    .meta { text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
    .meta h1 { font-size: 26px; }
    .parties { display: grid; grid-template-columns: 2fr 1fr 1fr 1.6fr; gap: 16px; font-size: 14px; }
    .parties div { display: flex; flex-direction: column; gap: 2px; }
    .label { font-size: 12px; color: var(--text-3); text-transform: uppercase; letter-spacing: .05em; }
    @media (max-width: 640px) { .parties { grid-template-columns: 1fr 1fr; } }
    .table-scroll { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 14px; }
    th { text-align: left; font-size: 12px; color: var(--text-3); text-transform: uppercase; letter-spacing: .05em; padding: 8px 0; border-bottom: 2px solid var(--border); }
    td { padding: 10px 0; border-bottom: 1px solid var(--border); }
    .num { text-align: right; white-space: nowrap; padding-left: 12px; font-variant-numeric: tabular-nums; }
    tfoot td { border-bottom: 0; padding: 6px 0; color: var(--text-2); }
    tfoot .total td { font-size: 17px; font-weight: 750; color: var(--text); border-top: 2px solid var(--border); padding-top: 12px; }
    .foot { font-size: 13px; }
    @media print {
      .no-print { display: none !important; }
      .invoice { box-shadow: none; border: 0; padding: 0; }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InvoicePage {
  private api = inject(ApiService);
  readonly invoiceId = input.required<string>();
  protected readonly inv = signal<Invoice | null>(null);
  protected readonly error = signal('');

  constructor() {
    effect(() => {
      const id = this.invoiceId();
      untracked(() => this.api.invoice(id).subscribe({ next: (i) => this.inv.set(i), error: (e) => this.error.set(errorMessage(e)) }));
    });
  }

  protected print(): void {
    window.print();
  }
}
