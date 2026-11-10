"""Products across channels (YouTube + Amazon) and their Amazon listings."""
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import actor, require, tenant_id
from app.platform import billing
from app.platform.auth import Membership
from app.truth import listings, pipeline, product_view
from app.workflow.state import Actor

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


@router.get("/products")
def products(tenant: str = Depends(tenant_id)):
    return {"products": product_view.list_products(tenant), "unassignedVideos": product_view.unassigned_videos(tenant)}


@router.get("/products/{product_id}")
def product(product_id: str, tenant: str = Depends(tenant_id)):
    found = product_view.overview(tenant, product_id)
    if not found:
        raise HTTPException(404, "Product not found")
    return found


@router.get("/products/{product_id}/comments")
def product_comments(product_id: str, tenant: str = Depends(tenant_id), channel: Optional[str] = None,
                     sentiment: Optional[str] = None, limit: int = 30, offset: int = 0):
    return product_view.comments(tenant, product_id, (channel or "").upper() or None, (sentiment or "").upper() or None,
                                 min(max(limit, 1), 100), max(offset, 0))


class AmazonRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=1000)
    product_id: str = Field(..., min_length=10, max_length=60)


@router.post("/amazon", status_code=202)
def analyze_amazon(body: AmazonRequest, background: BackgroundTasks, tenant: str = Depends(tenant_id),
                   user: Actor = Depends(actor)):
    """Track an Amazon listing for a product and collect its reviews now. Returns the job to poll."""
    try:
        billing.check_quota(tenant, "VIDEO_ANALYZED")
        listing = listings.add_listing(tenant, user.id, body.url, body.product_id)
    except listings.ListingError as e:
        raise HTTPException(400, str(e))
    except billing.QuotaError as e:
        raise HTTPException(402, str(e))
    job = listings.start_check(tenant, listing, user.id)
    if job["kind"] == "AMAZON" and job["status"] == "QUEUED":
        background.add_task(pipeline.run_job, job["id"], tenant)
    return {**job, "listing": listing}


@router.post("/listings/{listing_id}/check", status_code=202)
def check_listing(listing_id: str, background: BackgroundTasks, tenant: str = Depends(tenant_id),
                  user: Actor = Depends(actor)):
    listing = listings.get_listing(tenant, listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")
    job = listings.start_check(tenant, listing, user.id)
    if job["kind"] == "AMAZON" and job["status"] == "QUEUED":
        background.add_task(pipeline.run_job, job["id"], tenant)
    return job


@router.delete("/listings/{listing_id}", status_code=204)
def remove_listing(listing_id: str, tenant: str = Depends(tenant_id),
                   member: Membership = Depends(require("content.write"))):
    if not listings.delete_listing(tenant, member.user_id, listing_id):
        raise HTTPException(404, "Listing not found")
