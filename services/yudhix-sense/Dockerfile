# yudhix-sense: the Python API (truth pipeline, workflow, SaaS).
# Build from the REPOSITORY ROOT so the base schema files can be bundled:
#   docker build -f services/yudhix-sense/Dockerfile -t yudhix/api:local .
# Zoho Catalyst needs linux/amd64:  docker buildx build --platform linux/amd64 ...
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000 \
    WEB_CONCURRENCY=2

WORKDIR /app

COPY services/yudhix-sense/requirements.txt .
RUN pip install -r requirements.txt

COPY services/yudhix-sense/app ./app
# Base schema from the Java services' Flyway V1 files: lets this service bootstrap an empty database
COPY services/yudhix-tenant/src/main/resources/db/migration/V1__init_tenant_schema.sql \
     services/yudhix-ledger/src/main/resources/db/migration/V1__init_ledger_schema.sql \
     services/yudhix-dharma/src/main/resources/db/migration/V1__init_dharma_schema.sql \
     services/yudhix-catalog/src/main/resources/db/migration/V1__init_catalog_schema.sql \
     services/yudhix-radar/src/main/resources/db/migration/V1__init_radar_schema.sql \
     services/yudhix-link/src/main/resources/db/migration/V1__init_link_schema.sql \
     services/yudhix-pulse/src/main/resources/db/migration/V1__init_pulse_schema.sql \
     services/yudhix-resolve/src/main/resources/db/migration/V1__init_resolve_schema.sql \
     services/yudhix-loop/src/main/resources/db/migration/V1__init_loop_schema.sql \
     services/yudhix-notify/src/main/resources/db/migration/V1__init_notify_schema.sql \
     services/yudhix-meter/src/main/resources/db/migration/V1__init_meter_schema.sql \
     ./app/migrations/base/
# Keycloak realm setup tool, run as a one-off job (Kubernetes Job / compose service)
COPY keycloak/configure_realm.py ./tools/configure_realm.py

RUN useradd --uid 10001 --create-home app && chown -R app /app
USER 10001

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"X_ZOHO_CATALYST_LISTEN_PORT\", os.environ[\"PORT\"])}/healthz', timeout=2)"

# Listens on Zoho Catalyst's assigned port when present, else $PORT. TLS is terminated in front (gateway / LB).
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${X_ZOHO_CATALYST_LISTEN_PORT:-$PORT} --workers ${WEB_CONCURRENCY} --proxy-headers --forwarded-allow-ips='*'"]
