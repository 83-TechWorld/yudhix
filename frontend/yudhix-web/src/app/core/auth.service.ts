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
      this.kc.onTokenExpired = () => {
        this.kc.updateToken(30).catch(() => this.authenticated.set(false));
      };
      this.kc.onAuthLogout = () => this.authenticated.set(false);
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
    try {
      await this.kc.updateToken(30);
      return this.kc.token ?? null;
    } catch {
      this.authenticated.set(false);
      return null;
    }
  }

  private url(path: string): string {
    return `${location.origin}${path.startsWith('/') ? path : '/' + path}`;
  }
}
