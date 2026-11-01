"""Request context: tenant and acting user.

Until the SaaS/auth layer lands, the web app sends X-Tenant-Id, X-User-Id and X-User-Role.
In production these come from the gateway after it validates the Keycloak JWT; clients must
never be trusted to set them directly.
"""
import uuid
from typing import Optional

from fastapi import Header, HTTPException

from app.core import config
from app.workflow.state import Actor


def tenant_id(x_tenant_id: Optional[str] = Header(default=None)) -> str:
    value = x_tenant_id or config.DEFAULT_TENANT_ID
    try:
        uuid.UUID(value)
    except ValueError:
        raise HTTPException(400, "X-Tenant-Id must be a UUID")
    return value


def actor(x_user_id: Optional[str] = Header(default=None), x_user_role: Optional[str] = Header(default=None)) -> Actor:
    role = (x_user_role or "agent").lower()
    if role not in ("agent", "approver"):
        raise HTTPException(400, "X-User-Role must be 'agent' or 'approver'")
    user_id = x_user_id or config.DEMO_USERS[role]["id"]
    try:
        uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(400, "X-User-Id must be a UUID")
    return Actor(id=user_id, role=role)
