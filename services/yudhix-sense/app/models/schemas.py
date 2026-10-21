from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MaskRequest(BaseModel):
    text: str
    country_hint: Optional[str] = "IN"


class MaskResponse(BaseModel):
    original_length: int
    masked_text: str
    entities_detected: List[str] = []


class AspectItem(BaseModel):
    aspect: str
    sentiment: str  # POSITIVE, NEGATIVE, NEUTRAL, MIXED
    evidence: Optional[str] = None
    score: Optional[float] = 0.0


class AnalyzeCommentRequest(BaseModel):
    comment_id: str
    tenant_id: str
    raw_text: str
    platform: Optional[str] = "YOUTUBE"
    author_hash: Optional[str] = None
    channel_title: Optional[str] = None
    video_id: Optional[str] = None
    video_title: Optional[str] = None
    video_url: Optional[str] = None
    platform_created_at: Optional[str] = None
    language_hint: Optional[str] = "en"
    likes: int = 0
    replies: int = 0
    run_deep_llm: bool = True
    persist: bool = True


class AnalyzeCommentResponse(BaseModel):
    comment_id: str
    tenant_id: str
    masked_text: str
    sentiment: str  # POSITIVE, NEGATIVE, NEUTRAL, MIXED
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    aspects: List[AspectItem] = []
    intent: Optional[str] = "GENERAL"  # COMPLAINT, CHURN_RISK, QUESTION, PRAISE, SUGGESTION
    churn_risk: Optional[float] = 0.0
    topic: Optional[str] = "general"
    toxic: bool = False
    suggested_reply: Optional[str] = None
    entities_masked: List[str] = []


class BatchAnalyzeRequest(BaseModel):
    comments: List[AnalyzeCommentRequest]


class BatchAnalyzeResponse(BaseModel):
    results: List[AnalyzeCommentResponse]
    processed_count: int
