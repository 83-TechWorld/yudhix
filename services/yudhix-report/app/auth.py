"""Who is asking, and which workspaces they may report on.

Same rules as yudhix-sense: a Keycloak access token issued to the Yudhix app, and an active
membership per workspace (tenant_user). Any member may see reports, including read-only analysts.
"""
import logging
from dataclasses import dataclass
from typing import List, Optional

import jwt
from fastapi import Header, HTTPException
from jwt import PyJWKClient

from app import config
from app.db import fetch_all

logger = logging.getLogger(__name__)

ROLE_LABELS = {"admin": "Admin", "approver": "Approver", "agent": "Agent", "analyst": "Analyst"}


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 401):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class Principal:
    sub: str
    email: str
    name: str


@dataclass(frozen=True)
class Workspace:
    id: str
    name: str
    role: str
    is_demo: bool
    plan: Optional[str]


_jwks: Optional[PyJWKClient] = None


def _jwks_client() -> PyJWKClient:
    global _jwks
    if _jwks is None:
        _jwks = PyJWKClient(config.KEYCLOAK_JWKS_URL, cache_keys=True, lifespan=3600, timeout=5)
    return _jwks


def verify_token(token: str) -> Principal:
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
    name = claims.get("name") or claims.get("preferred_username") or email.split("@")[0]
    return Principal(sub=claims["sub"], email=email, name=name)


def principal(authorization: Optional[str] = Header(default=None)) -> Principal:
    """FastAPI dependency: the signed-in person."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Sign in to continue.", headers={"WWW-Authenticate": "Bearer"})
    try:
        return verify_token(authorization[7:].strip())
    except AuthError as e:
        raise HTTPException(e.status_code, str(e), headers={"WWW-Authenticate": "Bearer"})


def my_workspaces(user: Principal) -> List[Workspace]:
    """Every workspace this person is an active member of."""
    rows = fetch_all(
        """SELECT t.id::text AS id, t.name, tu.roles, t.is_demo, t.plan_code
           FROM tenant_user tu JOIN tenant t ON t.id = tu.tenant_id
           WHERE tu.keycloak_user_id = %s AND tu.active AND t.status <> 'DELETED'
           ORDER BY t.is_demo, lower(t.name)""", (user.sub,))
    out = []
    for r in rows:
        role = (r["roles"] or ["analyst"])[0]
        out.append(Workspace(id=r["id"], name=r["name"], role=role if role in ROLE_LABELS else "analyst",
                             is_demo=bool(r["is_demo"]), plan=r["plan_code"]))
    return out


def allowed(user: Principal, workspace_ids: List[str]) -> List[Workspace]:
    """The requested workspaces, in the user's order. Any workspace they don't belong to is refused."""
    mine = {w.id: w for w in my_workspaces(user)}
    wanted = list(dict.fromkeys(workspace_ids))
    if not wanted:
        raise HTTPException(400, "Pick at least one workspace.")
    if len(wanted) > config.MAX_WORKSPACES:
        raise HTTPException(400, f"A report can cover up to {config.MAX_WORKSPACES} workspaces.")
    missing = [w for w in wanted if w not in mine]
    if missing:
        raise HTTPException(403, "You don't have access to one or more of these workspaces.")
    return [mine[w] for w in wanted]
