import { HttpClient } from '@angular/common/http';
import { Injectable, computed, effect, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../environments/environment';
import { Me, WorkspaceRole, WorkspaceSummary } from './models';

export type Theme = 'system' | 'light' | 'dark';
export type Permission = 'workspace.manage' | 'team.manage' | 'billing.manage' | 'content.write' | 'reply.approve';

/** Mirrors PERMISSIONS in services/yudhix-sense/app/platform/auth.py. The API is the real gate. */
export const PERMISSIONS: Record<Permission, WorkspaceRole[]> = {
  'workspace.manage': ['admin'],
  'team.manage': ['admin'],
  'billing.manage': ['admin'],
  'content.write': ['admin', 'approver', 'agent'],
  'reply.approve': ['admin', 'approver'],
};

export const ROLE_INFO: Record<WorkspaceRole, { label: string; description: string }> = {
  admin: { label: 'Admin', description: 'Everything, including workspace settings, team and billing.' },
  approver: { label: 'Approver', description: 'Reviews and approves replies, plus everything an agent can do.' },
  agent: { label: 'Agent', description: 'Analyzes videos, manages knowledge, drafts and posts replies.' },
  analyst: { label: 'Analyst', description: 'Read-only access to reports, inbox and insights.' },
};

const WS_KEY = 'yudhix.workspace';

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string | null): void {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    /* storage blocked: the choice just won't persist */
  }
}

/** The signed-in user, their workspaces and the one they're working in. */
@Injectable({ providedIn: 'root' })
export class SessionService {
  private http = inject(HttpClient);

  readonly me = signal<Me | null>(null);
  readonly workspaceId = signal<string | null>(read(WS_KEY));
  readonly theme = signal<Theme>((read('yudhix.theme') as Theme) || 'system');

  readonly user = computed(() => this.me()?.user ?? null);
  readonly workspaces = computed(() => this.me()?.workspaces ?? []);
  readonly workspace = computed<WorkspaceSummary | null>(
    () => this.workspaces().find((w) => w.id === this.workspaceId()) ?? null,
  );
  readonly role = computed<WorkspaceRole>(() => this.workspace()?.role ?? 'analyst');
  readonly initials = computed(() => initials(this.user()?.name || this.user()?.email || '?'));

  constructor() {
    effect(() => write(WS_KEY, this.workspaceId()));
    effect(() => {
      const theme = this.theme();
      write('yudhix.theme', theme);
      const root = document.documentElement;
      if (theme === 'system') root.removeAttribute('data-theme');
      else root.setAttribute('data-theme', theme);
    });
  }

  can(permission: Permission): boolean {
    return PERMISSIONS[permission].includes(this.role());
  }

  /** Loads /me and makes sure a valid workspace is selected (or none, if the user has none). */
  async refresh(): Promise<Me> {
    const me = await firstValueFrom(this.http.get<Me>(`${environment.apiUrl}/api/v1/me`));
    this.me.set(me);
    if (!me.workspaces.some((w) => w.id === this.workspaceId())) {
      this.workspaceId.set(me.workspaces.find((w) => !w.isDemo)?.id ?? me.workspaces[0]?.id ?? null);
    }
    return me;
  }

  select(workspaceId: string): void {
    this.workspaceId.set(workspaceId);
  }

  clear(): void {
    this.me.set(null);
    this.workspaceId.set(null);
  }

  cycleTheme(): void {
    this.theme.update((t) => (t === 'system' ? 'light' : t === 'light' ? 'dark' : 'system'));
  }
}

export function initials(name: string): string {
  const parts = name.replace(/@.*/, '').split(/[\s._-]+/).filter(Boolean);
  return ((parts[0]?.[0] ?? '?') + (parts[1]?.[0] ?? '')).toUpperCase();
}

export function trialDaysLeft(ws: WorkspaceSummary | null): number | null {
  if (!ws?.trialEndsAt || ws.subscriptionStatus !== 'TRIALING') return null;
  return Math.max(0, Math.ceil((new Date(ws.trialEndsAt).getTime() - Date.now()) / 86_400_000));
}
