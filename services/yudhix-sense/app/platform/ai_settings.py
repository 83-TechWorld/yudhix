"""Per-workspace AI settings: local model or a cloud provider with the workspace's own key.

Turning cloud AI on is a two-step check, so a bad key never switches the workspace over:
  1. models(): the key is checked by listing the provider's models (also fills the model picker).
  2. save(): a tiny JSON request runs on the chosen model. Only if it answers is the setting stored
     with status VALID and mode CLOUD. Otherwise nothing changes and the error is returned.
Keys are encrypted at rest and never sent back to the browser (only the last 4 characters).
Facts, comments and replies always stay in this database; cloud AI only receives the text a single
request needs (one claim with its top matching facts, or a batch of PII-masked comments).
"""
import base64
import hashlib
import logging
from typing import Dict, Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core import config, llm
from app.core.database import append_audit, cursor, fetch_one
from app.core.providers import CATALOG, Provider, ProviderError, pick_embed_model, suggest_model

logger = logging.getLogger(__name__)

PROBE = 'Reply with exactly this JSON object: {"ok": true}'


class AiSettingError(Exception):
    pass


def _fernet() -> Fernet:
    key = hashlib.sha256(f"yudhix-ai-keys:{config.AI_KEY_SECRET}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        logger.warning("Stored AI key can't be decrypted (AI_KEY_SECRET changed?)")
        return None


def catalog() -> list:
    return [{"id": p.id, "label": p.label, "keyUrl": p.key_url, "needsBaseUrl": p.needs_base_url,
             "embeddings": bool(p.embeddings)} for p in CATALOG.values()]


def _row(tenant_id: str) -> Dict:
    return fetch_one("SELECT * FROM ai_setting WHERE tenant_id = %s", (tenant_id,)) or {}


def get(tenant_id: str) -> Dict:
    """The workspace's settings for the UI (never the key itself)."""
    r = _row(tenant_id)
    with llm.use_tenant(tenant_id):
        active = llm.describe()
    local = llm.local()
    return {
        "mode": r.get("mode") or "LOCAL",
        "provider": r.get("provider"),
        "model": r.get("model"),
        "embedModel": r.get("embed_model"),
        "baseUrl": r.get("base_url"),
        "keyHint": r.get("key_hint"),
        "hasKey": bool(r.get("api_key_enc")),
        "status": r.get("status") or "UNTESTED",
        "lastError": r.get("last_error"),
        "validatedAt": r["validated_at"].isoformat() if r.get("validated_at") else None,
        "active": active,
        "local": {"available": local is not None, "model": config.OLLAMA_MODEL,
                  "embedModel": local.embed_model if local else None},
    }


def _provider(provider_id: str, api_key: Optional[str], base_url: Optional[str], model: str = "") -> Provider:
    info = CATALOG.get(provider_id or "")
    if not info:
        raise AiSettingError("Pick a provider.")
    if info.needs_base_url and not (base_url or "").startswith(("http://", "https://")):
        raise AiSettingError("Enter the API base URL, e.g. http://localhost:1234/v1")
    if not api_key and not info.needs_base_url:
        raise AiSettingError("Paste the API key.")
    # Only "custom" takes a base URL; known providers always use their official endpoint.
    return Provider(info, model, api_key=api_key or "", base_url=(base_url or "").strip() if info.needs_base_url else "")


def _key_for(tenant_id: str, provider_id: str, api_key: Optional[str]) -> Optional[str]:
    """The pasted key, or the stored one when the same provider is kept and no new key was pasted."""
    if api_key:
        return api_key.strip()
    r = _row(tenant_id)
    return decrypt(r.get("api_key_enc")) if r.get("provider") == provider_id else None


def models(tenant_id: str, provider_id: str, api_key: Optional[str], base_url: Optional[str]) -> Dict:
    """Step 1: check the key by listing models. Returns the chat models and a suggested default."""
    p = _provider(provider_id, _key_for(tenant_id, provider_id, api_key), base_url)
    try:
        found = p.list_models()
    except ProviderError as e:
        raise AiSettingError(_friendly(e)) from e
    if not found["chat"]:
        raise AiSettingError("The key works, but this account has no chat models available.")
    return {"models": found["chat"], "suggested": suggest_model(p.info, found["chat"]),
            "embedModel": pick_embed_model(p.info, found["embed"])}


def save(tenant_id: str, actor: str, mode: str, provider_id: Optional[str] = None, model: Optional[str] = None,
         api_key: Optional[str] = None, base_url: Optional[str] = None) -> Dict:
    """Step 2. LOCAL: switch to the local model / rules (the cloud key stays stored for later).
    CLOUD: test the chosen model with the key; only a passing test switches the workspace to cloud AI."""
    mode = (mode or "LOCAL").upper()
    if mode == "LOCAL":
        with cursor(commit=True) as cur:
            cur.execute("""INSERT INTO ai_setting (tenant_id, mode, updated_by) VALUES (%s, 'LOCAL', %s)
                           ON CONFLICT (tenant_id) DO UPDATE SET mode = 'LOCAL', updated_by = EXCLUDED.updated_by,
                               updated_at = now()""", (tenant_id, actor))
            append_audit(cur, tenant_id, actor, "USER", "AI_MODE_CHANGED", "WORKSPACE", tenant_id, {"mode": "LOCAL"})
        llm.forget(tenant_id)
        return get(tenant_id)
    if mode != "CLOUD":
        raise AiSettingError("Mode must be LOCAL or CLOUD.")
    if not model:
        raise AiSettingError("Pick a model.")

    key = _key_for(tenant_id, provider_id, api_key)
    p = _provider(provider_id, key, base_url, model)
    try:
        listed = p.list_models()
        p.embed_model = pick_embed_model(p.info, listed["embed"])
    except ProviderError as e:
        _store_failure(tenant_id, actor, provider_id, e)
        raise AiSettingError(_friendly(e)) from e
    try:
        reply = p.generate_json(PROBE, timeout=45, max_tokens=50)
    except ProviderError as e:
        _store_failure(tenant_id, actor, provider_id, e)
        raise AiSettingError(_friendly(e)) from e
    if not isinstance(reply, dict):
        raise AiSettingError(f"{model} answered, but not with valid JSON. Pick a different model.")

    with cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO ai_setting (tenant_id, mode, provider, model, embed_model, base_url, api_key_enc, key_hint,
                   status, last_error, validated_at, updated_by)
               VALUES (%s, 'CLOUD', %s, %s, %s, %s, %s, %s, 'VALID', NULL, now(), %s)
               ON CONFLICT (tenant_id) DO UPDATE SET mode = 'CLOUD', provider = EXCLUDED.provider,
                   model = EXCLUDED.model, embed_model = EXCLUDED.embed_model, base_url = EXCLUDED.base_url,
                   api_key_enc = EXCLUDED.api_key_enc, key_hint = EXCLUDED.key_hint, status = 'VALID',
                   last_error = NULL, validated_at = now(), updated_by = EXCLUDED.updated_by, updated_at = now()""",
            (tenant_id, provider_id, model, p.embed_model, p.base_url or None, encrypt(key) if key else None,
             ("…" + key[-4:]) if key else None, actor))
        append_audit(cur, tenant_id, actor, "USER", "AI_MODE_CHANGED", "WORKSPACE", tenant_id,
                     {"mode": "CLOUD", "provider": provider_id, "model": model})
    llm.forget(tenant_id)
    return get(tenant_id)


def remove_key(tenant_id: str, actor: str) -> Dict:
    with cursor(commit=True) as cur:
        cur.execute("""UPDATE ai_setting SET mode = 'LOCAL', api_key_enc = NULL, key_hint = NULL, status = 'UNTESTED',
                              last_error = NULL, updated_by = %s, updated_at = now() WHERE tenant_id = %s""",
                    (actor, tenant_id))
        append_audit(cur, tenant_id, actor, "USER", "AI_KEY_REMOVED", "WORKSPACE", tenant_id, {})
    llm.forget(tenant_id)
    return get(tenant_id)


def active_provider(tenant_id: str) -> Optional[Provider]:
    """The cloud provider to use right now, or None (local / rules)."""
    r = _row(tenant_id)
    if r.get("mode") != "CLOUD" or r.get("status") != "VALID":
        return None
    info = CATALOG.get(r.get("provider") or "")
    key = decrypt(r.get("api_key_enc"))
    if not info or (not key and not info.needs_base_url):
        return None
    return Provider(info, r["model"], api_key=key or "", base_url=r.get("base_url") or "",
                    embed_model=r.get("embed_model"))


def mark_rejected(tenant_id: str, error: str) -> None:
    """The provider rejected the key mid-run: back to local, and tell the admins once."""
    with cursor(commit=True) as cur:
        cur.execute("""UPDATE ai_setting SET mode = 'LOCAL', status = 'INVALID', last_error = %s, updated_at = now()
                       WHERE tenant_id = %s AND mode = 'CLOUD' RETURNING provider""", (error[:500], tenant_id))
        changed = cur.fetchone()
    if changed:
        from app.platform.notifications import notify
        notify(tenant_id, "ai", "Cloud AI key rejected",
               "The provider rejected the API key, so Yudhix switched back to the local model. "
               "Check the key in Settings > AI.", "/settings/ai", roles=["admin"])


def _store_failure(tenant_id: str, actor: str, provider_id: Optional[str], e: ProviderError) -> None:
    """Remember why the last test failed, without touching the active mode or the stored key."""
    with cursor(commit=True) as cur:
        cur.execute("""INSERT INTO ai_setting (tenant_id, mode, last_error, updated_by) VALUES (%s, 'LOCAL', %s, %s)
                       ON CONFLICT (tenant_id) DO UPDATE SET last_error = EXCLUDED.last_error, updated_at = now()""",
                    (tenant_id, f"{provider_id}: {e}"[:500], actor))


def _friendly(e: ProviderError) -> str:
    if e.auth:
        return "The provider rejected this API key. Check that it was copied completely and is active."
    text = str(e)
    if "429" in text or "quota" in text.lower() or "credit" in text.lower():
        return f"The key works, but the account has no quota or credit left. ({text})"
    return text
