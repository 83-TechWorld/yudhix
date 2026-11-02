"""Respond & Track API: inbox, replies with approval, outcomes and KPIs."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import actor, membership, tenant_id
from app.platform import billing
from app.platform.auth import Membership
from app.workflow import insights, service
from app.workflow.state import Actor, WorkflowError

router = APIRouter(prefix="/api/v1", tags=["respond-track"])


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except WorkflowError as e:
        raise HTTPException(e.status_code, str(e))
    except billing.QuotaError as e:
        raise HTTPException(402, str(e))


@router.get("/inbox")
def inbox(tenant: str = Depends(tenant_id), video_id: Optional[str] = None, priority: Optional[str] = None,
          sentiment: Optional[str] = None, cause: Optional[str] = None, status: str = "OPEN",
          q: Optional[str] = None, limit: int = 50, offset: int = 0):
    return service.inbox(tenant, video_id, priority, sentiment, cause, status, q, min(max(limit, 1), 200),
                         max(offset, 0))


@router.get("/inbox/{comment_id}")
def inbox_item(comment_id: str, tenant: str = Depends(tenant_id)):
    item = service.comment_detail(tenant, comment_id)
    if not item:
        raise HTTPException(404, "Comment not found")
    return item


@router.post("/inbox/{comment_id}/suggest")
def suggest(comment_id: str, member: Membership = Depends(membership), _: Actor = Depends(actor)):
    billing.record(member.tenant_id, "AI_CALL", 1)
    return _run(service.suggest_reply, member.tenant_id, comment_id, member.tenant_name)


class ReplyCreate(BaseModel):
    comment_id: str
    text: str = Field(..., max_length=5000)


class ReplyEdit(BaseModel):
    text: str = Field(..., max_length=5000)


class Decision(BaseModel):
    reason: Optional[str] = Field(None, max_length=1000)


class OutcomeBody(BaseModel):
    follow_up_text: Optional[str] = Field(None, max_length=5000)
    outcome: Optional[str] = Field(None, pattern="^(IMPROVED|NEUTRAL|WORSENED)$")


@router.get("/replies")
def replies(tenant: str = Depends(tenant_id), status: Optional[str] = None):
    return {"replies": service.list_replies(tenant, status)}


@router.post("/replies", status_code=201)
def reply_create(body: ReplyCreate, tenant: str = Depends(tenant_id), user: Actor = Depends(actor)):
    return _run(service.create_reply, tenant, user, body.comment_id, body.text)


@router.get("/replies/{reply_id}")
def reply_get(reply_id: str, tenant: str = Depends(tenant_id)):
    r = service.get_reply(tenant, reply_id)
    if not r:
        raise HTTPException(404, "Reply not found")
    return r


@router.patch("/replies/{reply_id}")
def reply_edit(reply_id: str, body: ReplyEdit, tenant: str = Depends(tenant_id), user: Actor = Depends(actor)):
    return _run(service.edit_reply, tenant, user, reply_id, body.text)


@router.post("/replies/{reply_id}/outcomes")
def reply_outcome(reply_id: str, body: OutcomeBody, tenant: str = Depends(tenant_id), user: Actor = Depends(actor)):
    return _run(service.record_outcome, tenant, user, reply_id, body.follow_up_text, body.outcome)


@router.post("/replies/{reply_id}/{action}")
def reply_action(reply_id: str, action: str, body: Optional[Decision] = None, tenant: str = Depends(tenant_id),
                 user: Actor = Depends(actor)):
    """action: submit | approve | reject | post"""
    return _run(service.transition, tenant, user, reply_id, action, body.reason if body else None)


@router.post("/outcomes/check")
def outcomes_check(tenant: str = Depends(tenant_id), _: Actor = Depends(actor)):
    return service.check_live_outcomes(tenant)


@router.get("/insights/summary")
def insights_summary(tenant: str = Depends(tenant_id), video_id: Optional[str] = None):
    return insights.summary(tenant, video_id)


@router.get("/insights/trend")
def insights_trend(tenant: str = Depends(tenant_id), video_id: Optional[str] = None, days: int = 60):
    return {"points": insights.sentiment_trend(tenant, video_id, min(max(days, 1), 365))}


@router.get("/insights/videos")
def insights_videos(tenant: str = Depends(tenant_id)):
    return {"videos": insights.video_leaderboard(tenant)}
