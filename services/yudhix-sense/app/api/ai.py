"""Settings > AI: choose local or cloud AI, check a provider key, see what is answering right now."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import membership, require
from app.core import llm
from app.platform import ai_settings
from app.platform.auth import Membership

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


@router.get("/status")
def status(member: Membership = Depends(membership)):
    """What answers AI requests in this workspace (for the robot icon)."""
    with llm.use_tenant(member.tenant_id):
        return llm.describe()


@router.get("/providers")
def providers(_: Membership = Depends(membership)):
    return {"providers": ai_settings.catalog()}


@router.get("/settings")
def get_settings(member: Membership = Depends(membership)):
    return ai_settings.get(member.tenant_id)


class ModelsRequest(BaseModel):
    provider: str = Field(..., max_length=30)
    api_key: Optional[str] = Field(None, max_length=500)
    base_url: Optional[str] = Field(None, max_length=500)


@router.post("/models")
def list_models(body: ModelsRequest, member: Membership = Depends(require("workspace.manage"))):
    """Step 1: check the key by listing the provider's models."""
    try:
        return ai_settings.models(member.tenant_id, body.provider, body.api_key, body.base_url)
    except ai_settings.AiSettingError as e:
        raise HTTPException(400, str(e))


class SettingsRequest(BaseModel):
    mode: str = Field(..., pattern="^(LOCAL|CLOUD)$")
    provider: Optional[str] = Field(None, max_length=30)
    model: Optional[str] = Field(None, max_length=200)
    api_key: Optional[str] = Field(None, max_length=500)
    base_url: Optional[str] = Field(None, max_length=500)


@router.put("/settings")
def save_settings(body: SettingsRequest, member: Membership = Depends(require("workspace.manage"))):
    """Step 2: switch to local, or test the model with the key and switch to cloud only if it passes."""
    try:
        return ai_settings.save(member.tenant_id, member.user_id, body.mode, body.provider, body.model,
                                body.api_key, body.base_url)
    except ai_settings.AiSettingError as e:
        raise HTTPException(400, str(e))


@router.delete("/key")
def remove_key(member: Membership = Depends(require("workspace.manage"))):
    return ai_settings.remove_key(member.tenant_id, member.user_id)
