"""Central settings for yudhix-sense. Everything is read from environment variables.

For local development, put secrets such as YOUTUBE_API_KEY in services/yudhix-sense/.env
(git-ignored; see .env.example). Real environment variables always win over the file.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
except ImportError:  # python-dotenv is optional in container images
    pass

DEFAULT_TENANT_ID = "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"

# ---- Identity (Keycloak) -------------------------------------------------------------
# Issuer is what the BROWSER sees (tokens carry it). JWKS URL is what THIS server can reach
# (they differ when Keycloak runs on an internal hostname).
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8180").rstrip("/")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "yudhix")
KEYCLOAK_ISSUER = os.getenv("KEYCLOAK_ISSUER", f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}")
KEYCLOAK_JWKS_URL = os.getenv("KEYCLOAK_JWKS_URL", f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs")
# Tokens must be issued to one of these clients (the "azp" claim).
KEYCLOAK_CLIENT_IDS = [c.strip() for c in os.getenv("KEYCLOAK_CLIENT_IDS", "yudhix-web").split(",") if c.strip()]

# ---- SaaS -------------------------------------------------------------------------------
APP_URL = os.getenv("APP_URL", "http://localhost:4200").rstrip("/")   # used in invitation links
TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "14"))
TRIAL_PLAN = os.getenv("TRIAL_PLAN", "PROFESSIONAL")
INVITE_TTL_DAYS = int(os.getenv("INVITE_TTL_DAYS", "7"))
MAX_WORKSPACES_PER_USER = int(os.getenv("MAX_WORKSPACES_PER_USER", "20"))
# Lets any signed-in user join the seeded PlayStation demo workspace. Turn off in production.
DEMO_WORKSPACE_JOIN = os.getenv("DEMO_WORKSPACE_JOIN", "true").lower() == "true"
# Old pre-SaaS endpoints (/api/v1/comments, /analyze, /scheduler/…) are only reachable with this key.
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")

SMTP_HOST = os.getenv("SMTP_HOST", "localhost")     # Mailpit in docker-compose (UI: http://localhost:8025)
SMTP_PORT = int(os.getenv("SMTP_PORT", "1025"))
SMTP_FROM = os.getenv("SMTP_FROM", "Yudhix <no-reply@yudhix.local>")
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_STARTTLS = os.getenv("SMTP_STARTTLS", "false").lower() == "true"

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
# Secret used to pseudonymize comment authors (keyed per tenant). Set a strong value in production.
AUTHOR_HMAC_KEY = os.getenv("AUTHOR_HMAC_KEY", "dev-only-change-me")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:latest")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
# Time the AI may spend reading comments per analysis; the rest fall back to rules.
LLM_COMMENT_BUDGET_SECONDS = float(os.getenv("LLM_COMMENT_BUDGET_SECONDS", "240"))

# How many comments a single "Analyze video" job pulls from YouTube.
MAX_COMMENTS_PER_VIDEO = int(os.getenv("MAX_COMMENTS_PER_VIDEO", "500"))

# SLA per priority band, in hours.
SLA_HOURS = {"P1": 2, "P2": 24, "P3": 72}

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:4200,http://127.0.0.1:4200,http://localhost:3000,capacitor://localhost,http://localhost",
    ).split(",")
    if o.strip()
]
