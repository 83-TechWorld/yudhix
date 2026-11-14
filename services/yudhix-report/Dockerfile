# yudhix-report: business reports across workspaces (JSON preview + PDF). Reads the database read-only.
#   docker build -f services/yudhix-report/Dockerfile -t yudhix/report:local .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8010 \
    WEB_CONCURRENCY=2

WORKDIR /app
COPY services/yudhix-report/requirements.txt .
RUN pip install -r requirements.txt
COPY services/yudhix-report/app ./app

RUN useradd --uid 10001 --create-home app && chown -R app /app
USER 10001

EXPOSE 8010
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"X_ZOHO_CATALYST_LISTEN_PORT\", os.environ[\"PORT\"])}/healthz', timeout=2)"

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${X_ZOHO_CATALYST_LISTEN_PORT:-$PORT} --workers ${WEB_CONCURRENCY} --proxy-headers --forwarded-allow-ips='*'"]
