import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';
import { environment } from './environments/environment';
import { initNative } from './app/core/native';

/**
 * Runtime configuration. Container builds serve /config.json (written from environment variables
 * when the web container starts), so one image works in Docker, Kubernetes and Zoho Catalyst.
 * Empty values mean "same origin as the app" (everything behind one gateway). `ng serve` has no
 * config.json and keeps the defaults from environment.ts.
 */
async function loadRuntimeConfig(): Promise<void> {
  try {
    const res = await fetch('config.json', { cache: 'no-store' });
    if (!res.ok) return;
    const cfg = await res.json();
    const origin = location.origin;
    environment.apiUrl = (cfg.apiUrl || origin).replace(/\/$/, '');
    environment.keycloak = {
      url: (cfg.keycloakUrl || `${origin}/auth`).replace(/\/$/, ''),
      realm: cfg.keycloakRealm || environment.keycloak.realm,
      clientId: cfg.keycloakClientId || environment.keycloak.clientId,
    };
    if (cfg.salesEmail) environment.salesEmail = cfg.salesEmail;
  } catch {
    /* no runtime config: use build-time defaults */
  }
}

loadRuntimeConfig()
  .then(() => bootstrapApplication(App, appConfig))
  .then(() => initNative())
  .catch((err) => console.error(err));
