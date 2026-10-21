import os
import json
import logging
from typing import Dict, Any, List
import httpx
from app.models.schemas import AspectItem

logger = logging.getLogger(__name__)


class OllamaLlmEnricher:
    """
    Tier-2 Deep LLM Enrichment via local Ollama instance (qwen3:8b / gemma3).
    Extracts granular aspect sentiments, intent, churn risk, and drafts a safe brand reply.
    """

    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.model_name = os.getenv("OLLAMA_MODEL", "qwen3:8b")

    async def enrich(self, masked_text: str, base_sentiment: str) -> Dict[str, Any]:
        prompt = f"""
You are an enterprise social comment intelligence analyst. Analyze this customer comment and return valid JSON with aspects, intent, churnRisk, and a suggested reply:
Comment: "{masked_text}"

Return JSON matching this schema:
{{
  "aspects": [{{"aspect": "battery", "sentiment": "NEGATIVE", "evidence": "dies in 2 hours"}}],
  "intent": "COMPLAINT",
  "churnRisk": 0.7,
  "topic": "hardware-quality",
  "toxic": false,
  "suggestedReply": "We apologize for the issue. Please reach out to our team at support.example.com so we can help resolve this right away."
}}
"""

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "format": "json",
                        "stream": False
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    response_text = data.get("response", "{}")
                    parsed = json.loads(response_text)
                    return parsed
        except Exception as e:
            logger.warning(f"Ollama inference unavailable or timed out ({e}). Utilizing rule-based fallback enrichment.")

        # Fallback enrichment when local Ollama is pulling models or during offline demo
        return self._heuristic_fallback(masked_text, base_sentiment)

    def _heuristic_fallback(self, text: str, base_sentiment: str) -> Dict[str, Any]:
        lower = text.lower()
        aspects = []

        if "battery" in lower or "charge" in lower or "charging" in lower:
            aspects.append({"aspect": "battery", "sentiment": base_sentiment, "evidence": "battery mentioned in comment"})
        if "support" in lower or "service" in lower:
            aspects.append({"aspect": "customer-support", "sentiment": base_sentiment, "evidence": "support mentioned"})
        if "delivery" in lower or "shipping" in lower:
            aspects.append({"aspect": "shipping", "sentiment": base_sentiment, "evidence": "delivery mentioned"})
        if "price" in lower or "cost" in lower or "expensive" in lower:
            aspects.append({"aspect": "pricing", "sentiment": base_sentiment, "evidence": "price mentioned"})

        if not aspects:
            aspects.append({"aspect": "product-experience", "sentiment": base_sentiment, "evidence": text})

        intent = "COMPLAINT" if base_sentiment == "NEGATIVE" else ("PRAISE" if base_sentiment == "POSITIVE" else "GENERAL")
        churn_risk = 0.75 if base_sentiment == "NEGATIVE" else 0.0

        suggested_reply = None
        if base_sentiment == "NEGATIVE":
            suggested_reply = "We're sorry to hear about your experience. Please send us a direct message or visit our official support portal so we can investigate and make this right."

        return {
            "aspects": aspects,
            "intent": intent,
            "churnRisk": churn_risk,
            "topic": aspects[0]["aspect"] if aspects else "general",
            "toxic": False,
            "suggestedReply": suggested_reply
        }
