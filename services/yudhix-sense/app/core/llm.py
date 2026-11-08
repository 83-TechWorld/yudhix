"""The one door to AI for the whole app: picks the workspace's provider and falls back automatically.

Which engine answers, per workspace (Settings > AI):
  1. Cloud AI (Claude, ChatGPT, Gemini, ...) when the workspace turned it on and its key passed the check.
  2. The local model (Ollama) when it is running.
  3. Nobody: every caller handles `None` and uses its rules / retrieval-only path, so the product keeps
     working without any AI.
If the cloud call fails, the same request is retried on the local model. A rejected key (401/403) switches
the workspace back to local and marks the key invalid, so an expired key never stalls the pipeline.

Callers don't pass the workspace: entry points (jobs, reply drafts, creator notes) wrap their work in
`with llm.use_tenant(tenant_id):` and everything inside picks the right engine.
"""
import contextvars
import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import httpx

from app.core import config
from app.core.providers import Provider, ProviderError, local_provider, parse_json

logger = logging.getLogger(__name__)

_tenant: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("ai_tenant", default=None)
_local_cache: dict = {"checked_at": 0.0, "available": False, "models": []}
_cloud_cache: Dict[str, tuple] = {}  # tenant -> (checked_at, Provider | None)
CACHE_SECONDS = 30


@contextmanager
def use_tenant(tenant_id: Optional[str]):
    token = _tenant.set(tenant_id)
    try:
        yield
    finally:
        _tenant.reset(token)


def current_tenant() -> Optional[str]:
    return _tenant.get()


def forget(tenant_id: str) -> None:
    """Settings changed: re-read them on the next call."""
    _cloud_cache.pop(tenant_id, None)


# ----------------------------------------------------------------------------- engine selection

def _local_models() -> List[str]:
    now = time.time()
    if now - _local_cache["checked_at"] < 60:
        return _local_cache["models"]
    models: List[str] = []
    try:
        res = httpx.get(f"{config.OLLAMA_URL}/api/tags", timeout=2.0)
        if res.status_code == 200:
            models = [m.get("name") for m in res.json().get("models", [])]
    except Exception:
        models = []
    _local_cache.update(checked_at=now, models=models)
    return models


def _has(models: List[str], wanted: str) -> bool:
    return bool(wanted) and (wanted in models or f"{wanted}:latest" in models)


def local() -> Optional[Provider]:
    """The local Ollama model, if running and pulled."""
    models = _local_models()
    if not _has(models, config.OLLAMA_MODEL):
        return None
    p = local_provider()
    if not _has(models, p.embed_model or ""):
        p.embed_model = None
    return p


def cloud() -> Optional[Provider]:
    """The current workspace's cloud provider, when turned on and its key is valid."""
    tenant = _tenant.get()
    if not tenant:
        return None
    hit = _cloud_cache.get(tenant)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    provider = None
    try:
        from app.platform import ai_settings  # platform depends on core, not the other way round
        provider = ai_settings.active_provider(tenant)
    except Exception:
        logger.exception("Couldn't read AI settings for %s", tenant)
    _cloud_cache[tenant] = (time.time(), provider)
    return provider


def engine() -> Optional[Provider]:
    return cloud() or local()


def is_available() -> bool:
    return engine() is not None


def is_cloud() -> bool:
    return cloud() is not None


def describe() -> Dict[str, Any]:
    """What answers AI requests for the current workspace, for the robot icon and settings."""
    c = cloud()
    if c:
        return {"mode": "CLOUD", "provider": c.info.id, "label": c.info.label, "model": c.model,
                "embeddings": bool(c.embed_model) or bool(local() and local().embed_model)}
    loc = local()
    if loc:
        return {"mode": "LOCAL", "provider": "local", "label": "Local (Ollama)", "model": loc.model,
                "embeddings": bool(loc.embed_model)}
    return {"mode": "RULES", "provider": None, "label": "Rules and retrieval only", "model": None, "embeddings": False}


# ----------------------------------------------------------------------------- calls

def _call(fn_name: str, *args, **kwargs):
    """Run on the cloud provider, then the local model. Returns None when nothing answered."""
    for provider in (cloud(), local()):
        if provider is None:
            continue
        try:
            return getattr(provider, fn_name)(*args, **kwargs)
        except ProviderError as e:
            logger.warning("%s failed (%s), falling back", provider.label, e)
            if provider.cloud and e.auth:
                _key_rejected(str(e))
        except Exception as e:  # network or parsing surprises: never break the pipeline
            logger.warning("%s failed (%s: %s), falling back", provider.label, type(e).__name__, e)
    return None


def generate_json(prompt: str, timeout: Optional[float] = None, max_tokens: Optional[int] = None) -> Optional[Any]:
    """Run a prompt in JSON mode. Returns parsed JSON or None."""
    text = _call("generate", prompt, True, timeout or config.LLM_TIMEOUT_SECONDS, max_tokens, 0.1)
    return parse_json(text) if text else None


def generate_text(prompt: str) -> Optional[str]:
    text = _call("generate", prompt, False, config.LLM_TIMEOUT_SECONDS, None, 0.3)
    return (text or "").strip() or None


def embedder() -> Optional[Provider]:
    """Who makes embeddings for the current workspace: the cloud provider if it has an embeddings API,
    else the local embedding model, else nobody (keyword search only)."""
    c = cloud()
    if c and c.embed_model:
        return c
    loc = local()
    return loc if loc and loc.embed_model else None


def embed(texts: List[str]) -> Optional[tuple]:
    """(model name, vectors) or None. Vectors from different models are never mixed."""
    p = embedder()
    if not p or not texts:
        return None
    try:
        vectors = p.embed(texts)
        if len(vectors) == len(texts) and all(vectors):
            return f"{p.info.id}/{p.embed_model}", vectors
    except ProviderError as e:
        logger.warning("Embeddings from %s failed: %s", p.label, e)
        if p.cloud and e.auth:
            _key_rejected(str(e))
    except Exception as e:
        logger.warning("Embeddings from %s failed: %s", p.label, e)
    return None


def _key_rejected(error: str) -> None:
    tenant = _tenant.get()
    if not tenant:
        return
    try:
        from app.platform import ai_settings
        ai_settings.mark_rejected(tenant, error)
    except Exception:
        logger.exception("Couldn't mark the AI key as rejected")
    forget(tenant)
