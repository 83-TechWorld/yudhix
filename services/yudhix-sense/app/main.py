from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.models.schemas import (
    MaskRequest, MaskResponse,
    AnalyzeCommentRequest, AnalyzeCommentResponse,
    BatchAnalyzeRequest, BatchAnalyzeResponse, AspectItem
)
from app.pipeline.masker import PiiMasker
from app.pipeline.classifier import FastSentimentClassifier
from app.pipeline.llm_enricher import OllamaLlmEnricher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("yudhix-sense")

app = FastAPI(
    title="Yudhix Sense (AI & Sentiment Pipeline)",
    description="Privacy-preserving PII masking, fast sentiment classification, and Ollama LLM aspect extraction",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

masker = PiiMasker()
classifier = FastSentimentClassifier()
enricher = OllamaLlmEnricher()


@app.get("/health")
def health_check():
    return {"status": "UP", "service": "yudhix-sense"}


@app.post("/api/v1/mask", response_model=MaskResponse)
def mask_text(request: MaskRequest):
    masked, entities = masker.mask(request.text)
    return MaskResponse(
        original_length=len(request.text),
        masked_text=masked,
        entities_detected=entities
    )


@app.post("/api/v1/analyze", response_model=AnalyzeCommentResponse)
async def analyze_comment(request: AnalyzeCommentRequest):
    # Step 1: PII Masking
    masked_text, entities = masker.mask(request.raw_text)

    # Step 2: Fast Sentiment Classification
    sentiment, score = classifier.classify(masked_text)

    # Step 3: Deep LLM Enrichment (Aspects, Intent, Auto-draft)
    enrichment = await enricher.enrich(masked_text, sentiment)

    raw_aspects = enrichment.get("aspects", [])
    aspect_items = [
        AspectItem(
            aspect=a.get("aspect", "general"),
            sentiment=a.get("sentiment", sentiment),
            evidence=a.get("evidence"),
            score=a.get("score", 0.0)
        )
        for a in raw_aspects
    ]

    return AnalyzeCommentResponse(
        comment_id=request.comment_id,
        tenant_id=request.tenant_id,
        masked_text=masked_text,
        sentiment=sentiment,
        sentiment_score=score,
        aspects=aspect_items,
        intent=enrichment.get("intent", "GENERAL"),
        churn_risk=enrichment.get("churnRisk", 0.0),
        topic=enrichment.get("topic", "general"),
        toxic=enrichment.get("toxic", False),
        suggested_reply=enrichment.get("suggestedReply"),
        entities_masked=entities
    )


@app.post("/api/v1/analyze/batch", response_model=BatchAnalyzeResponse)
async def analyze_batch(batch_request: BatchAnalyzeRequest):
    results = []
    for item in batch_request.comments:
        res = await analyze_comment(item)
        results.append(res)

    return BatchAnalyzeResponse(
        results=results,
        processed_count=len(results)
    )
