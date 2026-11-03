import { Injectable, signal } from '@angular/core';
import Keycloak from 'keycloak-js';
import { environment } from '../../environments/environment';

/**
 * Sign-in through Keycloak: Authorization Code + PKCE (S256). Sign-up, login, password reset,
 * email verification and MFA all happen on Keycloak's (Yudhix-branded) pages, so the app never
 * handles passwords. Tokens live in memory only and are refreshed before they expire.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private kc = new Keycloak(environment.keycloak);

  /** True once init has finished (signed in or not). */
  readonly ready = signal(false);
  readonly authenticated = signal(false);
  /** Keycloak couldn't be reached. Public pages still work. */
  readonly unavailable = signal(false);

  async init(): Promise<void> {
    try {
      const ok = await this.kc.init({
        onLoad: 'check-sso',
        pkceMethod: 'S256',
        checkLoginIframe: false,
        silentCheckSsoRedirectUri: `${location.origin}/silent-check-sso.html`,
        messageReceiveTimeout: 4000,
      });
      this.authenticated.set(ok);
      this.hadSession = ok;
      this.kc.onTokenExpired = () => {
        this.refresh().then((fresh) => { if (!fresh) this.sessionEnded(); });
      };
      this.kc.onAuthLogout = () => this.sessionEnded();
    } catch (err) {
      console.warn('Keycloak is unreachable; continuing signed out.', err);
      this.unavailable.set(true);
    } finally {
      this.ready.set(true);
    }
  }

  /** Redirects to the Keycloak sign-in page, then back to `returnPath`. */
  login(returnPath = '/analyze'): Promise<void> {
    return this.kc.login({ redirectUri: this.url(returnPath) });
  }

  /** Redirects to the Keycloak sign-up page. New accounts land on onboarding. */
  register(returnPath = '/onboarding'): Promise<void> {
    return this.kc.register({ redirectUri: this.url(returnPath) });
  }

  logout(returnPath = '/'): Promise<void> {
    return this.kc.logout({ redirectUri: this.url(returnPath) });
  }

  /** Keycloak's account console: profile, password, MFA, active sessions. */
  accountUrl(): string {
    return this.kc.createAccountUrl({ redirectUri: this.url('/settings/workspace') });
  }

  /** A fresh access token (refreshed if it expires within 30s), or null when signed out. */
  async token(): Promise<string | null> {
    if (!this.kc.authenticated) return null;
    if (await this.refresh()) return this.kc.token ?? null;
    this.sessionEnded();
    return null;
  }

  /**
   * The session ended on the server (expired, signed out elsewhere, or Keycloak lost it).
   * Go back through sign-in once and return to the same page, instead of leaving every
   * screen stuck on "Sign in to continue". With a live Keycloak session this is a quick bounce.
   */
  sessionEnded(): void {
    this.authenticated.set(false);
    if (!this.hadSession || this.redirecting) return;
    // Loop guard: if the API rejects even a brand-new session (e.g. misconfigured issuer), don't bounce forever.
    try {
      const last = Number(sessionStorage.getItem('yudhix.reauthAt') || 0);
      if (Date.now() - last < 30_000) return;
      sessionStorage.setItem('yudhix.reauthAt', String(Date.now()));
    } catch { /* storage blocked: the in-memory flag still prevents repeats on this page */ }
    this.redirecting = true;
    this.login(location.pathname + location.search).catch(() => (this.redirecting = false));
  }

  private hadSession = false;
  private redirecting = false;
  private pending: Promise<boolean> | null = null;

  /** Refresh the token; one retry after a short pause covers Keycloak restarting. Shared by concurrent callers. */
  private refresh(): Promise<boolean> {
    this.pending ??= (async () => {
      for (const wait of [0, 2000]) {
        if (wait) await new Promise((r) => setTimeout(r, wait));
        try {
          await this.kc.updateToken(30);
          return true;
        } catch { /* retry once */ }
      }
      return false;
    })().finally(() => (this.pending = null));
    return this.pending;
  }

  private url(path: string): string {
    return `${location.origin}${path.startsWith('/') ? path : '/' + path}`;
  }
}
