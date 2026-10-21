# Yudhix — Enterprise Social Comment Intelligence Platform

Yudhix is a multi-tenant, privacy-first SaaS platform designed to collect public comments from social platforms, execute aspect-based sentiment analysis, calculate impact scores, and empower company agents to resolve customer complaints through human-in-the-loop turnaround workflows.

---

## Architecture & Microservices

| Service | Directory | Tech Stack | Responsibility |
|---|---|---|---|
| **yudhix-gateway** | `services/yudhix-gateway` | Spring Cloud Gateway | OIDC validation, tenant route isolation, rate-limiting |
| **yudhix-sense** | `services/yudhix-sense` | Python FastAPI, Presidio, Ollama | PII masking, XLM-RoBERTa sentiment, Qwen3 aspect extraction |
| **yudhix-link** | `services/yudhix-link` | Spring Boot | Platform SPI, OAuth token vault, incremental comment fetching |
| **yudhix-resolve** | `services/yudhix-resolve` | Spring Boot | Human-in-the-loop review, SLA tracking, brand-safe reply posting |
| **yudhix-pulse** | `services/yudhix-pulse` | Spring Boot | Velocity, engagement decay, P1/P2/P3 impact scoring |
| **yudhix-ledger** | `services/yudhix-ledger` | Spring Boot | Append-only, hash-chained tamper-evident audit logging |
| **yudhix-dharma** | `services/yudhix-dharma` | Spring Boot | Policy packs, DPDP/CCPA onboarding, DSR execution, retention |
| **yudhix-loop** | `services/yudhix-loop` | Spring Boot | 24h/72h/7d turnaround outcome checks, model retraining signals |
| **yudhix-radar** | `services/yudhix-radar` | Spring Boot | Topic clustering, keyword filters, engagement thresholding |
| **yudhix-meter** | `services/yudhix-meter` | Spring Boot | Idempotent usage events, plan quotas, Stripe/Razorpay invoicing |
| **yudhix-tenant** | `services/yudhix-tenant` | Spring Boot | Multi-tenant organization & user management |
| **yudhix-catalog** | `services/yudhix-catalog` | Spring Boot, pgvector | Product catalog, aliases, competitor tracking, embeddings |
| **yudhix-notify** | `services/yudhix-notify` | Spring Boot | Spike alerts, SLA warnings, email & Slack dispatch |
| **yudhix-config** | `services/yudhix-config` | Spring Cloud Config | Centralized configuration server |

### Shared Libraries & Frontend
- **`libs/yudhix-common`**: Shared tenant context, RLS interceptors, HMAC author pseudonymizer, standard DTOs.
- **`libs/yudhix-connector-sdk`**: PlatformConnector SPI interface.
- **`frontend/yudhix-web`**: Angular 18+ application (inbox, approval drawer, analytics dashboard).
