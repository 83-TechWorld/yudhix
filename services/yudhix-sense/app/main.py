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
from app.db import (
    persist_comment_and_analysis,
    get_all_comments_from_db,
    save_source_watermark,
    get_source_watermarks
)

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


@app.get("/api/v1/comments")
def list_comments(tenant_id: str = "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d", limit: int = 200):
    """
    Fetch all ingested comments, sentiment classifications, aspects, and channel/video metadata from PostgreSQL.
    """
    comments = get_all_comments_from_db(tenant_id=tenant_id, limit=limit)
    return {"comments": comments, "count": len(comments)}


@app.post("/api/v1/comments/persist")
def persist_single_comment(payload: dict):
    """
    Persist an analyzed comment and its aspects directly into PostgreSQL.
    """
    try:
        res = persist_comment_and_analysis(payload)
        return {"status": "SUCCESS", "result": res}
    except Exception as e:
        logger.error(f"Persist error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/watermarks")
def list_watermarks(tenant_id: str = "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"):
    """
    Get latest ingestion watermarks for all channels.
    """
    return {"watermarks": get_source_watermarks(tenant_id)}


@app.post("/api/v1/watermark")
def update_watermark(payload: dict):
    """
    Record or advance a channel's ingestion watermark.
    """
    res = save_source_watermark(
        tenant_id=payload.get("tenant_id", "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"),
        source_id=payload.get("source_id", "c0a80101-0000-0000-0000-000000000001"),
        platform=payload.get("platform", "YOUTUBE"),
        last_comment_ts=payload.get("last_comment_ts", "now()"),
        page_token=payload.get("page_token")
    )
    return res


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
    enrichment = {}
    if request.run_deep_llm:
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
    if not aspect_items:
        aspect_items = [
            AspectItem(
                aspect="overall",
                sentiment=sentiment,
                evidence=masked_text[:60],
                score=score
            )
        ]

    churn_risk = enrichment.get("churnRisk", 0.1 if sentiment == "POSITIVE" else 0.65)
    intent = enrichment.get("intent", "PRAISE" if sentiment == "POSITIVE" else "COMPLAINT")
    suggested_reply = enrichment.get("suggestedReply") or (
        "Thank you so much for the wonderful feedback! Our team is thrilled to hear this."
        if sentiment == "POSITIVE" else
        "We sincerely apologize for this experience. Please DM us so we can investigate and make this right."
    )

    # Step 4: Auto-Persist into PostgreSQL if requested
    if request.persist:
        try:
            persist_comment_and_analysis({
                "tenant_id": request.tenant_id,
                "platform": request.platform,
                "comment_id": request.comment_id,
                "raw_text": request.raw_text,
                "masked_text": masked_text,
                "author_hash": request.author_hash,
                "likes": request.likes,
                "replies": request.replies,
                "sentiment": sentiment,
                "sentiment_score": score,
                "intent": intent,
                "churn_risk": churn_risk,
                "toxic": enrichment.get("toxic", False),
                "suggested_reply": suggested_reply,
                "channel_title": request.channel_title,
                "video_id": request.video_id,
                "video_title": request.video_title,
                "video_url": request.video_url,
                "platform_created_at": request.platform_created_at,
                "priority": "P1" if (sentiment == "NEGATIVE" and churn_risk > 0.4) else "P2",
                "aspects": [a.model_dump() for a in aspect_items]
            })
        except Exception as e:
            logger.error(f"Failed to auto-persist comment {request.comment_id} to DB: {e}")

    return AnalyzeCommentResponse(
        comment_id=request.comment_id,
        tenant_id=request.tenant_id,
        masked_text=masked_text,
        sentiment=sentiment,
        sentiment_score=score,
        aspects=aspect_items,
        intent=intent,
        churn_risk=churn_risk,
        topic=enrichment.get("topic", "general"),
        toxic=enrichment.get("toxic", False),
        suggested_reply=suggested_reply,
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

