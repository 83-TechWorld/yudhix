"""Workspaces (tenants), members, invitations and onboarding."""
import hashlib
import re
import secrets
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from app.core import config
from app.core.database import append_audit, cursor, fetch_all, fetch_one
from app.platform import billing, mailer
from app.platform.auth import ROLE_LABELS, ROLES, Membership, Principal
from app.platform.notifications import notify


class WorkspaceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _iso(v):
    return v.isoformat() if hasattr(v, "isoformat") else v


def slugify(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (slug or "workspace")[:48].strip("-")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def is_expired(expires_at: datetime, now: Optional[datetime] = None) -> bool:
    return expires_at <= (now or datetime.now(timezone.utc))


def _unique_slug(cur, name: str) -> str:
    base = slugify(name)
    cur.execute("SELECT slug FROM tenant WHERE slug = %s OR slug LIKE %s", (base, f"{base}-%"))
    taken = {r["slug"] for r in cur.fetchall()}
    if base not in taken:
        return base
    for n in range(2, 1000):
        if f"{base}-{n}" not in taken:
            return f"{base}-{n}"
    return f"{base}-{secrets.token_hex(3)}"


# ----------------------------------------------------------------------------- me

def me(user: Principal) -> Dict:
    rows = fetch_all(
        """SELECT t.id, t.name, t.slug, t.is_demo, t.hq_country, tu.roles, s.plan_id, s.status AS sub_status,
                  s.trial_ends_at, p.name AS plan_name
           FROM tenant_user tu JOIN tenant t ON t.id = tu.tenant_id
           LEFT JOIN subscription s ON s.tenant_id = t.id LEFT JOIN plan p ON p.id = s.plan_id
           WHERE tu.keycloak_user_id = %s AND tu.active AND t.status <> 'DELETED'
           ORDER BY t.is_demo, t.name""", (user.sub,))
    invites = fetch_all(
        """SELECT i.id, i.role, i.expires_at, t.name AS workspace FROM workspace_invitation i
           JOIN tenant t ON t.id = i.tenant_id
           WHERE lower(i.email) = %s AND i.status = 'PENDING' AND i.expires_at > now() AND t.status <> 'DELETED'
             AND NOT EXISTS (SELECT 1 FROM tenant_user tu WHERE tu.tenant_id = i.tenant_id
                             AND tu.keycloak_user_id = %s AND tu.active)""", (user.email, user.sub))
    with cursor(commit=True) as cur:  # keep names/emails in sync with Keycloak
        cur.execute("""UPDATE tenant_user SET email = %s, full_name = %s, last_seen_at = now()
                       WHERE keycloak_user_id = %s AND active""", (user.email, user.name, user.sub))
    return {
        "user": {"id": user.sub, "email": user.email, "name": user.name, "emailVerified": user.email_verified},
        "workspaces": [{
            "id": str(r["id"]), "name": r["name"], "slug": r["slug"], "isDemo": r["is_demo"], "country": r["hq_country"],
            "role": (r["roles"] or ["analyst"])[0], "plan": r["plan_name"],
            "subscriptionStatus": billing.effective_status({"status": r["sub_status"], "trial_ends_at": r["trial_ends_at"]})
            if r["sub_status"] else None,
            "trialEndsAt": _iso(r["trial_ends_at"]),
        } for r in rows],
        "pendingInvitations": [{"id": str(i["id"]), "workspace": i["workspace"], "role": i["role"],
                                "expiresAt": _iso(i["expires_at"])} for i in invites],
        "demoAvailable": config.DEMO_WORKSPACE_JOIN,
    }


# ----------------------------------------------------------------------------- workspaces

def create(user: Principal, name: str, country: str, industry: Optional[str], team_size: Optional[str]) -> Dict:
    name = (name or "").strip()
    if len(name) < 2:
        raise WorkspaceError("Give your workspace a name (at least 2 characters).")
    if not user.email_verified:
        raise WorkspaceError("Verify your email address before creating a workspace.", 403)
    if not fetch_one("SELECT 1 FROM country_config WHERE country_code = %s AND enabled", (country,)):
        raise WorkspaceError("Pick a supported country.")
    owned = fetch_one("""SELECT count(*) AS n FROM tenant WHERE created_by = %s AND status <> 'DELETED'""", (user.sub,))
    if owned["n"] >= config.MAX_WORKSPACES_PER_USER:
        raise WorkspaceError(f"You can create up to {config.MAX_WORKSPACES_PER_USER} workspaces. Contact sales for more.")
    tenant_id = str(uuid.uuid4())
    with cursor(commit=True) as cur:
        cur.execute("SELECT pg_advisory_xact_lock(hashtext('tenant-slug'))")
        slug = _unique_slug(cur, name)
        region = fetch_one("SELECT data_region FROM country_config WHERE country_code = %s", (country,))["data_region"]
        cur.execute(
            """INSERT INTO tenant (id, name, slug, hq_country, operating_countries, data_region, status, plan_code,
                   industry, team_size, created_by)
               VALUES (%s, %s, %s, %s, %s, %s, 'ACTIVE', %s, %s, %s, %s)""",
            (tenant_id, name[:255], slug, country, [country], region, config.TRIAL_PLAN, industry, team_size, user.sub))
        cur.execute("""INSERT INTO tenant_user (id, tenant_id, keycloak_user_id, email, full_name, roles, active)
                       VALUES (%s, %s, %s, %s, %s, '{admin}', true)""",
                    (str(uuid.uuid4()), tenant_id, user.sub, user.email, user.name))
        currency = fetch_one("SELECT currency FROM country_config WHERE country_code = %s", (country,))["currency"]
        billing.start_trial(cur, tenant_id, currency)
        append_audit(cur, tenant_id, user.sub, "USER", "WORKSPACE_CREATED", "TENANT", tenant_id,
                     {"name": name, "slug": slug, "country": country})
    notify(tenant_id, "welcome", f"Welcome to {name}",
           f"Your {config.TRIAL_DAYS}-day trial has started. Analyze your first video to see what creators are claiming.",
           "/analyze", user_ids=[user.sub])
    return workspace(tenant_id)


def workspace(tenant_id: str) -> Dict:
    t = fetch_one("""SELECT t.*, c.country_name FROM tenant t LEFT JOIN country_config c ON c.country_code = t.hq_country
                     WHERE t.id = %s""", (tenant_id,))
    return {"id": str(t["id"]), "name": t["name"], "slug": t["slug"], "country": t["hq_country"],
            "countryName": t["country_name"], "industry": t.get("industry"), "teamSize": t.get("team_size"),
            "dataRegion": t["data_region"], "isDemo": t["is_demo"], "createdAt": _iso(t["created_at"])}


def update(member: Membership, data: Dict) -> Dict:
    fields = {k: v for k, v in data.items() if v is not None}
    if "name" in fields and len(fields["name"].strip()) < 2:
        raise WorkspaceError("Workspace name is too short.")
    if "country" in fields and not fetch_one("SELECT 1 FROM country_config WHERE country_code = %s AND enabled",
                                             (fields["country"],)):
        raise WorkspaceError("Pick a supported country.")
    with cursor(commit=True) as cur:
        cur.execute("""UPDATE tenant SET name = COALESCE(%s, name), hq_country = COALESCE(%s, hq_country),
                              industry = COALESCE(%s, industry), team_size = COALESCE(%s, team_size), updated_at = now()
                       WHERE id = %s""",
                    (fields.get("name", "").strip() or None, fields.get("country"), fields.get("industry"),
                     fields.get("teamSize"), member.tenant_id))
        append_audit(cur, member.tenant_id, member.user_id, "USER", "WORKSPACE_UPDATED", "TENANT", member.tenant_id, fields)
    return workspace(member.tenant_id)


def delete(member: Membership, confirm_name: str) -> None:
    if member.is_demo:
        raise WorkspaceError("The demo workspace can't be deleted.", 403)
    if (confirm_name or "").strip() != member.tenant_name:
        raise WorkspaceError("Type the workspace name exactly to confirm.")
    with cursor(commit=True) as cur:
        cur.execute("""UPDATE tenant SET status = 'DELETED', deleted_at = now(), updated_at = now() WHERE id = %s""",
                    (member.tenant_id,))
        cur.execute("""UPDATE subscription SET status = 'CANCELED', updated_at = now() WHERE tenant_id = %s""",
                    (member.tenant_id,))
        cur.execute("""UPDATE workspace_invitation SET status = 'REVOKED' WHERE tenant_id = %s AND status = 'PENDING'""",
                    (member.tenant_id,))
        append_audit(cur, member.tenant_id, member.user_id, "USER", "WORKSPACE_DELETED", "TENANT", member.tenant_id,
                     {"name": member.tenant_name})


def leave(member: Membership) -> None:
    # Anyone can rejoin the shared demo workspace, so it never needs a last admin.
    if member.role == "admin" and not member.is_demo and _admin_count(member.tenant_id) <= 1:
        raise WorkspaceError("You're the only admin. Make someone else an admin first, or delete the workspace.")
    with cursor(commit=True) as cur:
        cur.execute("UPDATE tenant_user SET active = false WHERE tenant_id = %s AND keycloak_user_id = %s",
                    (member.tenant_id, member.user_id))
        append_audit(cur, member.tenant_id, member.user_id, "USER", "MEMBER_LEFT", "MEMBER", member.user_id, {})


def join_demo(user: Principal) -> Dict:
    if not config.DEMO_WORKSPACE_JOIN:
        raise WorkspaceError("The demo workspace isn't available.", 404)
    demo = fetch_one("SELECT id FROM tenant WHERE is_demo AND status = 'ACTIVE' LIMIT 1")
    if not demo:
        raise WorkspaceError("The demo workspace isn't set up.", 404)
    _add_member(str(demo["id"]), user, "admin", invited_by=None, action="DEMO_JOINED")
    return workspace(str(demo["id"]))


def _admin_count(tenant_id: str) -> int:
    return int(fetch_one("""SELECT count(*) AS n FROM tenant_user WHERE tenant_id = %s AND active
                            AND 'admin' = ANY(roles)""", (tenant_id,))["n"])


def _add_member(tenant_id: str, user: Principal, role: str, invited_by: Optional[str], action: str) -> None:
    with cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO tenant_user (id, tenant_id, keycloak_user_id, email, full_name, roles, active, invited_by)
               VALUES (%s, %s, %s, %s, %s, %s, true, %s)
               ON CONFLICT (tenant_id, keycloak_user_id) DO UPDATE
                   SET active = true, roles = EXCLUDED.roles, email = EXCLUDED.email, full_name = EXCLUDED.full_name""",
            (str(uuid.uuid4()), tenant_id, user.sub, user.email, user.name, [role], invited_by))
        append_audit(cur, tenant_id, user.sub, "USER", action, "MEMBER", user.sub, {"role": role, "email": user.email})


# ----------------------------------------------------------------------------- onboarding

def onboarding(tenant_id: str) -> Dict:
    row = fetch_one(
        """SELECT (SELECT count(*) FROM product WHERE tenant_id = %(t)s AND active) AS products,
                  (SELECT count(*) FROM product_knowledge WHERE tenant_id = %(t)s) AS knowledge,
                  (SELECT count(*) FROM video_analysis_job WHERE tenant_id = %(t)s) +
                  (SELECT count(*) FROM video_truth_analysis WHERE tenant_id = %(t)s) AS videos,
                  (SELECT count(*) FROM tenant_user WHERE tenant_id = %(t)s AND active) +
                  (SELECT count(*) FROM workspace_invitation WHERE tenant_id = %(t)s AND status <> 'REVOKED') AS people,
                  (SELECT count(*) FROM reply WHERE tenant_id = %(t)s) AS replies""", {"t": tenant_id})
    steps = [
        {"key": "product", "label": "Add your first product", "done": row["products"] > 0, "link": "/onboarding"},
        {"key": "knowledge", "label": "Add an official fact to check claims against", "done": row["knowledge"] > 0,
         "link": "/knowledge"},
        {"key": "video", "label": "Analyze your first video", "done": row["videos"] > 0, "link": "/analyze"},
        {"key": "team", "label": "Invite a teammate", "done": row["people"] > 1, "link": "/settings/team"},
        {"key": "reply", "label": "Draft your first reply", "done": row["replies"] > 0, "link": "/inbox"},
    ]
    return {"steps": steps, "completed": sum(s["done"] for s in steps), "total": len(steps)}


def products(tenant_id: str) -> List[Dict]:
    return [{"id": str(r["id"]), "name": r["name"], "code": r["code"], "category": r["category"]}
            for r in fetch_all("SELECT * FROM product WHERE tenant_id = %s AND active ORDER BY created_at", (tenant_id,))]


def add_product(member: Membership, name: str, category: Optional[str]) -> Dict:
    name = (name or "").strip()
    if len(name) < 2:
        raise WorkspaceError("Product name is too short.")
    product_id = str(uuid.uuid4())
    with cursor(commit=True) as cur:
        code = slugify(name)
        cur.execute("SELECT count(*) AS n FROM product WHERE tenant_id = %s AND code LIKE %s", (member.tenant_id, f"{code}%"))
        if cur.fetchone()["n"]:
            code = f"{code}-{secrets.token_hex(2)}"
        cur.execute("""INSERT INTO product (id, tenant_id, code, name, category) VALUES (%s, %s, %s, %s, %s)""",
                    (product_id, member.tenant_id, code, name[:255], (category or "").strip()[:100] or None))
        append_audit(cur, member.tenant_id, member.user_id, "USER", "PRODUCT_ADDED", "PRODUCT", product_id, {"name": name})
    return {"id": product_id, "name": name, "code": code, "category": category}


# ----------------------------------------------------------------------------- team

def members(tenant_id: str) -> List[Dict]:
    rows = fetch_all("""SELECT * FROM tenant_user WHERE tenant_id = %s AND active
                        ORDER BY (roles[1] = 'admin') DESC, lower(coalesce(full_name, email))""", (tenant_id,))
    return [{"userId": r["keycloak_user_id"], "email": r["email"], "name": r["full_name"] or r["email"],
             "role": (r["roles"] or ["analyst"])[0], "joinedAt": _iso(r["created_at"]),
             "lastSeenAt": _iso(r.get("last_seen_at"))} for r in rows]


def set_role(member: Membership, user_id: str, role: str) -> List[Dict]:
    if role not in ROLES:
        raise WorkspaceError("Unknown role.")
    target = fetch_one("""SELECT roles FROM tenant_user WHERE tenant_id = %s AND keycloak_user_id = %s AND active""",
                       (member.tenant_id, user_id))
    if not target:
        raise WorkspaceError("Member not found.", 404)
    current = (target["roles"] or ["analyst"])[0]
    if current == "admin" and role != "admin" and _admin_count(member.tenant_id) <= 1:
        raise WorkspaceError("A workspace needs at least one admin.")
    with cursor(commit=True) as cur:
        cur.execute("UPDATE tenant_user SET roles = %s WHERE tenant_id = %s AND keycloak_user_id = %s",
                    ([role], member.tenant_id, user_id))
        append_audit(cur, member.tenant_id, member.user_id, "USER", "MEMBER_ROLE_CHANGED", "MEMBER", user_id,
                     {"role": role}, {"role": current})
    notify(member.tenant_id, "team", f"Your role is now {ROLE_LABELS[role]}",
           f"{member.name} changed your role in {member.tenant_name}.", "/settings/team", user_ids=[user_id],
           exclude=member.user_id)
    return members(member.tenant_id)


def remove_member(member: Membership, user_id: str) -> List[Dict]:
    if user_id == member.user_id:
        raise WorkspaceError("Use “Leave workspace” to remove yourself.")
    target = fetch_one("""SELECT roles, email FROM tenant_user WHERE tenant_id = %s AND keycloak_user_id = %s AND active""",
                       (member.tenant_id, user_id))
    if not target:
        raise WorkspaceError("Member not found.", 404)
    if "admin" in (target["roles"] or []) and _admin_count(member.tenant_id) <= 1:
        raise WorkspaceError("A workspace needs at least one admin.")
    with cursor(commit=True) as cur:
        cur.execute("UPDATE tenant_user SET active = false WHERE tenant_id = %s AND keycloak_user_id = %s",
                    (member.tenant_id, user_id))
        append_audit(cur, member.tenant_id, member.user_id, "USER", "MEMBER_REMOVED", "MEMBER", user_id,
                     {"email": target["email"]})
    return members(member.tenant_id)


def _invite(r: Dict) -> Dict:
    return {"id": str(r["id"]), "email": r["email"], "role": r["role"], "status": r["status"],
            "expiresAt": _iso(r["expires_at"]), "createdAt": _iso(r["created_at"]),
            "expired": is_expired(r["expires_at"]), "invitedBy": r.get("inviter_name")}


def invitations(tenant_id: str) -> List[Dict]:
    rows = fetch_all("""SELECT i.*, tu.full_name AS inviter_name FROM workspace_invitation i
                        LEFT JOIN tenant_user tu ON tu.tenant_id = i.tenant_id AND tu.keycloak_user_id = i.invited_by
                        WHERE i.tenant_id = %s AND i.status = 'PENDING' ORDER BY i.created_at DESC""", (tenant_id,))
    return [_invite(r) for r in rows]


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def invite(member: Membership, email: str, role: str) -> Dict:
    email = (email or "").strip().lower()
    if not EMAIL_RE.match(email):
        raise WorkspaceError("Enter a valid email address.")
    if role not in ROLES:
        raise WorkspaceError("Unknown role.")
    if fetch_one("""SELECT 1 FROM tenant_user WHERE tenant_id = %s AND lower(email) = %s AND active""",
                 (member.tenant_id, email)):
        raise WorkspaceError(f"{email} is already a member.", 409)
    if fetch_one("""SELECT 1 FROM workspace_invitation WHERE tenant_id = %s AND lower(email) = %s AND status = 'PENDING'
                    AND expires_at > now()""", (member.tenant_id, email)):
        raise WorkspaceError(f"{email} already has a pending invitation. Resend it instead.", 409)
    try:
        billing.check_seat(member.tenant_id)
    except billing.QuotaError as e:
        raise WorkspaceError(str(e), 402)
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=config.INVITE_TTL_DAYS)
    with cursor(commit=True) as cur:
        # An expired pending invite for the same email would block the unique index; retire it.
        cur.execute("""UPDATE workspace_invitation SET status = 'REVOKED' WHERE tenant_id = %s AND lower(email) = %s
                       AND status = 'PENDING'""", (member.tenant_id, email))
        cur.execute("""INSERT INTO workspace_invitation (tenant_id, email, role, token_hash, invited_by, expires_at)
                       VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
                    (member.tenant_id, email, role, hash_token(token), member.user_id, expires))
        row = dict(cur.fetchone())
        append_audit(cur, member.tenant_id, member.user_id, "USER", "MEMBER_INVITED", "INVITATION", str(row["id"]),
                     {"email": email, "role": role})
    link = f"{config.APP_URL}/invite/{token}"
    sent = mailer.invitation(email, member.tenant_name, member.name, ROLE_LABELS[role], link, config.INVITE_TTL_DAYS)
    return {**_invite(row), "link": link, "emailSent": sent}


def resend(member: Membership, invitation_id: str) -> Dict:
    row = fetch_one("""SELECT * FROM workspace_invitation WHERE tenant_id = %s AND id = %s AND status = 'PENDING'""",
                    (member.tenant_id, invitation_id))
    if not row:
        raise WorkspaceError("Invitation not found.", 404)
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=config.INVITE_TTL_DAYS)
    with cursor(commit=True) as cur:
        cur.execute("""UPDATE workspace_invitation SET token_hash = %s, expires_at = %s WHERE id = %s RETURNING *""",
                    (hash_token(token), expires, invitation_id))
        row = dict(cur.fetchone())
    link = f"{config.APP_URL}/invite/{token}"
    sent = mailer.invitation(row["email"], member.tenant_name, member.name, ROLE_LABELS[row["role"]], link,
                             config.INVITE_TTL_DAYS)
    return {**_invite(row), "link": link, "emailSent": sent}


def revoke(member: Membership, invitation_id: str) -> None:
    with cursor(commit=True) as cur:
        cur.execute("""UPDATE workspace_invitation SET status = 'REVOKED' WHERE tenant_id = %s AND id = %s
                       AND status = 'PENDING' RETURNING email""", (member.tenant_id, invitation_id))
        row = cur.fetchone()
        if not row:
            raise WorkspaceError("Invitation not found.", 404)
        append_audit(cur, member.tenant_id, member.user_id, "USER", "INVITATION_REVOKED", "INVITATION", invitation_id,
                     {"email": row["email"]})


def preview_invitation(token: str) -> Dict:
    """Public: what the invite page shows before sign-in. Reveals no more than the email did."""
    row = fetch_one("""SELECT i.*, t.name AS workspace, t.status AS tenant_status, tu.full_name AS inviter_name
                       FROM workspace_invitation i JOIN tenant t ON t.id = i.tenant_id
                       LEFT JOIN tenant_user tu ON tu.tenant_id = i.tenant_id AND tu.keycloak_user_id = i.invited_by
                       WHERE i.token_hash = %s""", (hash_token(token),))
    if not row or row["tenant_status"] == "DELETED" or row["status"] == "REVOKED":
        raise WorkspaceError("This invitation link isn't valid. Ask your admin for a new one.", 404)
    if row["status"] == "ACCEPTED":
        raise WorkspaceError("This invitation was already used. Sign in to open the workspace.", 410)
    if is_expired(row["expires_at"]):
        raise WorkspaceError("This invitation has expired. Ask your admin to resend it.", 410)
    local, _, domain = row["email"].partition("@")
    return {"workspace": row["workspace"], "role": row["role"], "roleLabel": ROLE_LABELS[row["role"]],
            "invitedBy": row["inviter_name"] or "A teammate", "email": f"{local[:2]}{'•' * max(1, len(local) - 2)}@{domain}",
            "expiresAt": _iso(row["expires_at"])}


def accept_invitation(user: Principal, token: str) -> Dict:
    row = fetch_one("""SELECT i.*, t.status AS tenant_status FROM workspace_invitation i
                       JOIN tenant t ON t.id = i.tenant_id WHERE i.token_hash = %s""", (hash_token(token),))
    if not row or row["status"] != "PENDING" or row["tenant_status"] == "DELETED":
        raise WorkspaceError("This invitation link isn't valid anymore.", 404)
    if is_expired(row["expires_at"]):
        raise WorkspaceError("This invitation has expired. Ask your admin to resend it.", 410)
    if row["email"].lower() != user.email.lower():
        raise WorkspaceError(f"This invitation was sent to a different email address. Sign in with that address "
                             f"(you're signed in as {user.email}).", 403)
    if not user.email_verified:
        raise WorkspaceError("Verify your email address first, then open the link again.", 403)
    tenant_id = str(row["tenant_id"])
    _add_member(tenant_id, user, row["role"], invited_by=row["invited_by"], action="INVITATION_ACCEPTED")
    with cursor(commit=True) as cur:
        cur.execute("""UPDATE workspace_invitation SET status = 'ACCEPTED', accepted_at = now(), accepted_by = %s
                       WHERE id = %s""", (user.sub, row["id"]))
    notify(tenant_id, "team", f"{user.name} joined the workspace", f"{user.email} accepted your invitation as "
           f"{ROLE_LABELS[row['role']]}.", "/settings/team", roles=["admin"], exclude=user.sub)
    return workspace(tenant_id)
