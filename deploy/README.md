# Deploying Yudhix

The same four container images run everywhere: on your laptop with Docker Compose, on any Kubernetes cluster, and on Zoho Catalyst AppSail.

```
                      ┌──────────────────────────── one public origin ────────────────────────────┐
  Browser / mobile ──►│ gateway (nginx)                                                            │
                      │   /            ─► web       Angular PWA (nginx, static)       2–6 pods      │
                      │   /api, /health ─► api      yudhix-sense (FastAPI, stateless)  2–10 pods     │
                      │   /auth        ─► keycloak  sign-in / sign-up / tokens         1–2 pods      │
                      └────────────────────────────────────────────────────────────────────────────┘
                                   api, keycloak ─► PostgreSQL (in-cluster locally, managed in prod)
                                   api ─► Ollama (optional AI) · SMTP (Mailpit locally, ZeptoMail/any in prod)
```

| Image | Built from | Port | Notes |
|---|---|---|---|
| `yudhix/gateway` | `deploy/gateway` | 8080 | Routing, rate limits (API 30 r/s, login 10 r/s per IP), security headers, gzip. Upstreams via env vars. |
| `yudhix/web` | `frontend/yudhix-web` | 8080 | Writes `/config.json` from env at start (empty = same origin). |
| `yudhix/api` | `services/yudhix-sense` (repo-root context) | 8000 | Creates the whole schema on an empty database; migrations run under an advisory lock, so replicas can start together. Probes: `/healthz`, `/readyz`. |
| `yudhix/keycloak` | `deploy/keycloak` (repo-root context) | 8080, 9000 | Keycloak 25, Yudhix theme + realm baked in, served under `/auth`, production mode. |

All images run as non-root, and listen on `X_ZOHO_CATALYST_LISTEN_PORT` when set (Zoho), else `PORT`.

---

## 1. Docker (whole stack on your laptop)

```bash
./deploy/scripts/docker-up.sh          # build + start + wait  → http://localhost:8080
./deploy/scripts/docker-down.sh        # stop (add --wipe to delete the database volume)
API_REPLICAS=4 ./deploy/scripts/docker-up.sh   # scale the API
```

- App: http://localhost:8080 · Keycloak admin: http://localhost:8080/auth/admin (`admin` / `admin_local_pw`) · Emails: http://localhost:8026
- The AI model is the Ollama running on your Mac (`host.docker.internal:11434`).
- This is separate from the root `docker-compose.yml`, which only runs dev infrastructure for `ng serve` + `uvicorn --reload` (project `yudhix-stack`, ports 4200 / 8000 / 8180 / 8025).
- The containerized database starts empty: sign up, create a workspace, analyze a video. The PlayStation sample data lives only in your dev database.

## 2. Kubernetes on your laptop

```bash
./deploy/scripts/k8s-local.sh up       # build, deploy to the current kube context, port-forward → http://localhost:8081
./deploy/scripts/k8s-local.sh status
./deploy/scripts/k8s-local.sh down     # keep the database volume   ·   wipe = delete everything
```

The cluster must be able to use the locally built `yudhix/*:local` images:

| Cluster | Works as is? |
|---|---|
| Docker Desktop, **kubeadm** provisioning | ✅ shares Docker's images |
| Docker Desktop, **kind** provisioning | ❌ doesn't share images. Switch to kubeadm (Settings → Kubernetes), or push to a registry: `REGISTRY=ghcr.io/<you> ./deploy/scripts/k8s-local.sh up` |
| minikube | ✅ after `eval $(minikube docker-env)` |
| Rancher Desktop (dockerd) | ✅ |

`deploy/k8s/overlays/local` adds in-cluster Postgres and Mailpit, one replica per service and dev-only secrets.

## 3. Kubernetes in production

`deploy/k8s/overlays/production` works on any managed cluster (EKS, GKE, AKS, DigitalOcean, Linode, OVH, or k3s on VMs):

1. Push the images: `REGISTRY=ghcr.io/83-techworld TAG=v1.0.0 PLATFORM=linux/amd64 ./deploy/scripts/push-images.sh`
2. Edit `overlays/production/kustomization.yaml` (`PUBLIC_URL`, database host, SMTP, image names and tag) and `ingress.yaml` (your domain).
3. Create the managed Postgres databases `yudhix` and `keycloak`, and the `yudhix-secrets` secret (commands are in the kustomization file).
4. Install ingress-nginx and cert-manager, then `kubectl apply -k deploy/k8s/overlays/production`.

What you get:
- **Autoscaling:** HPAs scale the API 2–10 pods on CPU and memory, web 2–6, gateway 2–10.
- **No-downtime operations:** PodDisruptionBudgets keep pods running during node maintenance, and rolling updates use `maxUnavailable: 0`.
- **Spread:** topology spread places replicas across nodes.
- **Keycloak:** clustered over JGroups (2 replicas).
- **Locked-down network:** NetworkPolicies only let the gateway reach the services.
- **Hardened containers:** non-root, read-only root filesystem for the API, and all Linux capabilities dropped.

Run the AI model on a GPU node or a separate host and set `OLLAMA_URL`. Without it, Yudhix runs in rule-based mode (the robot sleeps).

## 4. Zoho Catalyst (AppSail)

See [zoho/README.md](zoho/README.md).

## Configuration reference

| Variable | Used by | Purpose |
|---|---|---|
| `PUBLIC_URL` | all | The URL users type (`https://app.example.com`). Keycloak's issuer is `$PUBLIC_URL/auth/realms/yudhix`. |
| `WEB_UPSTREAM`, `API_UPSTREAM`, `KEYCLOAK_UPSTREAM` | gateway | Where to route (`http://api:8000`, or `https://….catalystappsail.com` on Zoho). |
| `KEYCLOAK_ADMIN_PUBLIC` | gateway | `true` exposes `/auth/admin` (local only). |
| `API_RATE_LIMIT`, `LOGIN_RATE_LIMIT`, `MAX_BODY_SIZE` | gateway | Abuse protection (defaults `30r/s`, `10r/s`, `2m`). |
| `API_URL`, `KEYCLOAK_URL`, `SALES_EMAIL` | web | Leave the URLs empty behind the gateway (same origin). |
| `PG_HOST`, `PG_PORT`, `PG_DB`, `PG_USER`, `PG_PASSWORD` | api | Database. |
| `KEYCLOAK_ISSUER`, `KEYCLOAK_JWKS_URL` | api | Public issuer vs internal key URL. |
| `SMTP_*`, `OLLAMA_URL`, `YOUTUBE_API_KEY`, `AUTHOR_HMAC_KEY` | api | See the root README, section 8.2. |
| `KC_DB_URL`, `KC_DB_USERNAME`, `KC_DB_PASSWORD`, `KC_HOSTNAME`, `KEYCLOAK_ADMIN_PASSWORD` | keycloak | `KC_HOSTNAME` = `$PUBLIC_URL/auth`. |
| `KC_URL`, `APP_ORIGINS`, `KC_SMTP_*` | keycloak-setup job | Applies sign-up / PKCE / SMTP / origins (`tools/configure_realm.py`). |
