import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';
import { Permission, SessionService } from './session.service';

/** Signed-in users only. Others go to the Keycloak sign-in page and come back here. */
export const authGuard: CanActivateFn = async (_route, state) => {
  const auth = inject(AuthService);
  if (auth.authenticated()) return true;
  await auth.login(state.url);
  return false;
};

/** Signed in AND a member of at least one workspace; otherwise start onboarding. */
export const workspaceGuard: CanActivateFn = async () => {
  const session = inject(SessionService);
  const router = inject(Router);
  try {
    const me = session.me() ?? (await session.refresh());
    if (!me.workspaces.length) return router.parseUrl('/onboarding');
    if (!session.workspace()) await session.refresh();
    return true;
  } catch {
    return true; // API down: let the shell render its offline banner instead of looping
  }
};

/** Pages that need a permission in the current workspace (e.g. billing for admins). */
export function permissionGuard(permission: Permission): CanActivateFn {
  return () => {
    const session = inject(SessionService);
    return session.can(permission) || inject(Router).parseUrl('/settings/workspace');
  };
}
