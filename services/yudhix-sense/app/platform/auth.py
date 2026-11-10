"""Keycloak token verification and workspace membership.

Every API request (except the public ones) must carry `Authorization: Bearer <access token>`
issued by the Yudhix Keycloak realm to the web/mobile client. The workspace being acted on
comes from `X-Tenant-Id`, and the caller must be an active member of it. Roles are per
workspace, stored in tenant_user.roles, not in the token, so one person can be an admin in one
brand's workspace and an agent in another.
"""
import logging
from dataclasses import dataclass
from typing import Optional

import jwt
from jwt import PyJWKClient

from app.core import config
from app.core.database import fetch_one

logger = logging.getLogger(__name__)

ROLES = ("admin", "approver", "agent", "analyst")
ROLE_LABELS = {"admin": "Admin", "approver": "Approver", "agent": "Agent", "analyst": "Analyst"}

# What each role may do. Kept in one place so the API and UI agree.
#   admin    : everything, incl. workspace settings, team and billing
#   approver : review + all agent actions
#   agent    : analyze videos, manage knowledge, draft / submit / post replies, creator notes
#   analyst  : read-only (reports, inbox, insights)
PERMISSIONS = {
    "workspace.manage": {"admin"},
    "team.manage": {"admin"},
    "billing.manage": {"admin"},
    "content.write": {"admin", "approver", "agent"},
    "reply.approve": {"admin", "approver"},
}


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 401):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class Principal:
    """The signed-in person, from the verified token."""
    sub: str
    email: str
    name: str
    email_verified: bool


@dataclass(frozen=True)
class Membership:
    """The signed-in person inside one workspace."""
    tenant_id: str
    tenant_name: str
    user_id: str
    role: str
    email: str
    name: str
    is_demo: bool = False

    def can(self, permission: str) -> bool:
        return self.role in PERMISSIONS.get(permission, set())


_jwks: Optional[PyJWKClient] = None


def _jwks_client() -> PyJWKClient:
    global _jwks
    if _jwks is None:
        _jwks = PyJWKClient(config.KEYCLOAK_JWKS_URL, cache_keys=True, lifespan=3600, timeout=5)
    return _jwks


def verify_token(token: str) -> Principal:
    """Validate signature, expiry, issuer and client. Raises AuthError on anything wrong."""
    try:
        key = _jwks_client().get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token, key, algorithms=["RS256"], issuer=config.KEYCLOAK_ISSUER,
            options={"verify_aud": False, "require": ["exp", "iat", "sub", "iss"]}, leeway=30,
        )
    except jwt.ExpiredSignatureError:
        raise AuthError("Your session expired. Sign in again.")
    except jwt.PyJWKClientError as e:
        logger.error("Can't load Keycloak signing keys from %s: %s", config.KEYCLOAK_JWKS_URL, e)
        raise AuthError("Sign-in service is unavailable. Try again shortly.", 503)
    except jwt.InvalidTokenError as e:
        raise AuthError(f"Invalid sign-in token ({e.__class__.__name__}).")
    return principal_from_claims(claims)


def principal_from_claims(claims: dict) -> Principal:
    if claims.get("azp") not in config.KEYCLOAK_CLIENT_IDS:
        raise AuthError("This token wasn't issued to the Yudhix app.")
    if claims.get("typ", "Bearer") != "Bearer":
        raise AuthError("Use an access token.")
    email = (claims.get("email") or "").strip().lower()
    if not email:
        raise AuthError("Your account has no email address.", 403)
    name = claims.get("name") or " ".join(x for x in (claims.get("given_name"), claims.get("family_name")) if x) \
        or claims.get("preferred_username") or email.split("@")[0]
    return Principal(sub=claims["sub"], email=email, name=name, email_verified=bool(claims.get("email_verified")))


def load_membership(principal: Principal, tenant_id: str) -> Membership:
    row = fetch_one(
        """SELECT tu.roles, tu.full_name, t.name AS tenant_name, t.status, t.is_demo
           FROM tenant_user tu JOIN tenant t ON t.id = tu.tenant_id
           WHERE tu.tenant_id = %s AND tu.keycloak_user_id = %s AND tu.active""",
        (tenant_id, principal.sub))
    if not row or row["status"] == "DELETED":
        raise AuthError("You don't have access to this workspace.", 403)
    role = (row["roles"] or ["analyst"])[0]
    return Membership(tenant_id=tenant_id, tenant_name=row["tenant_name"], user_id=principal.sub,
                      role=role if role in ROLES else "analyst", email=principal.email,
                      name=row["full_name"] or principal.name, is_demo=bool(row["is_demo"]))
