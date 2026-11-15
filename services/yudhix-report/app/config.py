"""Settings, from environment variables. Same names as yudhix-sense, so one .env / ConfigMap serves both.

For local development the service also reads services/yudhix-sense/.env (database and Keycloak
settings), then its own services/yudhix-report/.env. Real environment variables always win.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    _here = Path(__file__).resolve().parent.parent
    load_dotenv(_here / ".env")
    load_dotenv(_here.parent / "yudhix-sense" / ".env")
except ImportError:  # python-dotenv is optional in containers
    pass

# Database (read-only use: every session is opened with default_transaction_read_only=on)
PG_DB = os.getenv("PG_DB", "yudhix")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "postgres")
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))

# Keycloak: the same realm and clients as the main API
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8180").rstrip("/")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "yudhix")
KEYCLOAK_ISSUER = os.getenv("KEYCLOAK_ISSUER", f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}")
KEYCLOAK_JWKS_URL = os.getenv("KEYCLOAK_JWKS_URL", f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs")
KEYCLOAK_CLIENT_IDS = [c.strip() for c in os.getenv("KEYCLOAK_CLIENT_IDS", "yudhix-web").split(",") if c.strip()]

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:4200,http://127.0.0.1:4200,http://localhost:3000,capacitor://localhost,http://localhost",
    ).split(",")
    if o.strip()
]

# Limits: a report covers at most this many workspaces, and lists at most this many rows per table
MAX_WORKSPACES = int(os.getenv("REPORT_MAX_WORKSPACES", "25"))
TABLE_ROWS = int(os.getenv("REPORT_TABLE_ROWS", "10"))
