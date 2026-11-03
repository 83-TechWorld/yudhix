"""Small synchronous Ollama client used by the truth pipeline.

Every caller must handle `None` (model not pulled, Ollama offline, bad JSON) and fall
back to its heuristic path, so the product keeps working without a local GPU.
"""
import json
import logging
import time
from typing import Any, Optional

import httpx

from app.core import config

logger = logging.getLogger(__name__)

_status_cache: dict = {"checked_at": 0.0, "available": False}


def is_available() -> bool:
    """True when Ollama is reachable and the configured model is pulled. Cached for 60s."""
    now = time.time()
    if now - _status_cache["checked_at"] < 60:
        return _status_cache["available"]
    available = False
    try:
        res = httpx.get(f"{config.OLLAMA_URL}/api/tags", timeout=2.0)
        if res.status_code == 200:
            names = {m.get("name") for m in res.json().get("models", [])}
            wanted = config.OLLAMA_MODEL
            available = wanted in names or f"{wanted}:latest" in names
    except Exception:
        available = False
    _status_cache.update(checked_at=now, available=available)
    return available


def generate_json(prompt: str, timeout: Optional[float] = None, max_tokens: Optional[int] = None) -> Optional[Any]:
    """Run a prompt in JSON mode. Returns parsed JSON or None."""
    if not is_available():
        return None
    options = {"temperature": 0.1}
    if max_tokens:
        options["num_predict"] = max_tokens
    try:
        res = httpx.post(
            f"{config.OLLAMA_URL}/api/generate",
            json={"model": config.OLLAMA_MODEL, "prompt": prompt, "format": "json", "stream": False,
                  "options": options},
            timeout=timeout or config.LLM_TIMEOUT_SECONDS,
        )
        if res.status_code != 200:
            return None
        return json.loads(res.json().get("response", "null"))
    except Exception as e:
        logger.warning("Ollama call failed, using heuristic fallback: %s", e)
        return None


def generate_text(prompt: str) -> Optional[str]:
    if not is_available():
        return None
    try:
        res = httpx.post(
            f"{config.OLLAMA_URL}/api/generate",
            json={"model": config.OLLAMA_MODEL, "prompt": prompt, "stream": False,
                  "options": {"temperature": 0.3}},
            timeout=config.LLM_TIMEOUT_SECONDS,
        )
        if res.status_code == 200:
            return (res.json().get("response") or "").strip() or None
    except Exception as e:
        logger.warning("Ollama call failed, using template fallback: %s", e)
    return None
