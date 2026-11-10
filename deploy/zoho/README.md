# Yudhix on Zoho Catalyst

**What Zoho offers:** Zoho has no managed Kubernetes. Its container hosting is **Catalyst AppSail**, which runs OCI images as managed apps ("custom runtime"). Each Yudhix image becomes one AppSail app, and the gateway app is the public front door.

Catalyst rules that shaped the images ([AppSail custom runtimes](https://docs.catalyst.zoho.com/en/serverless/help/appsail/custom-runtimes/deploy-from-cli), [execution](https://docs.catalyst.zoho.com/en/serverless/help/appsail/key-concepts/appsail-execution/), [configuration](https://docs.catalyst.zoho.com/en/serverless/help/appsail/appsail-configurations)):
- **Architecture:** images must be `linux/amd64`. The script builds them with `PLATFORM=linux/amd64`.
- **Port:** apps listen on `X_ZOHO_CATALYST_LISTEN_PORT`. All four Yudhix images do this automatically.
- **Memory:** up to **2 GB** per app (128 MB to 2 GB). Keycloak sizes its JVM to the limit, so give it 2 GB.
- **Config:** environment variables are set per app in the console.
- **No PostgreSQL:** use a managed Postgres in the same region (for example AWS RDS / Aurora in Mumbai, Azure, Neon or Supabase), with TLS required.
- **No GPU:** the AI model (Ollama) can't run on AppSail. Point `OLLAMA_URL` at a GPU VM, or run in rule-based mode.

## Topology

```
custom domain app.example.com ─► yudhix-gateway (AppSail, 256–512 MB)
                                   ├─ /      ─► https://<yudhix-web>.catalystappsail.com       (128–256 MB)
                                   ├─ /api   ─► https://<yudhix-api>.catalystappsail.com       (1 GB)
                                   └─ /auth  ─► https://<yudhix-keycloak>.catalystappsail.com  (2 GB)
yudhix-api, yudhix-keycloak ─► managed PostgreSQL (TLS)
email ─► Zoho ZeptoMail SMTP (smtp.zeptomail.in:587, STARTTLS)
```

## Steps

1. **Database:** create a Postgres 16 instance with databases `yudhix` and `keycloak` and one user that owns both. The API creates the whole schema on first start.
2. **Deploy the images:**
   ```bash
   npm install -g zcatalyst-cli && catalyst login
   catalyst init                 # in a new folder for the Catalyst project
   /path/to/yudhix/deploy/zoho/deploy-catalyst.sh
   ```
   The script builds amd64 images, saves them as `.tar.gz` and runs `catalyst deploy appsail --name yudhix-<app> --source docker-archive://…`. Without the CLI it prints those commands. You can also push the images to Docker Hub / Amazon ECR / Google Artifact Registry and pick them in the Catalyst console.
3. **Environment variables** (Catalyst console → AppSail → each app → Configuration). Replace the `<…>` values:

   **yudhix-keycloak** (2 GB)
   ```
   KC_DB_URL=jdbc:postgresql://<db-host>:5432/keycloak?sslmode=require
   KC_DB_USERNAME=<db-user>   KC_DB_PASSWORD=<db-password>
   KC_HOSTNAME=https://app.example.com/auth
   KEYCLOAK_ADMIN=admin       KEYCLOAK_ADMIN_PASSWORD=<strong-password>
   ```
   **yudhix-api** (1 GB)
   ```
   PG_HOST=<db-host>  PG_PORT=5432  PG_DB=yudhix  PG_USER=<db-user>  PG_PASSWORD=<db-password>
   KEYCLOAK_ISSUER=https://app.example.com/auth/realms/yudhix
   KEYCLOAK_JWKS_URL=https://<yudhix-keycloak-url>/auth/realms/yudhix/protocol/openid-connect/certs
   APP_URL=https://app.example.com   CORS_ORIGINS=https://app.example.com
   SMTP_HOST=smtp.zeptomail.in  SMTP_PORT=587  SMTP_STARTTLS=true  SMTP_USER=emailapikey  SMTP_PASSWORD=<zeptomail-token>
   SMTP_FROM=Yudhix <no-reply@your-domain.com>
   AUTHOR_HMAC_KEY=<openssl rand -hex 32>   DEMO_WORKSPACE_JOIN=false   WEB_CONCURRENCY=2
   OLLAMA_URL=<optional AI host>            YOUTUBE_API_KEY=<optional>
   ```
   **yudhix-web** (256 MB): `SALES_EMAIL=sales@your-domain.com`
   **yudhix-gateway** (512 MB)
   ```
   WEB_UPSTREAM=https://<yudhix-web-url>
   API_UPSTREAM=https://<yudhix-api-url>
   KEYCLOAK_UPSTREAM=https://<yudhix-keycloak-url>
   ```
4. **Custom domain:** map `app.example.com` to **yudhix-gateway** in the Catalyst console, so TLS is handled by Catalyst.
5. **Realm settings (once):** from any machine with Python:
   ```bash
   KC_URL=https://<yudhix-keycloak-url>/auth KC_ADMIN_PASSWORD=<strong-password> \
   APP_ORIGINS=https://app.example.com,capacitor://localhost,http://localhost \
   KC_SMTP_HOST=smtp.zeptomail.in KC_SMTP_PORT=587 KC_SMTP_STARTTLS=true \
   KC_SMTP_USER=emailapikey KC_SMTP_PASSWORD=<zeptomail-token> KC_SMTP_FROM=no-reply@your-domain.com \
   python3 keycloak/configure_realm.py
   ```
6. **Mobile apps:** in `frontend/yudhix-web/src/environments/environment.prod.ts`, set `apiUrl: 'https://app.example.com'` and `keycloak.url: 'https://app.example.com/auth'`. The web build reads `/config.json` instead.

## Scaling and limits

- **Stateless services:** the API, web and gateway keep no state, so you can run more instances of each. Configure instance scaling for each app in the Catalyst console.
- **Keycloak:** run one instance on AppSail. Several instances need a clustered cache, which needs pod-to-pod networking that AppSail doesn't provide. For HA Keycloak, use Kubernetes (`deploy/k8s/overlays/production`) or a managed identity service.
- **Analysis jobs:** they run inside the API instance that received them. If that instance restarts mid-analysis, start the analysis again. A separate worker queue is on the roadmap.
- **If you need real Kubernetes:** the `production` overlay runs unchanged on any managed cluster. You could, for example, keep Zoho for email (ZeptoMail), CRM and Desk, and host the containers on a managed Kubernetes provider.

> These steps follow Catalyst's published AppSail documentation but haven't been run against a live Catalyst account from this repository. Check memory and scaling options in your console.
