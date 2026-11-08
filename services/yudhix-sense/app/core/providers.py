"""AI providers behind one small interface: generate (text or JSON), embed, list models.

  local       Ollama on this machine (default)
  anthropic   Claude
  openai      ChatGPT models
  gemini      Google Gemini
  mistral, groq, deepseek, openrouter, custom   OpenAI-compatible chat APIs

Every call raises ProviderError on failure; app/core/llm.py decides what to fall back to.
Model lists come from each provider's own /models endpoint, so new models show up without a code change.
"""
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import httpx

from app.core import config


class ProviderError(Exception):
    def __init__(self, message: str, auth: bool = False):
        super().__init__(message)
        self.auth = auth  # the key was rejected (401/403): stop using it


@dataclass(frozen=True)
class ProviderInfo:
    id: str
    label: str
    kind: str                       # local | anthropic | openai | gemini
    base_url: str = ""
    key_url: str = ""               # where to create a key
    prefer: tuple = ()              # substrings that make a good default model, best first
    embeddings: Optional[str] = None  # default embedding model, "auto" = pick from the model list
    needs_base_url: bool = False


CATALOG: Dict[str, ProviderInfo] = {p.id: p for p in [
    ProviderInfo("anthropic", "Claude (Anthropic)", "anthropic", "https://api.anthropic.com",
                 "https://console.anthropic.com/settings/keys", ("sonnet", "haiku", "opus")),
    ProviderInfo("openai", "ChatGPT (OpenAI)", "openai", "https://api.openai.com/v1",
                 "https://platform.openai.com/api-keys", ("mini", "gpt-"), "text-embedding-3-small"),
    ProviderInfo("gemini", "Gemini (Google)", "gemini", "https://generativelanguage.googleapis.com/v1beta",
                 "https://aistudio.google.com/app/apikey", ("flash", "pro"), "auto"),
    ProviderInfo("mistral", "Mistral", "openai", "https://api.mistral.ai/v1",
                 "https://console.mistral.ai/api-keys", ("medium", "small", "large"), "mistral-embed"),
    ProviderInfo("groq", "Groq", "openai", "https://api.groq.com/openai/v1",
                 "https://console.groq.com/keys", ("llama-3.3-70b", "70b", "llama")),
    ProviderInfo("deepseek", "DeepSeek", "openai", "https://api.deepseek.com/v1",
                 "https://platform.deepseek.com/api_keys", ("chat",)),
    ProviderInfo("openrouter", "OpenRouter (many models)", "openai", "https://openrouter.ai/api/v1",
                 "https://openrouter.ai/keys", ("claude", "gpt", "gemini")),
    ProviderInfo("custom", "Other OpenAI-compatible API", "openai", "", "", (), None, needs_base_url=True),
]}


@dataclass
class Provider:
    info: ProviderInfo
    model: str
    api_key: str = ""
    base_url: str = ""
    embed_model: Optional[str] = None
    cloud: bool = True
    _client_opts: dict = field(default_factory=dict)

    @property
    def label(self) -> str:
        return f"{self.info.label} · {self.model}"

    # --------------------------------------------------------------- generation
    def generate(self, prompt: str, json_mode: bool = False, timeout: float = 60, max_tokens: Optional[int] = None,
                 temperature: float = 0.1) -> str:
        kind = self.info.kind
        if kind == "anthropic":
            return self._anthropic(prompt, json_mode, timeout, max_tokens, temperature)
        if kind == "gemini":
            return self._gemini(prompt, json_mode, timeout, max_tokens, temperature)
        if kind == "local":
            return self._ollama(prompt, json_mode, timeout, max_tokens, temperature)
        return self._openai(prompt, json_mode, timeout, max_tokens, temperature)

    def generate_json(self, prompt: str, timeout: float = 60, max_tokens: Optional[int] = None):
        return parse_json(self.generate(prompt, True, timeout, max_tokens))

    def _base(self) -> str:
        return (self.base_url or self.info.base_url).rstrip("/")

    def _post(self, url: str, body: dict, headers: dict, timeout: float, params: Optional[dict] = None) -> dict:
        try:
            res = httpx.post(url, json=body, headers=headers, params=params, timeout=timeout)
        except httpx.HTTPError as e:
            raise ProviderError(f"{self.info.label} unreachable: {type(e).__name__}") from e
        _raise_for(res, self.info.label)
        return res.json()

    def _anthropic(self, prompt, json_mode, timeout, max_tokens, temperature) -> str:
        body = {"model": self.model, "max_tokens": max_tokens or 2048, "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]}
        if json_mode:
            body["system"] = "Reply with one valid JSON object only. No prose, no code fences."
        data = self._post(f"{self._base()}/v1/messages", body, self._anthropic_headers(), timeout)
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")

    def _anthropic_headers(self) -> dict:
        return {"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}

    def _openai(self, prompt, json_mode, timeout, max_tokens, temperature) -> str:
        body = {"model": self.model, "messages": [{"role": "user", "content": prompt}]}
        if not self.model.startswith(("o1", "o3", "o4", "gpt-5")):  # reasoning models reject custom temperature
            body["temperature"] = temperature
        if max_tokens:
            body["max_tokens"] = max_tokens
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        try:
            data = self._post(f"{self._base()}/chat/completions", body, headers, timeout)
        except ProviderError as e:
            if e.auth or not ("response_format" in str(e) or "max_tokens" in str(e)):
                raise
            body.pop("response_format", None)  # some compatible servers don't support JSON mode
            if "max_tokens" in body:
                body["max_completion_tokens"] = body.pop("max_tokens")
            data = self._post(f"{self._base()}/chat/completions", body, headers, timeout)
        choices = data.get("choices") or [{}]
        return (choices[0].get("message") or {}).get("content") or ""

    def _gemini(self, prompt, json_mode, timeout, max_tokens, temperature) -> str:
        gen = {"temperature": temperature}
        if max_tokens:
            gen["maxOutputTokens"] = max_tokens
        if json_mode:
            gen["responseMimeType"] = "application/json"
        model = self.model if self.model.startswith("models/") else f"models/{self.model}"
        data = self._post(f"{self._base()}/{model}:generateContent",
                          {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": gen},
                          {"x-goog-api-key": self.api_key}, timeout)
        parts = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
        return "".join(p.get("text", "") for p in parts)

    def _ollama(self, prompt, json_mode, timeout, max_tokens, temperature) -> str:
        options = {"temperature": temperature}
        if max_tokens:
            options["num_predict"] = max_tokens
        body = {"model": self.model, "prompt": prompt, "stream": False, "options": options}
        if json_mode:
            body["format"] = "json"
        return self._post(f"{self._base()}/api/generate", body, {}, timeout).get("response") or ""

    # --------------------------------------------------------------- embeddings
    @property
    def can_embed(self) -> bool:
        return bool(self.embed_model)

    def embed(self, texts: List[str], timeout: float = 60) -> List[List[float]]:
        if not self.embed_model or not texts:
            raise ProviderError("No embedding model")
        kind = self.info.kind
        if kind == "local":
            data = self._post(f"{self._base()}/api/embed", {"model": self.embed_model, "input": texts}, {}, timeout)
            return data.get("embeddings") or []
        if kind == "gemini":
            model = self.embed_model if self.embed_model.startswith("models/") else f"models/{self.embed_model}"
            data = self._post(f"{self._base()}/{model}:batchEmbedContents",
                              {"requests": [{"model": model, "content": {"parts": [{"text": t}]}} for t in texts]},
                              {"x-goog-api-key": self.api_key}, timeout)
            return [e.get("values") or [] for e in data.get("embeddings", [])]
        if kind == "openai":
            data = self._post(f"{self._base()}/embeddings", {"model": self.embed_model, "input": texts},
                              {"Authorization": f"Bearer {self.api_key}"}, timeout)
            return [d.get("embedding") or [] for d in sorted(data.get("data", []), key=lambda d: d.get("index", 0))]
        raise ProviderError(f"{self.info.label} has no embeddings API")

    # --------------------------------------------------------------- models
    def list_models(self, timeout: float = 15) -> Dict[str, List[str]]:
        """{"chat": [...], "embed": [...]} from the provider. A rejected key raises ProviderError(auth=True)."""
        kind = self.info.kind
        try:
            if kind == "anthropic":
                res = httpx.get(f"{self._base()}/v1/models", headers=self._anthropic_headers(),
                                params={"limit": 100}, timeout=timeout)
                _raise_for(res, self.info.label)
                return {"chat": [m["id"] for m in res.json().get("data", [])], "embed": []}
            if kind == "gemini":
                res = httpx.get(f"{self._base()}/models", headers={"x-goog-api-key": self.api_key},
                                params={"pageSize": 200}, timeout=timeout)
                _raise_for(res, self.info.label)
                models = res.json().get("models", [])
                name = lambda m: m["name"].split("/", 1)[-1]  # noqa: E731
                return {"chat": [name(m) for m in models if "generateContent" in m.get("supportedGenerationMethods", [])],
                        "embed": [name(m) for m in models if "embedContent" in m.get("supportedGenerationMethods", [])]}
            if kind == "local":
                res = httpx.get(f"{self._base()}/api/tags", timeout=timeout)
                _raise_for(res, self.info.label)
                names = [m["name"] for m in res.json().get("models", [])]
                return {"chat": [n for n in names if "embed" not in n], "embed": [n for n in names if "embed" in n]}
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            res = httpx.get(f"{self._base()}/models", headers=headers, timeout=timeout)
            _raise_for(res, self.info.label)
            ids = sorted(m.get("id", "") for m in res.json().get("data", []) if m.get("id"))
            return {"chat": [i for i in ids if _is_chat_model(self.info.id, i)], "embed": [i for i in ids if "embed" in i]}
        except httpx.HTTPError as e:
            raise ProviderError(f"{self.info.label} unreachable: {type(e).__name__}") from e


_NOT_CHAT = ("embed", "tts", "whisper", "transcribe", "audio", "realtime", "image", "dall-e", "moderation",
             "search", "davinci", "babbage", "computer-use", "codex", "sora")


def _is_chat_model(provider_id: str, model_id: str) -> bool:
    m = model_id.lower()
    if any(x in m for x in _NOT_CHAT):
        return False
    if provider_id == "openai":
        return m.startswith(("gpt-", "o1", "o3", "o4", "chatgpt"))
    return True


def suggest_model(info: ProviderInfo, models: List[str]) -> Optional[str]:
    """A sensible default: newest-looking model matching the provider's preferences."""
    if not models:
        return None
    ranked = sorted(models, reverse=True)  # higher version numbers sort later -> first after reverse
    for want in info.prefer:
        for m in ranked:
            if want in m.lower() and "preview" not in m.lower():
                return m
    return ranked[0]


def pick_embed_model(info: ProviderInfo, embed_models: List[str]) -> Optional[str]:
    if info.embeddings == "auto":
        return sorted(embed_models, reverse=True)[0] if embed_models else None
    if info.embeddings and (not embed_models or info.embeddings in embed_models):
        return info.embeddings
    return None


def local_provider() -> Provider:
    return Provider(ProviderInfo("local", "Local (Ollama)", "local", config.OLLAMA_URL), config.OLLAMA_MODEL,
                    base_url=config.OLLAMA_URL, embed_model=config.OLLAMA_EMBED_MODEL or None, cloud=False)


def _raise_for(res: httpx.Response, label: str) -> None:
    if res.status_code < 400:
        return
    try:
        body = res.json()
        err = body.get("error") if isinstance(body, dict) else None
        detail = (err.get("message") if isinstance(err, dict) else err) or body.get("message") or res.text
    except ValueError:
        detail = res.text
    detail = " ".join(str(detail).split())[:300]
    auth = res.status_code in (401, 403) or "api key" in detail.lower() and res.status_code == 400
    raise ProviderError(f"{label} {res.status_code}: {detail}", auth=auth)


def parse_json(text: str):
    """JSON from a model reply, tolerating code fences or a sentence around the object."""
    text = (text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except ValueError:
        pass
    m = re.search(r"\{.*\}|\[.*\]", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except ValueError:
            return None
    return None
