import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, errorMessage } from '../../core/api.service';
import { AiProvider, AiSettings } from '../../core/models';
import { SessionService } from '../../core/session.service';
import { IconComponent } from '../../shared/icon.component';
import { AgoPipe, ToastService } from '../../shared/ui';

/**
 * Settings > AI: local model or a cloud provider with the workspace's own key.
 * Cloud AI only turns on after the key is checked (model list) and a test request passes.
 * Without it the workspace keeps working with the local model, or with retrieval and rules.
 */
@Component({
  selector: 'y-ai-settings',
  imports: [FormsModule, IconComponent, AgoPipe],
  template: `
    @if (!settings()) {
      <div class="skeleton" style="height: 320px"></div>
    } @else {
      @let s = settings()!;
      <div class="stack-lg">
        <!-- What is answering now -->
        <section class="card card-pad stack enter">
          <div class="row-wrap">
            <h2 class="grow-title">AI engine</h2>
            <span class="chip" [class]="modeChip()"><y-icon [name]="s.active.mode === 'RULES' ? 'book' : 'sparkles'" [size]="13" /> {{ modeLabel() }}</span>
          </div>
          <p class="muted">
            @switch (s.active.mode) {
              @case ('CLOUD') { Claims, comments, reply drafts and creator notes use <strong>{{ s.active.label }} · {{ s.active.model }}</strong>. If it fails, the local model takes over automatically. }
              @case ('LOCAL') { Everything runs on this server's local model <strong>{{ s.active.model }}</strong>. Nothing leaves your machine. }
              @default { No AI model is available, so Yudhix uses fact retrieval and rules: claims are matched to your knowledge base by keywords, comments are read with keyword rules. It works, with less nuance. }
            }
          </p>
          <div class="row-wrap subtle facts">
            <span><y-icon name="search" [size]="14" /> Fact search: {{ s.active.embeddings ? 'keywords + meaning (embeddings)' : 'keywords only (BM25)' }}</span>
            @if (s.active.mode === 'CLOUD' && s.validatedAt) { <span>· key checked {{ s.validatedAt | ago }}</span> }
          </div>
          @if (s.status === 'INVALID' && s.lastError) {
            <div class="callout callout-danger"><y-icon name="alert" [size]="15" /> The last cloud key was rejected: {{ s.lastError }}</div>
          }
        </section>

        <!-- Mode -->
        <section class="card card-pad stack enter" style="--i: 1">
          <h2>Where AI runs</h2>
          <div class="segmented mode" role="radiogroup" aria-label="AI mode">
            <button type="button" role="radio" [attr.aria-checked]="tab() === 'LOCAL'" [class.active]="tab() === 'LOCAL'" (click)="tab.set('LOCAL')">
              <y-icon name="monitor" [size]="15" /> Local
            </button>
            <button type="button" role="radio" [attr.aria-checked]="tab() === 'CLOUD'" [class.active]="tab() === 'CLOUD'" (click)="tab.set('CLOUD')">
              <y-icon name="globe" [size]="15" /> Cloud AI
            </button>
          </div>

          @if (tab() === 'LOCAL') {
            <p class="muted">
              The model runs on this server through Ollama: private, free, slower.
              @if (s.local.available) {
                <strong>{{ s.local.model }}</strong> is running.
                Meaning-based fact search: {{ s.local.embedModel ? s.local.embedModel + ' is installed' : 'off (run "ollama pull nomic-embed-text" to turn it on)' }}.
              } @else {
                The local model isn't running right now, so retrieval and rules are used.
              }
            </p>
            @if (s.mode === 'CLOUD' && canManage) {
              <div><button class="btn" type="button" (click)="useLocal()" [disabled]="busy()">Switch to local</button></div>
            } @else if (s.mode === 'LOCAL') {
              <p class="subtle"><y-icon name="checkCircle" [size]="14" /> This workspace uses local AI.</p>
            }
          } @else {
            <p class="muted">Use your own account with a cloud provider: much faster, reads every comment, costs per use on your provider's bill.
              The key is checked before anything switches over.</p>

            <div class="providers" role="radiogroup" aria-label="Provider">
              @for (p of providers(); track p.id) {
                <button type="button" role="radio" class="provider" [attr.aria-checked]="provider() === p.id" [class.active]="provider() === p.id"
                        [disabled]="!canManage" (click)="pickProvider(p.id)">
                  <strong>{{ p.label }}</strong>
                  <span class="subtle">{{ p.embeddings ? 'Chat + embeddings' : 'Chat (local embeddings)' }}</span>
                </button>
              }
            </div>

            @if (selected(); as p) {
              <div class="stack form">
                @if (p.needsBaseUrl) {
                  <div class="field">
                    <label for="ai-url">API base URL</label>
                    <input id="ai-url" class="input" [(ngModel)]="baseUrl" placeholder="http://localhost:1234/v1" [disabled]="!canManage" />
                    <span class="hint">Any server that speaks the OpenAI chat API: LM Studio, vLLM, LocalAI, a company gateway.</span>
                  </div>
                }
                <div class="field">
                  <label for="ai-key">API key</label>
                  <input id="ai-key" class="input mono" type="password" autocomplete="off" [(ngModel)]="apiKey" [disabled]="!canManage"
                         [placeholder]="s.hasKey && s.provider === p.id ? 'Saved key ' + s.keyHint + ' (paste a new one to replace it)' : 'Paste your ' + p.label + ' API key'" />
                  @if (p.keyUrl) { <span class="hint">Create one at <a [href]="p.keyUrl" target="_blank" rel="noopener">{{ p.keyUrl }}</a>. It's stored encrypted and never shown again.</span> }
                </div>
                <div class="row-wrap">
                  <button class="btn" type="button" (click)="checkKey()" [disabled]="!canManage || busy() || !canCheck()">
                    <y-icon name="check" [size]="15" /> {{ step() === 'checking' ? 'Checking…' : 'Check key' }}
                  </button>
                  @if (models().length) { <span class="subtle"><y-icon name="checkCircle" [size]="14" /> Key works · {{ models().length }} models</span> }
                </div>

                @if (models().length) {
                  <div class="field">
                    <label for="ai-model">Model</label>
                    <select id="ai-model" class="select input" [(ngModel)]="model" [disabled]="!canManage">
                      @for (m of models(); track m) { <option [value]="m">{{ m }}{{ m === suggested() ? ' (suggested)' : '' }}</option> }
                    </select>
                    <span class="hint">One model does everything. A faster, cheaper model is fine for most workspaces.
                      @if (embedModel()) { Embeddings: {{ embedModel() }}. } @else { This provider has no embeddings, so meaning-based fact search uses the local model if installed. }</span>
                  </div>
                  <div class="row-wrap">
                    <button class="btn btn-primary" type="button" (click)="turnOn()" [disabled]="!canManage || busy() || !model">
                      <y-icon name="sparkles" [size]="15" /> {{ step() === 'testing' ? 'Testing ' + model + '…' : 'Test and turn on' }}
                    </button>
                  </div>
                }
                @if (error()) {
                  <div class="callout callout-danger"><y-icon name="alert" [size]="15" /> <span>{{ error() }} <strong>Nothing was changed</strong>: the workspace keeps using {{ s.active.mode === 'CLOUD' ? s.active.label : 'local AI and rules' }}.</span></div>
                }
              </div>
            }

            @if (s.hasKey && canManage) {
              <hr class="divider" />
              <div class="row-wrap">
                <span class="subtle grow-title">Saved key for {{ providerLabel(s.provider) }} {{ s.keyHint }}</span>
                <button class="btn btn-sm btn-danger" type="button" (click)="removeKey()" [disabled]="busy()">Remove key</button>
              </div>
            }
          }
          @if (!canManage) { <p class="subtle">Only admins can change AI settings.</p> }
        </section>

        <!-- Privacy -->
        <section class="card card-pad stack enter" style="--i: 2">
          <h2>What stays here, what is sent</h2>
          <ul class="privacy">
            <li><y-icon name="lock" [size]="15" /><span><strong>Stays in your database, always:</strong> the knowledge base, all comments, replies, ideas, the fact index and its embeddings.</span></li>
            <li><y-icon name="send" [size]="15" /><span><strong>Sent to a cloud provider, per request:</strong> one claim with its top 3 matching facts, or a batch of comments with personal details masked, or the text of a fact to embed. Nothing else.</span></li>
            <li><y-icon name="shield" [size]="15" /><span><strong>Guards against made-up answers:</strong> no matching fact means "unverified" without asking the AI; the AI must quote the official source word for word; figures are compared by code; with cloud AI each claim is read twice and disagreements go to "Needs review".</span></li>
          </ul>
        </section>
      </div>
    }
  `,
  styles: `
    .grow-title { flex: 1; margin: 0; }
    .facts { font-size: 13px; gap: 6px; }
    .mode { align-self: flex-start; }
    .providers { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 10px; }
    .provider { display: flex; flex-direction: column; gap: 2px; text-align: left; padding: 12px 14px; border-radius: 12px;
      border: 1px solid var(--border); background: var(--surface); color: var(--text); font: inherit; cursor: pointer;
      &:hover:not(:disabled) { border-color: var(--border-strong); }
      &.active { border-color: var(--brand); box-shadow: 0 0 0 1px var(--brand); }
      .subtle { font-size: 12px; } }
    .form { margin-top: 4px; }
    .hint { font-size: 12px; color: var(--muted-text); overflow-wrap: anywhere; }
    select.input { padding: 0 12px; }
    .privacy { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 12px; font-size: 14px; line-height: 1.5;
      li { display: flex; gap: 10px; align-items: flex-start; }
      y-icon { margin-top: 3px; flex: none; color: var(--muted-text); } }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AiSettingsPage {
  private api = inject(ApiService);
  private toast = inject(ToastService);
  private session = inject(SessionService);

  protected readonly canManage = this.session.can('workspace.manage');
  protected readonly settings = signal<AiSettings | null>(null);
  protected readonly providers = signal<AiProvider[]>([]);
  protected readonly tab = signal<'LOCAL' | 'CLOUD'>('LOCAL');
  protected readonly provider = signal<string | null>(null);
  protected readonly models = signal<string[]>([]);
  protected readonly suggested = signal<string | null>(null);
  protected readonly embedModel = signal<string | null>(null);
  protected readonly step = signal<'idle' | 'checking' | 'testing'>('idle');
  protected readonly error = signal('');
  protected apiKey = '';
  protected baseUrl = '';
  protected model = '';

  protected readonly busy = computed(() => this.step() !== 'idle');
  protected readonly selected = computed(() => this.providers().find((p) => p.id === this.provider()) ?? null);
  protected readonly modeLabel = computed(() => {
    const a = this.settings()?.active;
    return !a ? '' : a.mode === 'CLOUD' ? `Cloud AI · ${a.label}` : a.mode === 'LOCAL' ? 'Local AI' : 'Retrieval and rules';
  });
  protected readonly modeChip = computed(() => {
    const m = this.settings()?.active.mode;
    return m === 'CLOUD' ? 'chip-brand' : m === 'LOCAL' ? 'chip-ok' : 'chip-outline';
  });

  constructor() {
    this.api.aiProviders().subscribe({ next: (r) => this.providers.set(r.providers), error: () => {} });
    this.api.aiSettings().subscribe({
      next: (s) => {
        this.apply(s);
        this.tab.set(s.mode);
        this.provider.set(s.provider);
        this.baseUrl = s.baseUrl ?? '';
        if (s.mode === 'CLOUD' && s.model) {
          this.models.set([s.model]);
          this.model = s.model;
        }
      },
      error: (e) => this.toast.error(errorMessage(e)),
    });
  }

  private apply(s: AiSettings): void {
    this.settings.set(s);
  }

  protected providerLabel(id: string | null): string {
    return this.providers().find((p) => p.id === id)?.label ?? id ?? '';
  }

  protected canCheck(): boolean {
    const p = this.selected();
    if (!p) return false;
    const savedKey = this.settings()?.hasKey && this.settings()?.provider === p.id;
    return (!!this.apiKey.trim() || !!savedKey || p.needsBaseUrl) && (!p.needsBaseUrl || !!this.baseUrl.trim());
  }

  protected pickProvider(id: string): void {
    if (this.provider() === id) return;
    this.provider.set(id);
    this.apiKey = '';
    this.models.set([]);
    this.model = '';
    this.error.set('');
  }

  /** Step 1: list models with the key. */
  protected checkKey(): void {
    const p = this.selected();
    if (!p) return;
    this.step.set('checking');
    this.error.set('');
    this.api.aiModels({ provider: p.id, api_key: this.apiKey.trim() || null, base_url: p.needsBaseUrl ? this.baseUrl.trim() : null }).subscribe({
      next: (r) => {
        this.step.set('idle');
        this.models.set(r.models);
        this.suggested.set(r.suggested);
        this.embedModel.set(r.embedModel);
        this.model = r.models.includes(this.model) ? this.model : r.suggested ?? r.models[0];
      },
      error: (e) => {
        this.step.set('idle');
        this.models.set([]);
        this.error.set(errorMessage(e));
      },
    });
  }

  /** Step 2: a test request on the chosen model; only a pass switches the workspace to cloud AI. */
  protected turnOn(): void {
    const p = this.selected();
    if (!p || !this.model) return;
    this.step.set('testing');
    this.error.set('');
    this.api
      .saveAiSettings({ mode: 'CLOUD', provider: p.id, model: this.model, api_key: this.apiKey.trim() || null, base_url: p.needsBaseUrl ? this.baseUrl.trim() : null })
      .subscribe({
        next: (s) => {
          this.step.set('idle');
          this.apiKey = '';
          this.apply(s);
          this.toast.show(`Cloud AI is on: ${p.label} · ${this.model}.`);
        },
        error: (e) => {
          this.step.set('idle');
          this.error.set(errorMessage(e));
          this.api.aiSettings().subscribe((s) => this.apply(s));
        },
      });
  }

  protected useLocal(): void {
    this.step.set('testing');
    this.api.saveAiSettings({ mode: 'LOCAL' }).subscribe({
      next: (s) => {
        this.step.set('idle');
        this.apply(s);
        this.toast.show('Switched to local AI. The cloud key stays saved for later.');
      },
      error: (e) => {
        this.step.set('idle');
        this.toast.error(errorMessage(e));
      },
    });
  }

  protected removeKey(): void {
    if (!confirm('Remove the saved API key? The workspace switches to local AI.')) return;
    this.api.removeAiKey().subscribe({
      next: (s) => {
        this.apply(s);
        this.models.set([]);
        this.toast.show('Key removed. Using local AI.');
      },
      error: (e) => this.toast.error(errorMessage(e)),
    });
  }
}
