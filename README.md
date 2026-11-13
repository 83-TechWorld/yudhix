# Yudhix

**Truth-first social comment intelligence for brands.**

When a creator's video about your product goes viral and the comments turn angry, Yudhix answers one question before anyone replies: **is the anger caused by a real product problem, or by something the creator got wrong?** It checks the video's claims against your official facts, links each comment to the claim that triggered it, and runs a reviewed reply workflow.

Built as a multi-tenant SaaS: companies sign up, create a workspace per brand, invite their team and pick a plan. Works on desktop, tablet and phone, and is ready to ship to the App Store and Play Store.

---

## Contents

1. [How it works](#1-how-it-works)
2. [Architecture](#2-architecture) (with the tech used in each part)
3. [Run it locally](#3-run-it-locally)
4. [Configuration](#4-configuration)
5. [Project structure](#5-project-structure)
6. [Workspaces, roles and plans](#6-workspaces-roles-and-plans)
7. [Tests](#7-tests)
8. [Mobile apps](#8-mobile-apps)
9. [Deployment](#9-deployment)
10. [Status and roadmap](#10-status-and-roadmap)

---

## 1. How it works

The product follows five steps, each with its own screen:

| Step | Screen | What happens |
|---|---|---|
| **1. Analyze** | `/analyze` | Paste a YouTube link (or a transcript). Yudhix reads the transcript and pulls out timestamped claims. |
| **2. Truth report** | `/videos/:id` → Claims | Each claim is checked against the brand's official facts: **Accurate**, **Misleading**, **False** or **Unverified**, with the cited source. |
| **3. Audience impact** | `/videos/:id` → Audience impact | Each comment is linked to the claim that triggered it and gets a root cause: **misinformation**, **valid concern** or **unlinked**. |
| **4. Respond** | `/inbox`, `/approvals` | Agents draft replies (AI drafts cite the official fact), an approver signs off (nobody approves their own reply), and the team can send the creator a polite clarification note. |
| **5. Track** | `/track` | Turnaround rate, reply pipeline, SLA breaches, misinformation share and sentiment over time. |

### What happens when you analyze a video

"Analyze" starts a background job. The UI polls it and shows each stage live.

```mermaid
flowchart LR
    A[YouTube link<br/>or transcript] --> B[1. Fetch video<br/>title, channel, views]
    B --> C[2. Transcribe<br/>captions / Whisper / pasted]
    C --> D[3. Extract claims<br/>up to 8, timestamped]
    D --> E[4. Fact-check<br/>search official facts → verdict]
    E --> F[5. Ingest comments<br/>mask PII, hash authors]
    F --> U[6. Read comments<br/>AI: sentiment, topics, claim]
    U --> G[7. Attribute<br/>comment → claim, root cause, priority]
    G --> H[Truth report, product impact<br/>+ prioritized inbox]
```

| Stage | Code (`services/yudhix-sense/app/truth/`) | How | Fallback when an optional piece is missing |
|---|---|---|---|
| Fetch video | `youtube.py` | YouTube Data API | YouTube oEmbed (no key needed) |
| Transcribe | `youtube.py` | YouTube captions, else Whisper (`faster-whisper` + `yt-dlp`) | Pasted transcript (`[mm:ss] text` lines) |
| Extract claims | `claims.py` | Local LLM (Ollama, `llama3.1`) | Rules: sentences with numbers, prices, absolutes, policy verbs |
| Fact-check | `retrieval.py`, `verifier.py` | BM25 search over `product_knowledge`, then the LLM says whether the source *supports* or *contradicts* the claim; code maps that to a verdict | Rules: matching figures, absolutes the source negates, predictions → Unverified |
| Ingest comments | `pipeline.py` | YouTube Data API (needs `YOUTUBE_API_KEY`), regex PII masking, keyed HMAC-SHA256 author hash | Uses comments already stored for the video |
| Read comments | `audience.py` | Local LLM reads comments in batches of 20, **most-liked first**, within a time budget (`LLM_COMMENT_BUDGET_SECONDS`, default 240 s): sentiment, up to 2 topics, and which claim (if any) the comment responds to | Keyword sentiment and keyword topics |
| Attribute | `attribution.py`, `scoring.py` | Uses the AI's claim decision where it read the comment; otherwise needs two specific words shared with the claim (or one plus a related concept or a timestamp pointing at it). Stores "why linked" evidence | – |

**Root cause:** `MISINFORMATION` (reacts to a misleading, false or unverified claim), `VALID_CONCERN` (reacts to an accurate claim), or `UNLINKED`.

**Priority:** impact score 0–100 = `100 × severity^0.8 × engagement × recency`, +10% for misinformation. **P1** ≥ 80, **P2** ≥ 50, else **P3**.

**Topics:** Price & value, Quality & hardware, Performance, Features & software, Games & content, Online & subscriptions, Support & warranty, Trust in the company, Competitors & switching.

### Product impact

Truth report → **Audience impact** tab (or **View impact** in the Inbox once a video is picked) shows how the comments affect the product (`app/truth/product_impact.py`, `GET /api/v1/truth/videos/{id}/product-impact`):

| Part | What it shows |
|---|---|
| Impact score | 0–100 and High / Medium / Low, with the trend of negative comments (rising, steady, fading). Score = `100 × (negative share of reach)^0.75 × size`, where size grows with total reach (max at ~10,000). |
| Sentiment | Negative / neutral / positive **by comments** and **by reach**. Reach weights each comment by `1 + likes + 2 × replies`, so one comment with 2,500 likes counts more than fifty with none. |
| What can fix it | Negative reach split into disputed claims (creator note and replies), real product concerns (product team) and general negativity, with links to the inbox. |
| Topics | What people talk about, split by sentiment, ordered by negative reach. |
| Over time | Comments per day (per week for long spans). |
| Most-liked negative comments | The five with the most reach, with **Reply** opening them in the inbox. |

Charts use their own colour tokens (`--chart-*` in `styles.scss`), checked for colour-blind separation in light and dark mode, and every chart has hover details and a table view.

### Product growth and ideas

The **Product growth** tab is the positive side (`app/truth/growth.py`, `GET /api/v1/truth/videos/{id}/growth`):

| Part | What it shows |
|---|---|
| Growth score | Mirror of the impact score: `100 × (positive share of reach)^0.75 × size`. Strong ≥ 60, moderate ≥ 35. |
| What people want | Comments by intent: feature requests, praise, buying signals, questions, complaints, leaving. Each bar opens those comments in the inbox. |
| What people love | Topics of positive comments, by positive reach. |
| Product ideas | Feature requests named by the AI in a few words ("more storage") and grouped with similar requests from **all** videos. |
| Praise, buying signals, at risk of leaving | The most-liked comments of each. |

The **Ideas** page is the product team's backlog: every idea with its supporting comments, videos and reach, a status (New → Reviewing → Planned → Shipped, or Declined) and a note. Keyword rules can spot a request when the AI is offline, but only the AI's reading names and groups it, so ideas fill in as the AI reads comments.

### AI engines (Settings → AI)

Every AI call goes through one layer (`app/core/llm.py`, providers in `app/core/providers.py`). Each workspace picks where AI runs:

| Mode | What answers | When |
|---|---|---|
| **Cloud AI** | Claude, ChatGPT (OpenAI), Gemini, Mistral, Groq, DeepSeek, OpenRouter, or any OpenAI-compatible server (LM Studio, vLLM, …) with the workspace's own key | Only after the key passes two checks: listing the provider's models, then a test request on the chosen model |
| **Local** | Ollama on the server (`OLLAMA_MODEL`) | Default |
| **Retrieval and rules** | No model: keyword fact search, rule-based verdicts and comment reading | When neither is available |

- **Automatic fallback:** cloud → local → rules, on every call. A key the provider rejects (401/403) switches the workspace back to local, marks the key invalid and notifies the admins.
- **Keys:** encrypted at rest (Fernet, `AI_KEY_SECRET`), never sent back to the browser (only the last 4 characters).
- **Data:** facts, comments, replies and ideas stay in your database. A cloud provider only receives what one request needs: a claim with its top 3 facts, a batch of PII-masked comments, or a fact's text to embed.
- **Speed:** cloud providers read comments 4 batches at a time; the local model reads one at a time.
- The robot in the top bar shows which engine is answering.

### How fact-checking works (RAG) and the anti-hallucination guards

1. **Hybrid search** (`app/truth/retrieval.py`): keyword ranking (BM25) plus meaning-based search (embedding cosine similarity), merged with Reciprocal Rank Fusion. Embeddings come from the cloud provider when it has an embeddings API (OpenAI, Gemini, Mistral), otherwise from a local model (`ollama pull nomic-embed-text`), otherwise search is keyword-only. Fact vectors are cached in `knowledge_embedding` and recomputed only when a fact changes.
2. **No evidence, no AI:** if nothing in the knowledge base is close, the claim is *unverified* without asking the model.
3. **Relation, not verdict:** the model says whether the source supports, contradicts, partly contradicts or doesn't address the claim, and code maps that to a verdict.
4. **Quote check:** the model must copy the source sentence it relied on, and that sentence must really be in the official text. An invented quote means the AI verdict is dropped and the claim is flagged **Needs review**.
5. **Number check:** figures are compared by code. "Supports" with different figures becomes *misleading* and is flagged.
6. **Second opinion** (`SECOND_OPINION=cloud|always|off`): with cloud AI each claim is read twice with the sources reordered. Disagreement means **Needs review**.
7. **Human verdict:** anyone who can edit content can set a claim's verdict. Re-checks keep it, and comments are re-linked.

### Amazon reviews and the product view

**Analyze → Amazon reviews:** pick the product, paste its Amazon link (any marketplace: amazon.com, .in, .co.uk, …; short `amzn.to` links work too). Yudhix tracks that listing and collects its reviews (`app/truth/amazon.py`, `app/truth/listings.py`):

| Mode | What it reads | When |
|---|---|---|
| **Direct** (default) | The public product page: listing title, average stars, rating count and the reviews shown on it (about 8–13 per check) | No setup. One ordinary page request per check; no proxies or CAPTCHA solving. If Amazon shows a robot check, the check stops, the listing is marked *blocked*, and the next scheduled check tries again. |
| **Provider** | All reviews, newest first, through a review-data API (Rainforest API) | Set `AMAZON_REVIEWS_API_KEY`. Use this for complete collection in production. |

Amazon's Conditions of Use restrict automated access; the provider route is the one meant for production use.

- Reviews are stored as comments with platform `AMAZON` (PII masked, author pseudonymized). The AI reads them like YouTube comments (topics, intent, feature requests), and **sentiment follows the stars**: 4–5 positive, 3 neutral, 1–2 negative. Helpful votes count as reach.
- The scheduler re-checks every listing on the workspace's interval, so new reviews keep arriving, and notifies the team about new negative reviews.
- **Products** page: every product with its sentiment split by channel. A product's page shows sentiment by channel (by count or reach), what each channel talks about, the **positive and negative voices** filtered by channel (YouTube / Amazon, with stars and "verified purchase" for reviews), and its sources: videos and Amazon listings with **Check now**.
- The Inbox has a channel filter (All / YouTube / Amazon).

### Uploading documents and syncing the knowledge base with AI

**Upload document** on the Knowledge page takes PDF, Word (.docx), text, Markdown or CSV files up to 10 MB (`app/truth/documents.py`). Each document is split into clause-sized facts (a section's paragraphs, up to ~700 characters) titled with the document and section or page, so a verdict can cite and quote the exact clause. A CSV with the columns `title, statement` (optional `category, clause, source`) is read as ready-made facts. The same file can't be uploaded twice, and deleting a document deletes its facts.

**AI sync** (`app/truth/ai_sync.py`): the knowledge base always stays in your database. Syncing builds the AI's index of it, with one vector per fact from the workspace's embedding model.

- Every workspace has its own index per AI connection. Reconnecting the same provider and model reuses it, so only facts added or changed since are sent.
- Facts added or uploaded while AI was off are shown as **pending** and are synced automatically when AI is turned on again (or with **Sync now**).
- Switching provider builds a second index and keeps the first, so switching back is instant.
- Sync runs automatically after connecting a key, switching mode, adding a fact or uploading a document. When it changes the index, analyzed videos are offered **Re-check claims**.
- Claude, Groq and DeepSeek have no embeddings API, so their workspaces sync with the local embedding model (`ollama pull nomic-embed-text`); claims are still judged by the chosen cloud model.

The sync status is shown on the Knowledge page and in Settings → AI.

### Knowledge base and re-checking claims

Each workspace has its own **Knowledge base**: the official facts (specs, prices, policies, FAQs) that claims are checked against. A claim with no matching fact stays *unverified*, so a new workspace should add its facts first.

There is no separate index to build: the search index (BM25 over title, category, clause and statement in `app/truth/retrieval.py`) is rebuilt from the database on every check, so a new fact is used straight away. Videos analyzed earlier keep their verdicts until they are re-checked:

- Adding or deleting a fact flags every analyzed video in the workspace. The **Knowledge** page then offers **Re-check claims** for all of them (one at a time in the background, with a notification each).
- A flagged video shows a banner on its Claims tab; any video can be re-checked from there.
- A re-check runs only the fact-check on the stored claims and then re-links comments, because verdicts decide which negativity counts as misinformation. No new transcript, no new comments.

### New comments after the first analysis

- **Fetch new comments** on a video pulls only comments posted since the last check (newest first, stopping at the first one already stored), lets the AI read them and re-links the video. The transcript and fact-check stay as they are. It takes seconds to a minute.
- **The schedule** does the same for every analyzed video. Each workspace picks the interval in **Settings → Workspace** (default every 6 hours, or off). Admins, approvers and agents get a notification when new negative comments or product ideas arrive. With several API copies running, a database lock lets only one of them run each round.
- New comments are marked **New** in the inbox (filter: **New only**) until the next full analysis.

Every verdict shows how it was made (`LLM`, `HEURISTIC` or `SEEDED`). The app works without the AI model; it switches to rules, and the robot in the top bar goes to sleep.

### Reply workflow

```mermaid
stateDiagram-v2
    [*] --> DRAFT: agent writes or uses AI draft
    DRAFT --> IN_REVIEW: submit
    IN_REVIEW --> APPROVED: approver (not the author)
    IN_REVIEW --> REJECTED: request changes + reason
    REJECTED --> DRAFT: edit
    APPROVED --> POSTED: post
    POSTED --> [*]: record outcome (improved, neutral, worsened)
```

Every state change is written to a hash-chained audit log (`audit_event`: each row's hash includes the previous row's hash, so edits are detectable).

---

## 2. Architecture

### 2.1 System overview (what runs today)

```mermaid
flowchart TB
    subgraph Clients
        WEB[Browser<br/>desktop · tablet · phone]
        APP[iOS / Android app]
    end

    GW[Gateway<br/>/ · /api · /auth]

    subgraph Services
        UI[Web app<br/>yudhix-web]
        API[API<br/>yudhix-sense]
        KC[Identity<br/>Keycloak]
    end

    subgraph EXT ["Data and external"]
        DB[(PostgreSQL 16)]
        LLM[Ollama<br/>local AI model]
        YT[YouTube<br/>Data API · captions]
        MAIL[SMTP<br/>Mailpit / ZeptoMail]
    end

    WEB --> GW
    APP --> GW
    GW -->|/| UI
    GW -->|/api| API
    GW -->|/auth| KC
    API -->|verify tokens JWKS| KC
    API --> DB
    KC --> DB
    API --> LLM
    API --> YT
    API --> MAIL
    KC --> MAIL
```

| Part | Tech | Role |
|---|---|---|
| **Web app** (`frontend/yudhix-web`) | Angular 20 (standalone components, signals, lazy routes), TypeScript, SCSS design tokens, Inter font, hand-built SVG charts, PWA service worker | All screens: public site, onboarding, Analyze → Track, settings. Responsive: sidebar on desktop, icon rail on tablet, bottom tabs on phone. Light/dark theme. |
| **Mobile** | Capacitor 8 | Wraps the same Angular build as iOS and Android apps. |
| **Gateway** (`deploy/gateway`) | nginx | One public address. Routes `/` → web, `/api` → API, `/auth` → Keycloak. Rate limits, security headers, gzip. Used in Docker, Kubernetes and Zoho; not in hot-reload dev. |
| **API** (`services/yudhix-sense`) | Python 3.12, FastAPI, Uvicorn, psycopg2, PyJWT | Truth pipeline, inbox and reply workflow, insights, workspaces, team, billing, notifications. Stateless, so it scales out. Creates and migrates the database schema on start. |
| **Identity** (`keycloak/`) | Keycloak 25, OpenID Connect, PKCE | Sign-up, sign-in, email verification, password reset, brute-force protection, enterprise SSO. Branded `yudhix` login theme. |
| **Database** | PostgreSQL 16 (pgvector image) | All app data. Every row carries `tenant_id` (the workspace). |
| **AI model** | Ollama with `llama3.1` | Claim extraction, fact-check reasoning, reply drafts. Optional. |
| **Email** | SMTP: Mailpit locally, Zoho ZeptoMail (or any SMTP) in production | Verification and invitation emails. |

### 2.2 Sign-in and request flow

```mermaid
sequenceDiagram
    actor U as User
    participant W as Web app
    participant K as Keycloak
    participant A as API
    participant D as PostgreSQL

    U->>W: Open app, click Sign in / Start free trial
    W->>K: Redirect (Authorization Code + PKCE)
    U->>K: Sign up or sign in (Yudhix login theme)
    K-->>W: Access token (5 min, refreshed in memory)
    W->>A: Request + Authorization: Bearer token + X-Tenant-Id
    A->>K: Check signature (JWKS, cached), issuer, expiry, client
    A->>D: Is this user an active member of this workspace? Which role?
    D-->>A: role = admin / approver / agent / analyst
    A-->>W: Data for that workspace only
```

| Piece | Tech | Notes |
|---|---|---|
| Browser login | `keycloak-js` 26 | PKCE (S256), silent SSO to restore sessions. Passwords never reach the app; the password grant is disabled. |
| Token check | PyJWT + JWKS | RS256 signature, issuer, expiry and client (`azp`) checked on every call. |
| Roles | PostgreSQL `tenant_user` | Roles live per workspace, not in the token, so one person can be admin in one brand and agent in another. |
| Realm setup | `keycloak/configure_realm.py` | Applies sign-up, email verification, password policy, SMTP, theme and allowed origins. Safe to re-run. |

### 2.3 Deployment

The same four container images run everywhere.

```mermaid
flowchart LR
    U[Users] --> G[gateway<br/>2–10 pods]
    G --> W[web<br/>2–6 pods]
    G --> A[api<br/>2–10 pods, autoscaled]
    G --> K[keycloak<br/>1–2 pods]
    A --> P[(PostgreSQL<br/>in-cluster locally,<br/>managed in prod)]
    K --> P
    A --> O[Ollama<br/>GPU host, optional]
```

| Target | Tech | Command |
|---|---|---|
| Laptop, whole stack | Docker Compose (`deploy/docker/compose.yaml`) | `./yudhix.sh docker-up` → http://localhost:8080 |
| Laptop, Kubernetes | Kustomize `deploy/k8s/overlays/local` | `./yudhix.sh k8s-up` → http://localhost:8081 |
| Production, Kubernetes | Kustomize `deploy/k8s/overlays/production`: HPA autoscaling, PodDisruptionBudgets, NetworkPolicies, TLS ingress (ingress-nginx + cert-manager), clustered Keycloak | `kubectl apply -k deploy/k8s/overlays/production` |
| Zoho Catalyst | AppSail (one app per image) + managed Postgres + ZeptoMail | `deploy/zoho/deploy-catalyst.sh` |

Details: [deploy/README.md](deploy/README.md) · Zoho: [deploy/zoho/README.md](deploy/zoho/README.md).

---

## 3. Run it locally

Two ways to run it. For daily development use **A** (hot reload, your sample data). Use **B** to test the production setup.

### Prerequisites (once)

| Tool | Version | Install (macOS) |
|---|---|---|
| Docker Desktop | latest | docker.com |
| PostgreSQL | 16 | `brew install postgresql@16 && brew services start postgresql@16` |
| Python | 3.11+ | `brew install python` |
| Node.js | 22 (or 20.19+) | `brew install node@22` |
| Ollama + model (optional) | latest | `brew install ollama && ollama pull llama3.1` |

### A. Development mode (hot reload)

**First time only:**

```bash
cd ~/Desktop/code/yudhix
./yudhix.sh init-db                       # creates the yudhix database and all tables
docker compose up -d keycloak mailpit     # sign-in server + email catcher
./yudhix.sh keycloak                      # applies sign-up / PKCE / SMTP / theme settings to Keycloak
```

**Every day (and after a restart), in this order:**

```bash
open -a Docker                            # 1. start Docker Desktop, wait until it says running
brew services start postgresql@16         # 2. dev database (usually already up, it starts at login)
cd ~/Desktop/code/yudhix
docker compose up -d keycloak mailpit     # 3. sign-in + email catcher
./yudhix.sh start                         # 4. API (:8000) + web app (:4200); installs dependencies on first run
./yudhix.sh status                        # 5. check everything is online
```

Open **http://localhost:4200**.

| What | Address | Login |
|---|---|---|
| Web app | http://localhost:4200 | `admin@sony.com` / `sony_admin_2026`, or **Start free trial** to sign up |
| API docs | http://localhost:8000/docs | – |
| Keycloak admin | http://localhost:8180 | `admin` / `admin_yudhix_2026` |
| Emails (Mailpit) | http://localhost:8025 | – (verification and invite emails land here) |
| AI model | localhost:11434 | – |

Try it: **Videos → "PlayStation Explains Why it's Ending Physical Discs"** shows a full report built from 2,662 stored comments. From the workspace menu you can also **Explore the demo workspace**.

**Stop:**

```bash
./yudhix.sh stop                          # API + web app
docker compose stop                       # Keycloak + Mailpit
```

Logs are in `.logs/` (`sense.log` for the API, `frontend.log` for the web app).

### B. Whole stack in containers

```bash
./yudhix.sh docker-up                     # builds 4 images, starts everything → http://localhost:8080
./yudhix.sh docker-down                   # stop (add --wipe to delete its database)
API_REPLICAS=4 ./yudhix.sh docker-up      # run 4 API copies behind the gateway
```

It reads `YOUTUBE_API_KEY` from the same `services/yudhix-sense/.env` file as dev mode. App: http://localhost:8080 · Keycloak admin: http://localhost:8080/auth/admin (`admin` / `admin_local_pw`) · Emails: http://localhost:8026. This stack has its **own empty database**: sign up, create a workspace and analyze a video.

### Troubleshooting

| Problem | Fix |
|---|---|
| Postgres won't start after a restart or crash | `tail /opt/homebrew/var/log/postgresql@16.log`. If it says `lock file "postmaster.pid" already exists` and `pgrep postgres` shows nothing, run `rm /opt/homebrew/var/postgresql@16/postmaster.pid && brew services restart postgresql@16`. |
| Sign-in page doesn't load | Keycloak takes ~30 s to start. `docker compose ps` should show `yudhix-keycloak` up. |
| No verification email | Check http://localhost:8025. Re-run `./yudhix.sh keycloak` if SMTP settings were lost. |
| Video report shows **0 comments** | The API has no YouTube API key. Put `YOUTUBE_API_KEY=...` in `services/yudhix-sense/.env`, run `./yudhix.sh restart`, then analyze the link again. |
| Robot in the top bar is asleep | The AI model isn't reachable. Run `ollama serve` and `ollama pull llama3.1`. The app still works in rule-based mode. |
| `./yudhix.sh k8s-up` can't find images | Docker Desktop's Kubernetes in **kind** mode doesn't share local images. Switch it to **kubeadm** (Settings → Kubernetes), or push to a registry: `REGISTRY=ghcr.io/<you> ./yudhix.sh k8s-up`. |
| Old icon or old page after an update | Hard reload (Cmd+Shift+R). The PWA service worker caches the app. |

> Note: the `postgres` container in `docker-compose.yml` holds Keycloak's data. Your app data is in the Homebrew Postgres. Both use port 5432; the API connects to `127.0.0.1`, which reaches Homebrew.

---

## 4. Configuration

API settings are environment variables (`services/yudhix-sense/app/core/config.py`). All have working local defaults.

For local secrets, copy `services/yudhix-sense/.env.example` to `.env` in the same folder (git-ignored) and restart the API. **To pull comments for new videos, set `YOUTUBE_API_KEY` there**: without it, analysis still finds and checks claims, but collects no comments.

| Variable | Default | Purpose |
|---|---|---|
| `PG_HOST` `PG_PORT` `PG_DB` `PG_USER` `PG_PASSWORD` | `localhost` `5432` `yudhix` `postgres` `postgres` | Database |
| `OLLAMA_URL` / `OLLAMA_MODEL` | `http://127.0.0.1:11434` / `llama3.1:latest` | AI model. Without it, rule-based mode. |
| `YOUTUBE_API_KEY` | empty | Pull metadata and comments for new videos. Server-side only. |
| `WHISPER_MODEL` | `small` | Only for videos without captions (needs `faster-whisper` and `yt-dlp`). |
| `KEYCLOAK_URL` / `KEYCLOAK_REALM` | `http://localhost:8180` / `yudhix` | Where tokens come from. |
| `KEYCLOAK_ISSUER` / `KEYCLOAK_JWKS_URL` | derived | Set when the browser and the API reach Keycloak by different addresses. |
| `APP_URL` / `CORS_ORIGINS` | `http://localhost:4200` / local + Capacitor origins | Invitation links; allowed web and app origins. |
| `SMTP_HOST` `SMTP_PORT` `SMTP_FROM` `SMTP_USER` `SMTP_PASSWORD` `SMTP_STARTTLS` | `localhost` `1025` … | Invitation emails. |
| `AUTHOR_HMAC_KEY` | `dev-only-change-me` | Secret for hashing comment authors. **Set a strong value in production.** |
| `TRIAL_DAYS` / `TRIAL_PLAN` | `14` / `PROFESSIONAL` | Free trial for new workspaces. |
| `DEMO_WORKSPACE_JOIN` | `true` | Anyone signed in can join the demo workspace. **Turn off in production.** |
| `MAX_COMMENTS_PER_VIDEO` | `100` | Comments kept per analysis. |
| `COMMENT_SAMPLING` | `spread` | `spread`: 40% newest, 40% oldest, 20% random from the middle, so the charts show a cross-section over time; the video's other stored comments are archived (hidden, not deleted), except ones with a reply. `top`: the most relevant comments as YouTube ranks them. |
| `COMMENT_POOL_MAX` | `2000` | `spread` reads up to this many comments, newest first, to find the oldest (1 YouTube quota unit per 100). |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Local embedding model for meaning-based fact search (used when the cloud provider has no embeddings). Optional. |
| `AI_KEY_SECRET` | `AUTHOR_HMAC_KEY` | Encrypts workspace AI keys. Set a long random value in production; changing it makes saved keys unreadable. |
| `SECOND_OPINION` | `cloud` | Read each claim twice and flag disagreements: `cloud` (only with cloud AI), `always`, `off`. |
| `AMAZON_REVIEWS_API_KEY` | (empty) | Rainforest API key: collect all Amazon reviews through the provider instead of reading the product page. |
| `AMAZON_MAX_REVIEWS` | `100` | Most reviews read per check with the provider. |
| `LLM_FACTCHECK_BUDGET_SECONDS` | `180` | Time the AI gets to fact-check a video's claims; the rest use the rule-based check (marked "Rule-based"). Cloud AI checks 4 claims at a time. |
| `NEW_COMMENTS_MAX` | `100` | Most comments one "Fetch new comments" check adds. |
| `SCHEDULER_ENABLED` | `true` | Background checks for new comments on this server. Workspaces set their own interval. |
| `SCHEDULER_TICK_SECONDS` | `300` | How often the scheduler looks for videos that are due. |
| `SCHEDULER_DEFAULT_HOURS` | `6` | Interval for workspaces that haven't chosen one. |
| `LLM_COMMENT_BUDGET_SECONDS` | `240` | Time the AI may spend reading comments per analysis (most-liked first); the rest use keyword rules. About 20 comments per 50 s on an M-series Mac with `llama3.1`. |
| `INTERNAL_API_KEY` | empty (disabled) | Unlocks the old internal endpoints (`/api/v1/comments`, `/analyze`, `/scheduler/…`). |

Web app settings: `frontend/yudhix-web/src/environments/` (`apiUrl`, `keycloak`, `salesEmail`). Container builds read `/config.json` at start instead, written from env vars. `GET /health` shows which optional features are active.

---

## 5. Project structure

```
yudhix/
├── yudhix.sh                    # start / stop / status / tests / docker / k8s helper
├── docker-compose.yml           # dev infrastructure: Keycloak, Mailpit, Postgres for Keycloak, Ollama
├── frontend/yudhix-web/         # Angular 20 PWA + Capacitor
│   └── src/app/
│       ├── core/                # API client, auth (keycloak-js), session & roles, guards
│       ├── layout/              # app shell: sidebar, top bar, bottom tabs
│       ├── shared/              # icons, badges, charts, money formatting, AI status robot
│       └── features/            # public, onboarding, analyze, videos, inbox, approvals, track, knowledge, settings
├── services/yudhix-sense/       # Python API (FastAPI): everything the web app calls
│   ├── app/
│   │   ├── api/                 # HTTP routes
│   │   ├── truth/               # video analysis pipeline
│   │   ├── workflow/            # inbox, reply state machine, outcomes, insights
│   │   ├── platform/            # auth, workspaces, team, billing, notifications, email
│   │   ├── pipeline/            # PII masking, sentiment, LLM enrichment
│   │   ├── core/                # config, database, migrations runner, LLM client
│   │   └── migrations/          # V2 truth-first · V3 SaaS · V4 regional pricing
│   └── tests/                   # pytest unit tests + end-to-end SaaS test
├── keycloak/                    # realm file, configure_realm.py, login theme
├── deploy/                      # gateway, Dockerfiles, Compose stack, Kubernetes, Zoho, scripts
├── services/yudhix-*/ (Java)    # planned Spring Boot services; their V1 SQL is the base schema
├── libs/                        # shared Java libraries for those services
└── airflow/dags/                # planned scheduled jobs (ingestion, outcomes, retention)
```

### Main database tables

| Area | Tables |
|---|---|
| Workspaces & team | `tenant`, `tenant_user`, `workspace_invitation`, `country_config` |
| Products & facts | `product`, `product_knowledge`, `knowledge_document`, `knowledge_embedding`, `ai_sync_run` |
| AI | `ai_setting` (provider, model, encrypted key per workspace) |
| Videos & claims | `video_truth_analysis`, `video_claim`, `video_analysis_job`, `creator_outreach` |
| Comments | `comment` (YouTube comments and Amazon reviews), `comment_analysis`, `comment_claim_link`, `comment_watch` (schedule) |
| Channels | `product_listing` (Amazon listings per product) |
| Product ideas | `product_idea`, `product_idea_comment` |
| Replies | `reply`, `approval_step`, `reply_outcome` |
| Billing | `plan`, `plan_price`, `subscription`, `usage_event`, `invoice`, `invoice_line` |
| Other | `app_notification`, `audit_event` |

The API creates every table on an empty database, then applies `app/migrations/V*.sql` on each start. Migrations are safe to run from many API copies at once.

---

## 6. Workspaces, roles and plans

**Sign-up flow:** Landing → Start free trial → Keycloak sign-up → verify email → onboarding (workspace → product + one official fact → first video) → truth report. Agencies switch between client workspaces from one login.

| Permission | Admin | Approver | Agent | Analyst |
|---|:-:|:-:|:-:|:-:|
| Read reports, inbox, insights | ✓ | ✓ | ✓ | ✓ |
| Analyze videos, edit facts, draft and post replies | ✓ | ✓ | ✓ | |
| Approve / reject replies (never their own) | ✓ | ✓ | | |
| Workspace settings, team, billing | ✓ | | | |

| Plan | India (INR + 18% GST) | Other countries (USD) | Video analyses | Comments | Team |
|---|---|---|---|---|---|
| Starter | ₹7,999 / mo | $99 / mo | 20 | 10,000 | 5 |
| Professional | ₹39,999 / mo | $499 / mo | 100 | 100,000 | 20 |
| Enterprise | ₹1,59,999 / mo | $1,999 / mo | Unlimited | Unlimited | Unlimited |

- Yearly = 10× monthly. New workspaces get a 14-day Professional trial.
- Currency comes from the workspace's country (India → INR, else USD) and stays fixed while a paid plan is active. The pricing page shows ₹ to visitors in India and $ to others, with a toggle.
- Prices live in the `plan_price` table. To change one: `UPDATE plan_price SET monthly_price = 8999, yearly_price = 89990 WHERE plan_id = 'STARTER' AND currency = 'INR';`
- When the trial ends or a quota is used up, reports stay readable but new analyses and posting are blocked until an admin picks a plan. Admins are notified at 80% and 100%.
- Invoices are real (proration, GST, printable), but **no card is charged yet**.

---

## Demo kit

`docs/demo/` has everything for presenting Yudhix: a scene-by-scene script with narration (`DEMO_SCRIPT.md`), a slide deck with real screenshots (`Yudhix-Demo.pptx`), and a recorder that produces a narrated 1080p video from the running app. See `docs/demo/README.md`.

## 7. Tests

```bash
./yudhix.sh unit     # backend (34 pytest) + frontend (10 Karma) unit tests
./yudhix.sh e2e      # ~47 end-to-end checks through the real Keycloak (needs dev mode running)
```

The end-to-end test creates two throwaway users, signs in with the real PKCE flow, and checks workspaces, invitations (including the email), role permissions, workspace isolation, plan changes with invoices, notifications and deletion. It removes its users at the end.

---

## 8. Mobile apps

The Angular build ships to the stores through Capacitor (`capacitor.config.ts`, app id `io.yudhix.app`). Native projects aren't generated yet. On a Mac with Xcode and Android Studio:

```bash
cd frontend/yudhix-web
# Set apiUrl and keycloak.url in src/environments/environment.prod.ts to your public address
npx cap add ios && npx cap add android     # once; commit the ios/ and android/ folders
npm run mobile:sync                        # build + copy into the native projects
npm run mobile:ios                         # opens Xcode
npm run mobile:android                     # opens Android Studio
```

Still needed before submitting: app icons and splash (`npx @capacitor/assets generate`), store listings, a privacy policy URL and the production API.

---

## 9. Deployment

| Where | Command | URL |
|---|---|---|
| Docker, whole stack | `./yudhix.sh docker-up` | http://localhost:8080 |
| Kubernetes on your laptop | `./yudhix.sh k8s-up` | http://localhost:8081 |
| Kubernetes in production | `kubectl apply -k deploy/k8s/overlays/production` | your domain |
| Zoho Catalyst AppSail | `deploy/zoho/deploy-catalyst.sh` | your domain → gateway app |

Step-by-step guides: [deploy/README.md](deploy/README.md) and [deploy/zoho/README.md](deploy/zoho/README.md).

Production checklist: strong `AUTHOR_HMAC_KEY` and database passwords, `DEMO_WORKSPACE_JOIN=false`, real SMTP, HTTPS, and `APP_ORIGINS=https://your-domain` when running `configure_realm.py`.

---

## 10. Status and roadmap

| Area | Today | Next |
|---|---|---|
| Posting replies | Approved replies are recorded as `SIMULATED`; nothing is sent to YouTube. | YouTube OAuth connector, live posting, automatic +24h / +72h / +7d outcome checks. |
| Payments | Plans, quotas and invoices work; no card is charged. | Stripe / Razorpay checkout and webhooks. |
| Ingestion | On demand per video, plus scheduled checks for new comments on analyzed videos. | Channel watchers that pick up new uploads. |
| Attribution | Keyword matching with evidence; weak on sarcasm and memes. | Embedding similarity (pgvector) with LLM re-ranking. |
| Fact-checking | Hybrid search (BM25 + embeddings) and local or cloud AI with quote, number and second-opinion checks. | Scanned PDFs (OCR); an evaluation set from human verdicts. |
| Sentiment & topics | Local LLM for the most-liked comments, keyword rules for the rest. | Faster model or GPU so the AI reads every comment; agent corrections. |
| Product impact & growth | Per video; product ideas across videos. | **Product health** across all videos of a product: trend, top issues, which creators drive negativity. |
| Services | One Python API does everything. | Split into the planned Java services (`services/yudhix-*`) as load requires. |
| Mobile | Capacitor configured. | Generate native projects, icons, store listings, push alerts. |

> **Security:** an old version of the web app had a YouTube API key in its code. It is still in git history, so **rotate that key in Google Cloud Console**. YouTube access now happens only on the server.
>
> AIzaSyCWGhmMjOdPlGkSjcaV4OKdvLSGIhvL3Uc>>>
