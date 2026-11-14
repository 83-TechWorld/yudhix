import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { Subscription } from 'rxjs';
import { ApiService, errorMessage } from '../../core/api.service';
import { Report, ReportOptions, ReportRequest, ReportSentimentRow, ReportTone } from '../../core/models';
import { IconComponent } from '../../shared/icon.component';
import { ToastService } from '../../shared/ui';

const STORE_KEY = 'yudhix.reports.v1';
const TONE_CHIP: Record<string, string> = { High: 'chip-danger', Medium: 'chip-warn', Low: 'chip' };

interface TrendGeom {
  w: number; h: number; left: number; bottom: number;
  ticks: { y: number; label: string }[];
  cols: { x: number; w: number; label: string; total: number; segs: { y: number; h: number; color: string; title: string }[] }[];
  labels: { x: number; text: string }[];
}

/**
 * Business reports across workspaces (served by the separate yudhix-report service).
 * Pick who it's for, which workspaces and the period; the preview updates as you go, and the same
 * report downloads as a PDF.
 */
@Component({
  selector: 'y-reports',
  imports: [IconComponent],
  template: `
    <div class="page">
      <header class="page-head">
        <div>
          <h1>Reports</h1>
          <p>Business reports across your workspaces, ready to share with leadership.</p>
        </div>
        <button class="btn btn-primary" type="button" (click)="download()" [disabled]="!canRun() || downloading()">
          <y-icon [name]="downloading() ? 'loader' : 'download'" [class.spin]="downloading()" /> {{ downloading() ? 'Preparing PDF…' : 'Download PDF' }}
        </button>
      </header>

      @if (options() === null) {
        <div class="layout"><div class="skeleton" style="height: 520px"></div><div class="skeleton" style="height: 520px"></div></div>
      } @else {
        @let o = options()!;
        <div class="layout">
          <!-- ---------------- settings ---------------- -->
          <aside class="card card-pad settings" aria-label="Report settings">
            <section>
              <h2 class="label">Who is it for</h2>
              <div class="audiences" role="radiogroup" aria-label="Report type">
                @for (a of o.audiences; track a.id) {
                  <button type="button" role="radio" class="aud" [class.active]="audience() === a.id" [attr.aria-checked]="audience() === a.id"
                          (click)="pickAudience(a.id)">
                    <span class="aud-top"><strong>{{ a.label }}</strong>@if (audience() === a.id) { <y-icon name="check" [size]="14" /> }</span>
                    <span class="subtle">{{ a.for }}</span>
                  </button>
                }
              </div>
            </section>

            <section>
              <div class="row">
                <h2 class="label">Workspaces <span class="count">{{ selected().length }} of {{ o.workspaces.length }}</span></h2>
                <span class="spacer"></span>
                <button type="button" class="link" (click)="selectAll(selected().length < o.workspaces.length)">
                  {{ selected().length < o.workspaces.length ? 'Select all' : 'Clear' }}
                </button>
              </div>
              <div class="ws-list">
                @for (w of o.workspaces; track w.id) {
                  <label class="ws">
                    <input type="checkbox" [checked]="selected().includes(w.id)" (change)="toggleWorkspace(w.id)" />
                    <span class="ws-name">{{ w.name }}</span>
                    @if (w.isDemo) { <span class="chip chip-outline">Demo</span> }
                    <span class="chip">{{ w.roleLabel }}</span>
                  </label>
                }
              </div>
            </section>

            <section>
              <h2 class="label">Period</h2>
              <div class="segmented periods" role="group" aria-label="Period">
                @for (p of o.periods; track p.id) {
                  <button type="button" [class.active]="period() === p.id" [attr.aria-pressed]="period() === p.id" (click)="setPeriod(p.id)">{{ p.label }}</button>
                }
              </div>
            </section>

            <section>
              <div class="row">
                <h2 class="label">Sections <span class="count">{{ activeSections().length }}</span></h2>
                <span class="spacer"></span>
                @if (customSections()) { <button type="button" class="link" (click)="customSections.set(null)">Reset</button> }
              </div>
              <div class="sec-list">
                @for (s of o.sections; track s.id) {
                  <label class="sec" [title]="s.description">
                    <input type="checkbox" [checked]="activeSections().includes(s.id)" (change)="toggleSection(s.id)" />
                    <span>{{ s.title }}</span>
                  </label>
                }
              </div>
            </section>
          </aside>

          <!-- ---------------- preview ---------------- -->
          <div class="preview-wrap">
            @if (!selected().length) {
              <div class="card card-pad empty"><y-icon name="building" [size]="22" /><p>Pick at least one workspace to build a report.</p></div>
            } @else if (!activeSections().length) {
              <div class="card card-pad empty"><y-icon name="layers" [size]="22" /><p>Turn on at least one section.</p></div>
            } @else if (error()) {
              <div class="callout callout-danger"><y-icon name="alert" [size]="16" /> {{ error() }}</div>
            } @else if (report() === null) {
              <div class="card paper"><div class="skeleton" style="height: 140px; margin-bottom: 16px"></div><div class="skeleton" style="height: 320px"></div></div>
            } @else {
              @let r = report()!;
              <article class="card paper" [class.busy]="loading()" aria-live="polite">
                <header class="cover">
                  <p class="eyebrow">Yudhix · {{ r.audience.label }} report</p>
                  <h2>{{ r.title }}</h2>
                  <p class="lead">{{ r.audience.description }}</p>
                  <dl class="meta">
                    <div><dt>Prepared for</dt><dd>{{ r.audience.for }}</dd></div>
                    <div><dt>Period</dt><dd>{{ r.period.label }}{{ r.period.from ? ' · ' + day(r.period.from) + ' – ' + day(r.period.to) : '' }}</dd></div>
                    <div><dt>Workspaces</dt><dd>{{ workspaceNames(r) }}</dd></div>
                  </dl>
                </header>

                @for (s of r.sections; track s.id; let i = $index) {
                  <section class="rsec">
                    <h3>{{ i + 1 }}. {{ s.title }}</h3>
                    <p class="desc">{{ s.description }}</p>
                    @for (b of s.blocks; track $index) {
                      @switch (b.type) {
                        @case ('kpis') {
                          <div class="kpis">
                            @for (k of b.items; track k.label) {
                              <div class="kpi">
                                <span class="k-label">{{ k.label }}</span>
                                <span class="k-value" [class]="'tone-' + k.tone">{{ k.value }}</span>
                                @if (k.sub) { <span class="k-sub">{{ k.sub }}</span> }
                                @if (k.delta) { <span class="k-delta" [class]="'tone-' + k.delta.tone">{{ k.delta.text }}</span> }
                              </div>
                            }
                          </div>
                        }
                        @case ('findings') {
                          <ul class="findings">
                            @for (f of b.items; track $index) { <li><span class="dot" [style.background]="toneColor(f.tone)"></span>{{ f.text }}</li> }
                          </ul>
                        }
                        @case ('table') {
                          @if (b.title) { <h4>{{ b.title }}</h4> }
                          <div class="tbl-wrap">
                            <table class="tbl">
                              <thead><tr>@for (c of b.columns; track $index) { <th [class.num]="c.align === 'right'">{{ c.label }}</th> }</tr></thead>
                              <tbody>
                                @for (row of b.rows; track $index) {
                                  <tr>
                                    @for (cell of row; track $index; let ci = $index) {
                                      <td [class.num]="b.columns[ci]?.align === 'right'">
                                        @if (b.severityColumn === ci) { <span class="chip" [class]="severityChip(cell)">{{ cell }}</span> } @else { {{ cell }} }
                                      </td>
                                    }
                                  </tr>
                                }
                              </tbody>
                            </table>
                          </div>
                        }
                        @case ('bars') {
                          @if (b.title) { <h4>{{ b.title }}</h4> }
                          <div class="legend" aria-hidden="true">
                            <span><i style="background: var(--chart-neg)"></i>Negative</span>
                            <span><i style="background: var(--chart-neu)"></i>Neutral</span>
                            <span><i style="background: var(--chart-pos)"></i>Positive</span>
                          </div>
                          <div class="sbars">
                            @for (row of b.rows; track row.label) {
                              <div class="sbar-row">
                                <div class="sbar-label"><strong>{{ row.label }}</strong>@if (row.sub) { <span>{{ row.sub }}</span> }</div>
                                <div class="sbar" role="img" [attr.aria-label]="barLabel(row)">
                                  @if (row.negative) { <span [style.flex-grow]="row.negative" style="background: var(--chart-neg)" [title]="'Negative: ' + row.negative + ' (' + share(row, row.negative) + ')'"></span> }
                                  @if (row.neutral) { <span [style.flex-grow]="row.neutral" style="background: var(--chart-neu)" [title]="'Neutral: ' + row.neutral + ' (' + share(row, row.neutral) + ')'"></span> }
                                  @if (row.positive) { <span [style.flex-grow]="row.positive" style="background: var(--chart-pos)" [title]="'Positive: ' + row.positive + ' (' + share(row, row.positive) + ')'"></span> }
                                </div>
                                <span class="sbar-val">{{ share(row, row.negative) }} neg · {{ share(row, row.positive) }} pos</span>
                              </div>
                            }
                          </div>
                        }
                        @case ('trend') {
                          @if (b.title) { <h4>{{ b.title }}</h4> }
                          <div class="legend" aria-hidden="true">
                            <span><i style="background: var(--chart-neg)"></i>Negative</span>
                            <span><i style="background: var(--chart-neu)"></i>Neutral</span>
                            <span><i style="background: var(--chart-pos)"></i>Positive</span>
                          </div>
                          @let g = trendGeom(b.points);
                          <svg class="trend" [attr.viewBox]="'0 0 ' + g.w + ' ' + g.h" role="img" [attr.aria-label]="b.title || 'Sentiment over time'">
                            @for (t of g.ticks; track t.y) {
                              <line [attr.x1]="g.left" [attr.x2]="g.w" [attr.y1]="t.y" [attr.y2]="t.y" class="grid" />
                              <text [attr.x]="g.left - 6" [attr.y]="t.y + 3" class="axis" text-anchor="end">{{ t.label }}</text>
                            }
                            @for (c of g.cols; track $index) {
                              <g class="col">
                                <title>{{ c.label }}: {{ c.total }} total</title>
                                <rect [attr.x]="c.x - 2" [attr.y]="0" [attr.width]="c.w + 4" [attr.height]="g.h - g.bottom" class="hit" />
                                @for (s of c.segs; track $index) {
                                  <rect [attr.x]="c.x" [attr.y]="s.y" [attr.width]="c.w" [attr.height]="s.h" [attr.fill]="s.color" rx="1.5"><title>{{ s.title }}</title></rect>
                                }
                              </g>
                            }
                            @for (l of g.labels; track $index) {
                              <text [attr.x]="l.x" [attr.y]="g.h - g.bottom + 14" class="axis" text-anchor="middle">{{ l.text }}</text>
                            }
                          </svg>
                        }
                        @case ('note') { <p class="r-note">{{ b.text }}</p> }
                      }
                    }
                  </section>
                }
                <footer class="foot">Every number comes from the workspace data. Findings and risks are written by fixed rules, not by AI.</footer>
              </article>
            }
          </div>
        </div>
      }
    </div>
  `,
  styles: `
    .layout { display: grid; grid-template-columns: 320px minmax(0, 1fr); gap: 20px; align-items: start; > * { min-width: 0; } }
    .settings { position: sticky; top: calc(var(--topbar-h) + 16px); display: flex; flex-direction: column; gap: 22px;
      max-height: calc(100vh - var(--topbar-h) - 32px); overflow-y: auto; }
    .label { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; color: var(--text-3); margin: 0 0 8px; }
    .count { font-weight: 500; text-transform: none; letter-spacing: 0; margin-left: 4px; }
    .link { border: 0; background: none; color: var(--brand-text); font-size: 12.5px; font-weight: 550; cursor: pointer; padding: 0 0 8px; }
    .audiences { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
    .aud { text-align: left; border: 1px solid var(--border); background: var(--surface); border-radius: var(--radius); padding: 9px 10px;
      display: flex; flex-direction: column; gap: 2px; cursor: pointer; color: var(--text); font: inherit;
      transition: border-color var(--dur-2) ease, background var(--dur-2) ease;
      .subtle { font-size: 11.5px; line-height: 1.35; } }
    .aud:hover { border-color: var(--border-strong); }
    .aud.active { border-color: var(--brand); background: var(--brand-soft); }
    .aud-top { display: flex; align-items: center; justify-content: space-between; font-size: 13.5px; y-icon { color: var(--brand-text); } }
    .ws-list, .sec-list { display: flex; flex-direction: column; gap: 2px; }
    .ws, .sec { display: flex; align-items: center; gap: 8px; padding: 6px 4px; border-radius: var(--radius-sm); cursor: pointer; font-size: 13.5px; }
    .ws:hover, .sec:hover { background: var(--surface-2); }
    .ws-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    input[type=checkbox] { accent-color: var(--brand); width: 15px; height: 15px; margin: 0; flex: none; }
    .periods { display: grid; grid-template-columns: 1fr 1fr; width: 100%; button { justify-content: center; padding: 0 6px; } }

    .empty { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 48px 24px; color: var(--text-3); text-align: center; }
    .paper { padding: 32px 36px; transition: opacity var(--dur-2) ease; }
    .paper.busy { opacity: .55; }
    .cover { border-bottom: 1px solid var(--border); padding-bottom: 20px; margin-bottom: 8px;
      h2 { font-size: 26px; line-height: 1.2; margin: 4px 0 6px; letter-spacing: -.01em; }
      .eyebrow { color: var(--brand-text); margin: 0; } .lead { color: var(--text-2); margin: 0 0 14px; font-size: 14.5px; } }
    .meta { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 0;
      dt { font-size: 11.5px; color: var(--text-3); } dd { margin: 2px 0 0; font-weight: 550; font-size: 13.5px; } }
    .rsec { padding: 22px 0 6px; border-bottom: 1px solid var(--border);
      &:last-of-type { border-bottom: 0; }
      h3 { font-size: 17px; margin: 0 0 2px; } .desc { color: var(--text-3); margin: 0 0 14px; font-size: 13px; }
      h4 { font-size: 13.5px; margin: 16px 0 8px; } }
    .kpis { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 1px; background: var(--border);
      border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; margin-bottom: 14px; }
    .kpi { background: var(--surface); padding: 12px 14px; display: flex; flex-direction: column; gap: 2px; min-width: 0; }
    .k-label { font-size: 12px; color: var(--text-3); }
    .k-value { font-size: 24px; font-weight: 650; letter-spacing: -.01em; font-variant-numeric: tabular-nums; color: var(--text); }
    .k-sub { font-size: 12px; color: var(--text-3); }
    .k-delta { font-size: 12px; font-weight: 600; }
    .tone-good { color: var(--ok-text); } .tone-bad { color: var(--danger-text); } .tone-warn { color: var(--warn-text); }
    .k-value.tone-info { color: var(--text); } .k-delta.tone-info { color: var(--text-2); }
    .findings { list-style: none; padding: 0; margin: 0 0 10px; display: flex; flex-direction: column; gap: 8px;
      li { display: flex; gap: 10px; align-items: baseline; font-size: 14px; line-height: 1.5; } .dot { transform: translateY(-1px); } }
    .tbl-wrap { overflow-x: auto; margin-bottom: 10px; }
    .tbl { width: 100%; border-collapse: collapse; font-size: 13px;
      th { text-align: left; font-size: 11.5px; font-weight: 600; color: var(--text-2); padding: 7px 8px; border-bottom: 1px solid var(--border-strong); white-space: nowrap; }
      td { padding: 8px; border-bottom: 1px solid var(--border); vertical-align: top; }
      .num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
      tbody tr:hover td { background: var(--surface-2); } }
    .legend { display: flex; gap: 14px; font-size: 12px; color: var(--muted-text); margin: 0 0 10px;
      span { display: inline-flex; align-items: center; gap: 6px; } i { width: 10px; height: 10px; border-radius: 3px; display: inline-block; } }
    .sbars { display: flex; flex-direction: column; gap: 10px; margin-bottom: 12px; }
    .sbar-row { display: grid; grid-template-columns: minmax(120px, 200px) minmax(0, 1fr) 120px; gap: 12px; align-items: center; }
    .sbar-label { display: flex; flex-direction: column; min-width: 0; font-size: 13px;
      strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } span { font-size: 11.5px; color: var(--text-3); } }
    .sbar { display: flex; gap: 2px; height: 14px; border-radius: 4px; overflow: hidden;
      span { display: block; min-width: 3px; flex-basis: 0; cursor: default; } }
    .sbar-val { font-size: 12px; color: var(--text-2); font-variant-numeric: tabular-nums; text-align: right; }
    .trend { width: 100%; height: auto; display: block; margin-bottom: 8px; overflow: visible;
      .grid { stroke: var(--chart-grid); stroke-width: 1; } .axis { font-size: 10px; fill: var(--text-3); }
      .hit { fill: transparent; } .col:hover .hit { fill: var(--surface-2); } }
    .r-note { font-size: 12.5px; color: var(--text-3); margin: 6px 0 10px; line-height: 1.5; }
    .foot { margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border); font-size: 12px; color: var(--text-3); }
    .spin { animation: spin 1s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }

    @media (max-width: 1023px) {
      .layout { grid-template-columns: 1fr; }
      .settings { position: static; max-height: none; }
    }
    @media (max-width: 639px) {
      .paper { padding: 20px 16px; }
      .sbar-row { grid-template-columns: 1fr; gap: 4px; }
      .sbar-val { text-align: left; }
      .page-head .btn { width: 100%; justify-content: center; }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReportsPage {
  private api = inject(ApiService);
  private toast = inject(ToastService);

  protected readonly options = signal<ReportOptions | null>(null);
  protected readonly audience = signal('executive');
  protected readonly selected = signal<string[]>([]);
  protected readonly period = signal('90d');
  /** null = the audience's default sections */
  protected readonly customSections = signal<string[] | null>(null);
  protected readonly report = signal<Report | null>(null);
  protected readonly loading = signal(false);
  protected readonly downloading = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly activeSections = computed(() => {
    const custom = this.customSections();
    if (custom) return custom;
    return this.options()?.audiences.find((a) => a.id === this.audience())?.sections ?? [];
  });
  protected readonly canRun = computed(() => !!this.options() && this.selected().length > 0 && this.activeSections().length > 0);
  private readonly request = computed<ReportRequest>(() => ({
    audience: this.audience(),
    workspaceIds: this.selected(),
    period: this.period(),
    sections: this.customSections(),
  }));

  private timer: ReturnType<typeof setTimeout> | null = null;
  private inflight: Subscription | null = null;

  constructor() {
    inject(DestroyRef).onDestroy(() => {
      if (this.timer) clearTimeout(this.timer);
      this.inflight?.unsubscribe();
    });
    this.api.reportOptions().subscribe({
      next: (o) => {
        const saved = this.restore();
        const ids = o.workspaces.map((w) => w.id);
        const keep = (saved?.workspaceIds ?? []).filter((id) => ids.includes(id));
        // Default: every workspace (the point of a cross-workspace report)
        this.selected.set(keep.length ? keep : ids);
        if (saved?.audience && o.audiences.some((a) => a.id === saved.audience)) this.audience.set(saved.audience);
        this.period.set(saved?.period && o.periods.some((p) => p.id === saved.period) ? saved.period : o.defaultPeriod);
        if (saved?.sections?.length) this.customSections.set(saved.sections.filter((s) => o.sections.some((x) => x.id === s)));
        this.options.set(o);
      },
      error: (e) => {
        this.options.set({ audiences: [], sections: [], periods: [], defaultPeriod: '90d', workspaces: [] });
        this.error.set(errorMessage(e));
      },
    });
    // Rebuild the preview shortly after any change
    effect(() => {
      const req = this.request();
      if (!this.canRun()) return;
      this.save(req);
      if (this.timer) clearTimeout(this.timer);
      this.timer = setTimeout(() => this.load(req), 250);
    });
  }

  private load(req: ReportRequest): void {
    this.inflight?.unsubscribe();
    this.loading.set(true);
    this.error.set(null);
    this.inflight = this.api.reportPreview(req).subscribe({
      next: (r) => {
        this.report.set(r);
        this.loading.set(false);
      },
      error: (e) => {
        this.loading.set(false);
        this.error.set(errorMessage(e));
      },
    });
  }

  protected pickAudience(id: string): void {
    this.audience.set(id);
    this.customSections.set(null);
  }
  protected setPeriod(id: string): void {
    this.period.set(id);
  }
  protected toggleWorkspace(id: string): void {
    this.selected.update((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  }
  protected selectAll(all: boolean): void {
    this.selected.set(all ? (this.options()?.workspaces.map((w) => w.id) ?? []) : []);
  }
  protected toggleSection(id: string): void {
    const now = this.activeSections();
    this.customSections.set(now.includes(id) ? now.filter((s) => s !== id) : [...now, id]);
  }

  protected download(): void {
    if (!this.canRun()) return;
    this.downloading.set(true);
    this.api.reportPdf(this.request()).subscribe({
      next: (res) => {
        this.downloading.set(false);
        const name = /filename="([^"]+)"/.exec(res.headers.get('Content-Disposition') ?? '')?.[1] ?? 'Yudhix-report.pdf';
        const url = URL.createObjectURL(res.body!);
        const a = document.createElement('a');
        a.href = url;
        a.download = name;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 10_000);
        this.toast.show('Report downloaded.');
      },
      error: async (e) => {
        this.downloading.set(false);
        // The PDF call asks for a Blob, so an error body arrives as a Blob too
        let msg = errorMessage(e);
        if (e instanceof HttpErrorResponse && e.error instanceof Blob) {
          try {
            msg = JSON.parse(await e.error.text())?.detail ?? msg;
          } catch {
            /* keep the generic message */
          }
        }
        this.toast.error(msg);
      },
    });
  }

  // ---- view helpers
  protected day(iso: string): string {
    return new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
  }
  protected workspaceNames(r: Report): string {
    return r.workspaces.map((w) => w.name).join(', ');
  }
  protected toneColor(t: ReportTone): string {
    return { good: 'var(--ok)', warn: 'var(--warn)', bad: 'var(--danger)', info: 'var(--text-3)' }[t];
  }
  protected severityChip(v: string): string {
    return 'chip ' + (TONE_CHIP[v] ?? '');
  }
  protected share(r: ReportSentimentRow, v: number): string {
    const t = r.negative + r.neutral + r.positive;
    return t ? `${Math.round((100 * v) / t)}%` : '–';
  }
  protected barLabel(r: ReportSentimentRow): string {
    return `${r.label}: ${this.share(r, r.negative)} negative, ${this.share(r, r.neutral)} neutral, ${this.share(r, r.positive)} positive`;
  }

  protected trendGeom(points: ReportSentimentRow[]): TrendGeom {
    const w = 680, h = 210, left = 36, bottom = 22, top = 8;
    const plotH = h - bottom - top, plotW = w - left;
    const peak = Math.max(1, ...points.map((p) => p.negative + p.neutral + p.positive));
    const step = niceStep(peak);
    const ymax = Math.ceil(peak / step) * step;
    const y = (v: number) => top + plotH - (plotH * v) / ymax;
    const ticks = [];
    for (let v = 0; v <= ymax; v += step) ticks.push({ y: y(v), label: v >= 1000 ? `${v / 1000}K` : String(v) });
    const slot = plotW / Math.max(points.length, 1);
    const bw = Math.max(Math.min(slot * 0.7, 28), 2);
    const every = Math.max(1, Math.ceil(points.length / 10));
    const cols = points.map((p, i) => {
      const x = left + i * slot + (slot - bw) / 2;
      let base = 0;
      const segs = [];
      for (const [v, color, name] of [[p.negative, 'var(--chart-neg)', 'Negative'], [p.neutral, 'var(--chart-neu)', 'Neutral'], [p.positive, 'var(--chart-pos)', 'Positive']] as const) {
        if (!v) continue;
        const top2 = y(base + v);
        const hh = y(base) - top2;
        segs.push({ y: top2, h: Math.max(hh - (hh > 3 ? 1.5 : 0), 1), color, title: `${p.label} · ${name}: ${v}` });
        base += v;
      }
      return { x, w: bw, label: p.label, total: p.negative + p.neutral + p.positive, segs };
    });
    const labels = points.map((p, i) => ({ x: left + i * slot + slot / 2, text: p.label })).filter((_, i) => i % every === 0);
    return { w, h, left, bottom, ticks, cols, labels };
  }

  // ---- remember the last choice in this browser (a convenience only)
  private save(req: ReportRequest): void {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify(req));
    } catch {
      /* storage unavailable */
    }
  }
  private restore(): Partial<ReportRequest> | null {
    try {
      return JSON.parse(localStorage.getItem(STORE_KEY) ?? 'null');
    } catch {
      return null;
    }
  }
}

function niceStep(peak: number): number {
  const raw = peak / 4;
  const mag = Math.pow(10, Math.floor(Math.log10(Math.max(raw, 1))));
  for (const m of [1, 2, 2.5, 5, 10]) if (raw <= m * mag) return Math.max(1, Math.round(m * mag));
  return 10 * mag;
}
