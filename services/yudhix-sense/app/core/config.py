"""Central settings for yudhix-sense. Everything is read from environment variables."""
import os

DEFAULT_TENANT_ID = "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"

# Demo identities used until the SaaS/auth layer ships. The web app sends one of these
# in the X-User-Id / X-User-Role headers so separation of duties can be enforced.
DEMO_USERS = {
    "agent": {"id": "11111111-1111-4111-8111-111111111111", "name": "Asha (Agent)", "role": "agent"},
    "approver": {"id": "22222222-2222-4222-8222-222222222222", "name": "Ravi (Brand Approver)", "role": "approver"},
}

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
# Secret used to pseudonymize comment authors (keyed per tenant). Set a strong value in production.
AUTHOR_HMAC_KEY = os.getenv("AUTHOR_HMAC_KEY", "dev-only-change-me")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:latest")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))

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
