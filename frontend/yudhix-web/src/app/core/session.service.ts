import { Injectable, effect, signal } from '@angular/core';
import { Role } from './models';

/** Demo identities until the SaaS/auth layer ships. Must match DEMO_USERS in yudhix-sense config.py. */
export const DEMO_USERS: Record<Role, { id: string; name: string; initials: string; title: string }> = {
  agent: { id: '11111111-1111-4111-8111-111111111111', name: 'Asha', initials: 'AS', title: 'Social agent' },
  approver: { id: '22222222-2222-4222-8222-222222222222', name: 'Ravi', initials: 'RV', title: 'Brand approver' },
};

export type Theme = 'system' | 'light' | 'dark';

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* private mode / storage blocked: preference just won't persist */
  }
}

@Injectable({ providedIn: 'root' })
export class SessionService {
  readonly role = signal<Role>(read('yudhix.role') === 'approver' ? 'approver' : 'agent');
  readonly theme = signal<Theme>((read('yudhix.theme') as Theme) || 'system');

  constructor() {
    effect(() => write('yudhix.role', this.role()));
    effect(() => {
      const theme = this.theme();
      write('yudhix.theme', theme);
      const root = document.documentElement;
      if (theme === 'system') root.removeAttribute('data-theme');
      else root.setAttribute('data-theme', theme);
    });
  }

  user() {
    return DEMO_USERS[this.role()];
  }

  toggleRole(): void {
    this.role.update((r) => (r === 'agent' ? 'approver' : 'agent'));
  }

  cycleTheme(): void {
    this.theme.update((t) => (t === 'system' ? 'light' : t === 'light' ? 'dark' : 'system'));
  }
}
