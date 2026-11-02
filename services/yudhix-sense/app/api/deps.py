"""Request context: who is calling (Keycloak token) and which workspace (X-Tenant-Id).

Route dependencies:
  principal  -> signed-in user, no workspace needed (e.g. /me, create workspace, accept invite)
  membership -> signed-in member of the X-Tenant-Id workspace (read access)
  tenant_id  -> just the workspace id, for read routes
  actor      -> a member who may change content (admin / approver / agent; analysts are read-only)
  require(p) -> a member holding permission p (e.g. "team.manage")
"""
import uuid
from typing import Callable, Optional

from fastapi import Depends, Header, HTTPException

from app.platform.auth import AuthError, Membership, Principal, load_membership, verify_token
from app.workflow.state import Actor


def principal(authorization: Optional[str] = Header(default=None)) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Sign in to continue.", headers={"WWW-Authenticate": "Bearer"})
    try:
        return verify_token(authorization[7:].strip())
    except AuthError as e:
        raise HTTPException(e.status_code, str(e), headers={"WWW-Authenticate": "Bearer"})


def membership(user: Principal = Depends(principal), x_tenant_id: Optional[str] = Header(default=None)) -> Membership:
    if not x_tenant_id:
        raise HTTPException(400, "Pick a workspace first (X-Tenant-Id header is missing).")
    try:
        uuid.UUID(x_tenant_id)
    except ValueError:
        raise HTTPException(400, "X-Tenant-Id must be a workspace id.")
    try:
        return load_membership(user, x_tenant_id)
    except AuthError as e:
        raise HTTPException(e.status_code, str(e))


def tenant_id(member: Membership = Depends(membership)) -> str:
    return member.tenant_id


def require(permission: str) -> Callable[..., Membership]:
    def check(member: Membership = Depends(membership)) -> Membership:
        if not member.can(permission):
            raise HTTPException(403, _denied(permission))
        return member
    return check


def actor(member: Membership = Depends(membership)) -> Actor:
    """Someone allowed to change content. Approvers and admins can also review replies."""
    if not member.can("content.write"):
        raise HTTPException(403, _denied("content.write"))
    return Actor(id=member.user_id, role="approver" if member.can("reply.approve") else "agent")


def _denied(permission: str) -> str:
    return {
        "workspace.manage": "Only workspace admins can change workspace settings.",
        "team.manage": "Only workspace admins can manage the team.",
        "billing.manage": "Only workspace admins can change billing.",
        "content.write": "Your role is read-only in this workspace. Ask an admin for agent access.",
        "reply.approve": "Only approvers and admins can review replies.",
    }.get(permission, "You don't have permission to do that.")
