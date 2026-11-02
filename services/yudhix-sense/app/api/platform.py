"""SaaS API: account, workspaces, onboarding, team, billing, notifications, public pricing."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import membership, principal, require
from app.core.database import fetch_all
from app.platform import billing, notifications, workspaces
from app.platform.auth import Membership, Principal

router = APIRouter(prefix="/api/v1", tags=["saas"])


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except workspaces.WorkspaceError as e:
        raise HTTPException(e.status_code, str(e))
    except billing.QuotaError as e:
        raise HTTPException(402, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


# ----------------------------------------------------------------------------- public

@router.get("/public/plans")
def public_plans():
    return {"plans": billing.plans()}


@router.get("/public/countries")
def public_countries():
    rows = fetch_all("SELECT country_code, country_name, currency FROM country_config WHERE enabled ORDER BY country_name")
    return {"countries": [{"code": r["country_code"], "name": r["country_name"], "currency": r["currency"]} for r in rows]}


@router.get("/public/invitations/{token}")
def invitation_preview(token: str):
    return _run(workspaces.preview_invitation, token)


# ----------------------------------------------------------------------------- account

@router.get("/me")
def me(user: Principal = Depends(principal)):
    return workspaces.me(user)


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    country: str = Field(..., min_length=2, max_length=10)
    industry: Optional[str] = Field(None, max_length=80)
    teamSize: Optional[str] = Field(None, max_length=20)


@router.post("/workspaces", status_code=201)
def create_workspace(body: WorkspaceCreate, user: Principal = Depends(principal)):
    return _run(workspaces.create, user, body.name, body.country, body.industry, body.teamSize)


@router.post("/workspaces/demo/join")
def join_demo(user: Principal = Depends(principal)):
    return _run(workspaces.join_demo, user)


@router.post("/invitations/{token}/accept")
def accept_invitation(token: str, user: Principal = Depends(principal)):
    return _run(workspaces.accept_invitation, user, token)


# ----------------------------------------------------------------------------- current workspace

class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=120)
    country: Optional[str] = Field(None, max_length=10)
    industry: Optional[str] = Field(None, max_length=80)
    teamSize: Optional[str] = Field(None, max_length=20)


@router.get("/workspace")
def get_workspace(member: Membership = Depends(membership)):
    return {**workspaces.workspace(member.tenant_id), "role": member.role}


@router.patch("/workspace")
def update_workspace(body: WorkspaceUpdate, member: Membership = Depends(require("workspace.manage"))):
    return _run(workspaces.update, member, body.model_dump())


class DeleteWorkspace(BaseModel):
    confirm_name: str


@router.post("/workspace/delete", status_code=204)
def delete_workspace(body: DeleteWorkspace, member: Membership = Depends(require("workspace.manage"))):
    _run(workspaces.delete, member, body.confirm_name)


@router.post("/workspace/leave", status_code=204)
def leave_workspace(member: Membership = Depends(membership)):
    _run(workspaces.leave, member)


@router.get("/workspace/onboarding")
def onboarding(member: Membership = Depends(membership)):
    return workspaces.onboarding(member.tenant_id)


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    category: Optional[str] = Field(None, max_length=100)


@router.get("/workspace/products")
def products(member: Membership = Depends(membership)):
    return {"products": workspaces.products(member.tenant_id)}


@router.post("/workspace/products", status_code=201)
def add_product(body: ProductCreate, member: Membership = Depends(require("content.write"))):
    return _run(workspaces.add_product, member, body.name, body.category)


# ----------------------------------------------------------------------------- team

@router.get("/team")
def team(member: Membership = Depends(membership)):
    return {"members": workspaces.members(member.tenant_id),
            "invitations": workspaces.invitations(member.tenant_id) if member.can("team.manage") else [],
            "canManage": member.can("team.manage")}


class InviteBody(BaseModel):
    emails: List[str] = Field(..., min_length=1, max_length=20)
    role: str


@router.post("/team/invitations", status_code=201)
def invite(body: InviteBody, member: Membership = Depends(require("team.manage"))):
    results = []
    for email in body.emails:
        try:
            results.append({"email": email, "ok": True, "invitation": workspaces.invite(member, email, body.role)})
        except workspaces.WorkspaceError as e:
            results.append({"email": email, "ok": False, "error": str(e)})
    return {"results": results}


@router.post("/team/invitations/{invitation_id}/resend")
def resend(invitation_id: str, member: Membership = Depends(require("team.manage"))):
    return _run(workspaces.resend, member, invitation_id)


@router.delete("/team/invitations/{invitation_id}", status_code=204)
def revoke(invitation_id: str, member: Membership = Depends(require("team.manage"))):
    _run(workspaces.revoke, member, invitation_id)


class RoleBody(BaseModel):
    role: str


@router.patch("/team/members/{user_id}")
def set_role(user_id: str, body: RoleBody, member: Membership = Depends(require("team.manage"))):
    return {"members": _run(workspaces.set_role, member, user_id, body.role)}


@router.delete("/team/members/{user_id}")
def remove_member(user_id: str, member: Membership = Depends(require("team.manage"))):
    return {"members": _run(workspaces.remove_member, member, user_id)}


# ----------------------------------------------------------------------------- billing

@router.get("/billing")
def billing_summary(member: Membership = Depends(membership)):
    return _run(billing.summary, member.tenant_id)


class PlanChange(BaseModel):
    plan_id: str
    interval: str = "MONTH"


@router.post("/billing/plan")
def change_plan(body: PlanChange, member: Membership = Depends(require("billing.manage"))):
    return _run(billing.change_plan, member.tenant_id, member.user_id, body.plan_id, body.interval)


@router.get("/billing/invoices")
def invoices(member: Membership = Depends(require("billing.manage"))):
    return {"invoices": billing.invoices(member.tenant_id)}


@router.get("/billing/invoices/{invoice_id}")
def invoice(invoice_id: str, member: Membership = Depends(require("billing.manage"))):
    found = billing.invoice(member.tenant_id, invoice_id)
    if not found:
        raise HTTPException(404, "Invoice not found")
    return found


# ----------------------------------------------------------------------------- notifications

@router.get("/notifications")
def list_notifications(member: Membership = Depends(membership)):
    return notifications.list_for(member.tenant_id, member.user_id)


class ReadBody(BaseModel):
    ids: Optional[List[int]] = None


@router.post("/notifications/read", status_code=204)
def read_notifications(body: ReadBody, member: Membership = Depends(membership)):
    notifications.mark_read(member.tenant_id, member.user_id, body.ids)
