import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, errorMessage } from '../../core/api.service';
import { Knowledge } from '../../core/models';
import { IconComponent } from '../../shared/icon.component';
import { AgoPipe, EmptyStateComponent, ToastService } from '../../shared/ui';

@Component({
  selector: 'y-knowledge',
  imports: [FormsModule, IconComponent, EmptyStateComponent, AgoPipe],
  template: `
    <div class="page page-narrow">
      <header class="page-head">
        <div>
          <span class="eyebrow">Ground truth</span>
          <h1>Knowledge base</h1>
          <p>The official facts Yudhix checks creator claims against. Better sources mean better verdicts.</p>
        </div>
        <button class="btn btn-primary" type="button" (click)="openForm()"><y-icon name="plus" /> Add a fact</button>
      </header>

      <div class="search toolbar">
        <y-icon name="search" />
        <input class="input" [ngModel]="q()" (ngModelChange)="q.set($event)" placeholder="Search policies, specs, clauses" aria-label="Search knowledge" />
      </div>

      @if (items() === null) {
        <div class="stack">@for (i of [1, 2, 3]; track i) { <div class="skeleton" style="height: 120px"></div> }</div>
      } @else if (!groups().length) {
        <div class="card">
          <y-empty icon="book" title="No facts yet" text="Add your product specs, policies and FAQs so claims can be checked.">
            <button class="btn btn-primary" type="button" (click)="openForm()">Add the first fact</button>
          </y-empty>
        </div>
      } @else {
        @for (g of groups(); track g.category) {
          <section class="group">
            <h2 class="eyebrow">{{ g.category }} · {{ g.items.length }}</h2>
            <div class="stack">
              @for (k of g.items; track k.id) {
                <article class="card card-pad doc">
                  <div class="row-wrap">
                    <h3>{{ k.title }}</h3>
                    @if (k.clauseRef) { <span class="chip chip-outline mono">{{ k.clauseRef }}</span> }
                    <span class="spacer"></span>
                    @if (k.usedByClaims) { <span class="chip chip-brand">Cited by {{ k.usedByClaims }} claims</span> }
                    <button class="btn btn-ghost btn-icon btn-sm" type="button" (click)="remove(k)" [attr.aria-label]="'Delete ' + k.title"><y-icon name="trash" [size]="16" /></button>
                  </div>
                  <p class="statement">{{ k.statement }}</p>
                  <div class="subtle">
                    @if (k.productName) { {{ k.productName }} · }
                    @if (k.source) { Source: {{ k.source }} · }
                    Verified {{ k.verifiedAt | ago }}
                  </div>
                </article>
              }
            </div>
          </section>
        }
      }
    </div>

    @if (formOpen()) {
      <div class="sheet-backdrop" (click)="formOpen.set(false)"></div>
      <aside class="sheet" role="dialog" aria-modal="true" aria-labelledby="kf-title">
        <div class="sheet-head">
          <h2 id="kf-title" style="flex: 1">Add an official fact</h2>
          <button class="btn btn-ghost btn-icon" type="button" (click)="formOpen.set(false)" aria-label="Close"><y-icon name="x" /></button>
        </div>
        <form class="sheet-body stack" id="kform" (ngSubmit)="save()">
          <div class="field">
            <label for="kt">Title</label>
            <input id="kt" name="title" class="input" [(ngModel)]="form.title" required placeholder="e.g. PS5 Disc Drive Offline Policy" />
          </div>
          <div class="field">
            <label for="ks">Official statement</label>
            <textarea id="ks" name="statement" class="textarea" rows="6" [(ngModel)]="form.statement" required
              placeholder="Write exactly what your company officially states. Be specific: numbers, conditions, dates."></textarea>
            <span class="hint">Write one clear fact per entry. The fact-checker quotes this text back to creators and commenters.</span>
          </div>
          <div class="grid-2">
            <div class="field">
              <label for="kc">Category</label>
              <input id="kc" name="category" class="input" [(ngModel)]="form.category" placeholder="Hardware, Policy, Pricing…" list="cats" />
              <datalist id="cats">@for (g of groups(); track g.category) { <option [value]="g.category"></option> }</datalist>
            </div>
            <div class="field">
              <label for="kr">Clause / reference</label>
              <input id="kr" name="clauseRef" class="input" [(ngModel)]="form.clauseRef" placeholder="e.g. HW-DISC-01" />
            </div>
          </div>
          <div class="field">
            <label for="ksrc">Source</label>
            <input id="ksrc" name="source" class="input" [(ngModel)]="form.source" placeholder="URL or document name" />
          </div>
          @if (formError()) { <div class="callout callout-danger">{{ formError() }}</div> }
        </form>
        <div class="sheet-foot">
          <button class="btn" type="button" (click)="formOpen.set(false)">Cancel</button>
          <button class="btn btn-primary" type="submit" form="kform" [disabled]="saving()" style="flex: 1">{{ saving() ? 'Saving…' : 'Add fact' }}</button>
        </div>
      </aside>
    }
  `,
  styles: `
    .toolbar { margin-bottom: 20px; }
    .group { margin-bottom: 24px; }
    .group h2 { margin-bottom: 10px; }
    .doc { display: flex; flex-direction: column; gap: 8px; }
    .statement { color: var(--text-2); }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KnowledgePage {
  private api = inject(ApiService);
  private toast = inject(ToastService);

  protected readonly items = signal<Knowledge[] | null>(null);
  protected readonly q = signal('');
  protected readonly formOpen = signal(false);
  protected readonly saving = signal(false);
  protected readonly formError = signal('');
  protected form = { title: '', statement: '', category: '', clauseRef: '', source: '' };

  protected readonly groups = computed(() => {
    const q = this.q().trim().toLowerCase();
    const map = new Map<string, Knowledge[]>();
    for (const k of this.items() ?? []) {
      const hay = `${k.title} ${k.statement} ${k.clauseRef ?? ''} ${k.category}`.toLowerCase();
      if (q && !hay.includes(q)) continue;
      map.set(k.category, [...(map.get(k.category) ?? []), k]);
    }
    return [...map.entries()].map(([category, items]) => ({ category, items }));
  });

  constructor() {
    this.load();
  }

  private load(): void {
    this.api.knowledge().subscribe({
      next: (r) => this.items.set(r.knowledge),
      error: (e) => {
        this.items.set([]);
        this.toast.error(errorMessage(e));
      },
    });
  }

  protected openForm(): void {
    this.form = { title: '', statement: '', category: '', clauseRef: '', source: '' };
    this.formError.set('');
    this.formOpen.set(true);
  }

  protected save(): void {
    if (this.form.title.trim().length < 3 || this.form.statement.trim().length < 10) {
      this.formError.set('Add a title and an official statement (at least a full sentence).');
      return;
    }
    this.saving.set(true);
    this.api
      .addKnowledge({
        title: this.form.title.trim(),
        statement: this.form.statement.trim(),
        category: this.form.category.trim() || 'General',
        clauseRef: this.form.clauseRef.trim() || undefined,
        source: this.form.source.trim() || undefined,
      })
      .subscribe({
        next: (k) => {
          this.saving.set(false);
          this.formOpen.set(false);
          this.items.update((list) => [...(list ?? []), k]);
          this.toast.show('Fact added. Re-analyze a video to use it.');
        },
        error: (e) => {
          this.saving.set(false);
          this.formError.set(errorMessage(e));
        },
      });
  }

  protected remove(k: Knowledge): void {
    const warn = k.usedByClaims ? ` It's cited by ${k.usedByClaims} claims, which will lose their source.` : '';
    if (!confirm(`Delete "${k.title}"?${warn}`)) return;
    this.api.deleteKnowledge(k.id).subscribe({
      next: () => {
        this.items.update((list) => (list ?? []).filter((x) => x.id !== k.id));
        this.toast.show('Deleted.');
      },
      error: (e) => this.toast.error(errorMessage(e)),
    });
  }
}
