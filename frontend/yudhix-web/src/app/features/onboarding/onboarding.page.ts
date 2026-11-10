import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { Subscription, switchMap, takeWhile, timer } from 'rxjs';
import { ApiService, errorMessage } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { Country, Job, Me } from '../../core/models';
import { SessionService } from '../../core/session.service';
import { IconComponent } from '../../shared/icon.component';
import { ToastService } from '../../shared/ui';

type Step = 1 | 2 | 3;

const INDUSTRIES = ['Consumer electronics', 'Gaming', 'Automotive', 'Telecom', 'Retail & e-commerce', 'Beauty & personal care',
  'Food & beverage', 'Financial services', 'Travel & hospitality', 'Media & entertainment', 'Software / SaaS', 'Agency', 'Other'];
const TEAM_SIZES = ['1-10', '11-50', '51-200', '201-1000', '1000+'];

/** Sign-up → workspace → first product → first video → results, in a few minutes. */
@Component({
  selector: 'y-onboarding',
  imports: [FormsModule, RouterLink, IconComponent],
  templateUrl: './onboarding.page.html',
  styleUrl: './onboarding.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OnboardingPage {
  private api = inject(ApiService);
  private router = inject(Router);
  private toast = inject(ToastService);
  protected auth = inject(AuthService);
  protected session = inject(SessionService);

  /** ?new=1 when an existing user creates another workspace from the switcher. */
  readonly new = input<string | undefined>();

  protected readonly industries = INDUSTRIES;
  protected readonly teamSizes = TEAM_SIZES;
  protected readonly step = signal<Step>(1);
  protected readonly me = signal<Me | null>(null);
  protected readonly countries = signal<Country[]>([]);
  protected readonly busy = signal(false);
  protected readonly error = signal('');

  protected ws = { name: '', country: '', industry: '', teamSize: '' };
  protected product = { name: '', category: '' };
  protected fact = { title: '', statement: '' };
  protected readonly addFact = signal(false);
  protected video = { url: '', transcript: '' };
  protected readonly showTranscript = signal(false);

  protected readonly workspaceName = signal('');
  protected readonly productId = signal<string | null>(null);
  protected readonly job = signal<Job | null>(null);
  private poll?: Subscription;

  protected readonly firstName = computed(() => (this.me()?.user.name ?? '').split(' ')[0]);

  constructor() {
    inject(DestroyRef).onDestroy(() => this.poll?.unsubscribe());
    this.api.countries().subscribe({
      next: (r) => {
        this.countries.set(r.countries);
        if (!this.ws.country) this.ws.country = guessCountry(r.countries);
      },
      error: () => {},
    });
    this.session.refresh().then((me) => {
      this.me.set(me);
      if (me.workspaces.length && !this.new()) this.router.navigateByUrl('/analyze');
    }).catch((e) => this.error.set(errorMessage(e)));
  }

  protected createWorkspace(): void {
    if (this.ws.name.trim().length < 2) return this.error.set('Give your workspace a name.');
    if (!this.ws.country) return this.error.set('Pick the country your company is based in.');
    this.run(() =>
      this.api.createWorkspace({ name: this.ws.name.trim(), country: this.ws.country, industry: this.ws.industry || null, teamSize: this.ws.teamSize || null }),
      async (ws) => {
        await this.session.refresh();
        this.session.select(ws.id);
        this.workspaceName.set(ws.name);
        this.step.set(2);
      });
  }

  protected saveProduct(): void {
    if (this.product.name.trim().length < 2) return this.error.set('Name the product people talk about.');
    if (this.addFact() && (this.fact.title.trim().length < 3 || this.fact.statement.trim().length < 10)) {
      return this.error.set('Add a title and a full-sentence statement for the fact, or remove it.');
    }
    this.run(() => this.api.addProduct(this.product.name.trim(), this.product.category.trim() || null), (p) => {
      this.productId.set(p.id);
      if (this.addFact()) {
        this.api.addKnowledge({ title: this.fact.title.trim(), statement: this.fact.statement.trim(), category: p.category || 'General' })
          .subscribe({ error: (e) => this.toast.error(errorMessage(e)) });
      }
      this.step.set(3);
    });
  }

  protected analyze(): void {
    if (!this.video.url.trim()) return this.error.set('Paste a YouTube link.');
    this.run(() => this.api.analyze({ video_url: this.video.url.trim(), transcript: this.video.transcript.trim() || null, product_id: this.productId() }), (job) => {
      this.job.set(job);
      this.poll = timer(0, 1500)
        .pipe(switchMap(() => this.api.job(job.id)), takeWhile((j) => j.status === 'QUEUED' || j.status === 'RUNNING', true))
        .subscribe({ next: (j) => this.job.set(j), error: () => {} });
    });
  }

  protected joinDemo(): void {
    this.run(() => this.api.joinDemo(), async (ws) => {
      await this.session.refresh();
      this.session.select(ws.id);
      this.router.navigateByUrl('/videos');
    });
  }

  protected finish(path = '/analyze'): void {
    this.router.navigateByUrl(path);
  }

  private run<T>(call: () => import('rxjs').Observable<T>, done: (v: T) => void | Promise<void>): void {
    this.error.set('');
    this.busy.set(true);
    call().subscribe({
      next: async (v) => {
        try {
          await done(v);
        } finally {
          this.busy.set(false);
        }
      },
      error: (e) => {
        this.busy.set(false);
        this.error.set(errorMessage(e));
      },
    });
  }
}

/** Pre-select the country from the browser's locale when it's one we support. */
function guessCountry(countries: Country[]): string {
  const region = (navigator.language.split('-')[1] ?? '').toUpperCase();
  return countries.find((c) => c.code === region)?.code ?? countries[0]?.code ?? '';
}
