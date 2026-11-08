"""Truth-first API: analyze a video, read its report and audience impact, manage knowledge."""
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import actor, membership, require, tenant_id
from app.platform import billing
from app.platform.auth import Membership
from app.truth import growth, pipeline, product_impact, repository, scheduler, youtube
from app.workflow.state import Actor

router = APIRouter(prefix="/api/v1/truth", tags=["truth"])


class AnalyzeRequest(BaseModel):
    video_url: str = Field(..., min_length=5, max_length=500)
    product_id: Optional[str] = None
    transcript: Optional[str] = Field(None, max_length=200_000,
                                      description="Optional pasted transcript; lines may start with [mm:ss]")


@router.post("/analyze", status_code=202)
def analyze(body: AnalyzeRequest, background: BackgroundTasks, tenant: str = Depends(tenant_id),
            user: Actor = Depends(actor)):
    try:
        youtube.parse_video_id(body.video_url)
        billing.check_quota(tenant, "VIDEO_ANALYZED")
        job = pipeline.create_job(tenant, body.video_url, body.product_id, user.id)
    except youtube.YouTubeError as e:
        raise HTTPException(400, str(e))
    except billing.QuotaError as e:
        raise HTTPException(402, str(e))
    billing.record(tenant, "VIDEO_ANALYZED", 1, key=f"job:{job['id']}")
    background.add_task(pipeline.run_job, job["id"], tenant, body.transcript)
    return job


@router.get("/jobs")
def jobs(tenant: str = Depends(tenant_id)):
    return {"jobs": pipeline.list_jobs(tenant)}


@router.get("/jobs/{job_id}")
def job(job_id: str, tenant: str = Depends(tenant_id)):
    found = pipeline.get_job(tenant, job_id)
    if not found:
        raise HTTPException(404, "Job not found")
    return found


@router.get("/videos")
def videos(tenant: str = Depends(tenant_id)):
    items = repository.list_videos(tenant)
    return {"videos": items, "count": len(items)}


@router.get("/videos/{video_id}")
def video(video_id: str, tenant: str = Depends(tenant_id)):
    found = repository.get_video(tenant, video_id)
    if not found:
        raise HTTPException(404, "Video not found")
    return found


@router.get("/videos/{video_id}/impact")
def impact(video_id: str, tenant: str = Depends(tenant_id)):
    found = repository.get_impact(tenant, video_id)
    if not found:
        raise HTTPException(404, "Video not found")
    return found


@router.get("/videos/{video_id}/product-impact")
def product_impact_view(video_id: str, tenant: str = Depends(tenant_id)):
    if not repository.get_video(tenant, video_id):
        raise HTTPException(404, "Video not found")
    return product_impact.load(tenant, video_id)


@router.post("/videos/{video_id}/check-comments", status_code=202)
def check_comments(video_id: str, background: BackgroundTasks, tenant: str = Depends(tenant_id),
                   user: Actor = Depends(actor)):
    """Fetch comments posted since the last check (no new transcript or fact-check). Returns the job to poll."""
    try:
        job = pipeline.start_comment_check(tenant, video_id, user.id)
    except pipeline.PipelineError as e:
        raise HTTPException(404, str(e))
    if job["kind"] == "COMMENTS" and job["status"] == "QUEUED":
        background.add_task(pipeline.run_job, job["id"], tenant)
    return job


@router.post("/videos/{video_id}/recheck-facts", status_code=202)
def recheck_facts(video_id: str, background: BackgroundTasks, tenant: str = Depends(tenant_id),
                  user: Actor = Depends(actor)):
    """Fact-check this video's claims again against the current knowledge base. Returns the job to poll."""
    try:
        job = pipeline.start_video_job(tenant, video_id, user.id, "FACTS")
    except pipeline.PipelineError as e:
        raise HTTPException(404, str(e))
    if job["kind"] == "FACTS" and job["status"] == "QUEUED":
        background.add_task(pipeline.run_job, job["id"], tenant)
    return job


@router.post("/knowledge/recheck", status_code=202)
def recheck_all(background: BackgroundTasks, tenant: str = Depends(tenant_id), user: Actor = Depends(actor)):
    """Re-check every video checked against older facts, one after another in the background."""
    jobs = [pipeline.start_video_job(tenant, v, user.id, "FACTS") for v in repository.stale_videos(tenant)]
    queued = [j["id"] for j in jobs if j["kind"] == "FACTS" and j["status"] == "QUEUED"]
    if queued:
        background.add_task(pipeline.run_jobs, queued, tenant)
    return {"queued": len(queued), "jobs": jobs}


@router.get("/videos/{video_id}/growth")
def growth_view(video_id: str, tenant: str = Depends(tenant_id)):
    if not repository.get_video(tenant, video_id):
        raise HTTPException(404, "Video not found")
    return growth.load(tenant, video_id)


class WatchSetting(BaseModel):
    enabled: Optional[bool] = None
    interval_hours: Optional[int] = None


@router.get("/comment-schedule")
def comment_schedule(tenant: str = Depends(tenant_id)):
    return scheduler.get_setting(tenant)


@router.put("/comment-schedule")
def save_comment_schedule(body: WatchSetting, tenant: str = Depends(tenant_id),
                          member: Membership = Depends(require("workspace.manage"))):
    try:
        return scheduler.save_setting(tenant, member.user_id, body.enabled, body.interval_hours)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ----------------------------------------------------------------------------- product ideas

@router.get("/ideas")
def ideas(tenant: str = Depends(tenant_id), status: Optional[str] = None, video_id: Optional[str] = None):
    return {"ideas": growth.list_ideas(tenant, status=status, video_id=video_id)}


@router.get("/ideas/{idea_id}")
def idea(idea_id: str, tenant: str = Depends(tenant_id)):
    found = growth.get_idea(tenant, idea_id)
    if not found:
        raise HTTPException(404, "Idea not found")
    return found


class IdeaUpdate(BaseModel):
    status: Optional[str] = None
    note: Optional[str] = Field(None, max_length=4000)
    title: Optional[str] = Field(None, min_length=3, max_length=200)


@router.patch("/ideas/{idea_id}")
def update_idea(idea_id: str, body: IdeaUpdate, tenant: str = Depends(tenant_id),
                member: Membership = Depends(require("content.write"))):
    try:
        found = growth.update_idea(tenant, member.user_id, idea_id, body.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not found:
        raise HTTPException(404, "Idea not found")
    return found


@router.post("/videos/{video_id}/reattribute")
def reattribute(video_id: str, tenant: str = Depends(tenant_id), _: Actor = Depends(actor)):
    try:
        return pipeline.attribute_video(tenant, video_id)
    except pipeline.PipelineError as e:
        raise HTTPException(404, str(e))


@router.get("/claims/{claim_id}/comments")
def claim_comments(claim_id: str, tenant: str = Depends(tenant_id), limit: int = 50):
    return {"comments": repository.claim_comments(tenant, claim_id, min(limit, 200))}


class OutreachRequest(BaseModel):
    claim_ids: Optional[List[str]] = None


@router.get("/videos/{video_id}/outreach")
def outreach_list(video_id: str, tenant: str = Depends(tenant_id)):
    return {"notes": repository.list_outreach(tenant, video_id)}


@router.post("/videos/{video_id}/outreach", status_code=201)
def outreach_create(video_id: str, body: OutreachRequest, member: Membership = Depends(membership),
                    user: Actor = Depends(actor)):
    tenant = member.tenant_id
    billing.record(tenant, "AI_CALL", 1)
    try:
        note = repository.create_outreach(tenant, user.id, video_id, body.claim_ids, member.tenant_name)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not note:
        raise HTTPException(404, "Video not found")
    return note


class OutreachUpdate(BaseModel):
    subject: Optional[str] = Field(None, max_length=300)
    body: Optional[str] = Field(None, max_length=10_000)
    status: Optional[str] = Field(None, pattern="^(DRAFT|SENT)$")


@router.patch("/outreach/{outreach_id}")
def outreach_update(outreach_id: str, body: OutreachUpdate, tenant: str = Depends(tenant_id),
                    user: Actor = Depends(actor)):
    note = repository.update_outreach(tenant, user.id, outreach_id, body.model_dump(exclude_none=True))
    if not note:
        raise HTTPException(404, "Note not found")
    return note


# ----------------------------------------------------------------------------- knowledge base

@router.get("/knowledge")
def knowledge(tenant: str = Depends(tenant_id)):
    items = repository.list_knowledge(tenant)
    stale = repository.stale_videos(tenant)
    return {"knowledge": items, "count": len(items), "staleVideos": len(stale)}


class KnowledgeRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    statement: str = Field(..., min_length=10, max_length=20_000)
    category: Optional[str] = Field("General", max_length=100)
    clauseRef: Optional[str] = Field(None, max_length=100)
    source: Optional[str] = Field(None, max_length=255)
    productId: Optional[str] = None


@router.post("/knowledge", status_code=201)
def knowledge_add(body: KnowledgeRequest, tenant: str = Depends(tenant_id), user: Actor = Depends(actor)):
    added = repository.add_knowledge(tenant, user.id, body.model_dump())
    pipeline.mark_facts_stale(tenant)  # claims checked before this fact existed can now be re-checked
    return added


@router.delete("/knowledge/{knowledge_id}", status_code=204)
def knowledge_delete(knowledge_id: str, tenant: str = Depends(tenant_id), user: Actor = Depends(actor)):
    if not repository.delete_knowledge(tenant, user.id, knowledge_id):
        raise HTTPException(404, "Document not found")
    pipeline.mark_facts_stale(tenant)
