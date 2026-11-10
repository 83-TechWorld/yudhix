"""End-to-end SaaS API test against a running Keycloak + yudhix-sense (not run by pytest).

    ./.venv/bin/python tests/e2e_saas.py

Creates two throwaway Keycloak users and one workspace, checks sign-in, workspaces, invites, roles,
billing and notifications. At the end it deletes the Keycloak users, leaves the demo workspace and
soft-deletes its workspace (status DELETED; billing rows stay for the audit trail)."""
import base64
import hashlib
import html
import re
import secrets
import sys
import urllib.parse

import httpx

KC = "http://localhost:8180"
API = "http://localhost:8000/api/v1"
REDIRECT = "http://localhost:4200/"
RUN = secrets.token_hex(3)
PASSWORD = "Test-pass-" + secrets.token_hex(4)
created_users = []
failures = []


def check(label, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + label + (f"  [{detail}]" if detail and not cond else ""))
    if not cond:
        failures.append(label)


def admin_token():
    r = httpx.post(f"{KC}/realms/master/protocol/openid-connect/token",
                   data={"client_id": "admin-cli", "username": "admin", "password": "admin_yudhix_2026",
                         "grant_type": "password"})
    return r.json()["access_token"]


def create_user(email, first, last):
    h = {"Authorization": f"Bearer {admin_token()}"}
    r = httpx.post(f"{KC}/admin/realms/yudhix/users", headers=h, json={
        "username": email, "email": email, "firstName": first, "lastName": last, "enabled": True, "emailVerified": True,
        "credentials": [{"type": "password", "value": PASSWORD, "temporary": False}]})
    assert r.status_code == 201, r.text
    uid = r.headers["Location"].rsplit("/", 1)[1]
    created_users.append(uid)
    return uid


def login(email):
    """Authorization Code + PKCE, exactly like keycloak-js in the browser."""
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    with httpx.Client(follow_redirects=False) as c:
        r = c.get(f"{KC}/realms/yudhix/protocol/openid-connect/auth", params={
            "client_id": "yudhix-web", "redirect_uri": REDIRECT, "response_type": "code", "scope": "openid",
            "code_challenge": challenge, "code_challenge_method": "S256", "state": "x", "nonce": "y"})
        action = html.unescape(re.search(r'id="kc-form-login"[^>]*action="([^"]+)"', r.text).group(1))
        r = c.post(action, data={"username": email, "password": PASSWORD, "credentialId": ""})
        assert r.status_code == 302, f"login failed {r.status_code}"
        code = urllib.parse.parse_qs(urllib.parse.urlparse(r.headers["location"]).query)["code"][0]
        r = c.post(f"{KC}/realms/yudhix/protocol/openid-connect/token", data={
            "grant_type": "authorization_code", "client_id": "yudhix-web", "code": code, "redirect_uri": REDIRECT,
            "code_verifier": verifier})
        return r.json()["access_token"]


def api(token, method, path, tenant=None, **kw):
    h = {"Authorization": f"Bearer {token}"}
    if tenant:
        h["X-Tenant-Id"] = tenant
    return httpx.request(method, f"{API}{path}", headers=h, timeout=30, **kw)


try:
    admin_email, agent_email = f"e2e-admin-{RUN}@example.test", f"e2e-agent-{RUN}@example.test"
    create_user(admin_email, "Priya", "Admin")
    create_user(agent_email, "Arjun", "Agent")

    # password grant must be off for the web client
    r = httpx.post(f"{KC}/realms/yudhix/protocol/openid-connect/token",
                   data={"client_id": "yudhix-web", "grant_type": "password", "username": admin_email, "password": PASSWORD})
    check("password grant disabled", r.status_code in (400, 401), r.text[:100])

    A = login(admin_email)
    G = login(agent_email)
    check("PKCE login works", bool(A and G))
    check("garbage token rejected", api("abc.def.ghi", "GET", "/me").status_code == 401)

    me = api(A, "GET", "/me").json()
    check("new user has no workspaces", me["workspaces"] == [] and me["user"]["email"] == admin_email, me)

    r = api(A, "POST", "/workspaces", json={"name": f"Acme Audio {RUN}", "country": "IN", "industry": "Consumer electronics", "teamSize": "51-200"})
    check("create workspace", r.status_code == 201, r.text)
    ws = r.json()["id"]
    me = api(A, "GET", "/me").json()
    check("creator is admin on trial", me["workspaces"][0]["role"] == "admin" and me["workspaces"][0]["subscriptionStatus"] == "TRIALING", me["workspaces"])

    b = api(A, "GET", "/billing", tenant=ws).json()
    check("trial billing summary", b["status"] == "TRIALING" and b["plan"]["id"] == "PROFESSIONAL" and len(b["meters"]) == 5, b)
    check("India workspace bills in INR", b["plan"]["currency"] == "INR", b["plan"])

    check("add product", api(A, "POST", "/workspace/products", tenant=ws, json={"name": "SoundMax Pro Headphones", "category": "Audio"}).status_code == 201)
    ob = api(A, "GET", "/workspace/onboarding", tenant=ws).json()
    check("onboarding counts product", ob["steps"][0]["done"] and ob["completed"] == 1, ob)

    # Team: invite the agent
    r = api(A, "POST", "/team/invitations", tenant=ws, json={"emails": [agent_email, "not-an-email"], "role": "agent"})
    res = r.json()["results"]
    check("invite created + bad email rejected", res[0]["ok"] and not res[1]["ok"], res)
    link = res[0]["invitation"]["link"]
    token = link.rsplit("/", 1)[1]
    check("invitation email sent (Mailpit)", res[0]["invitation"]["emailSent"])
    mails = httpx.get("http://localhost:8025/api/v1/messages").json()["messages"]
    check("mailpit received invite", any(agent_email in str(m.get("To")) for m in mails))

    check("duplicate invite blocked", not api(A, "POST", "/team/invitations", tenant=ws, json={"emails": [agent_email], "role": "agent"}).json()["results"][0]["ok"])
    pv = httpx.get(f"{API}/public/invitations/{token}").json()
    check("public invite preview masks email", pv["workspace"].startswith("Acme") and "•" in pv["email"], pv)

    check("agent can't see workspace before accepting", api(G, "GET", "/workspace", tenant=ws).status_code == 403)
    check("admin can't accept agent's invite", api(A, "POST", f"/invitations/{token}/accept").status_code == 403)
    r = api(G, "POST", f"/invitations/{token}/accept")
    check("agent accepts invite", r.status_code == 200, r.text)
    check("invite link single-use", api(G, "POST", f"/invitations/{token}/accept").status_code == 404)
    me_g = api(G, "GET", "/me").json()
    check("agent sees workspace with agent role", me_g["workspaces"][0]["role"] == "agent", me_g)

    # Permissions
    check("agent can't rename workspace", api(G, "PATCH", "/workspace", tenant=ws, json={"name": "Hacked"}).status_code == 403)
    check("agent can't invite", api(G, "POST", "/team/invitations", tenant=ws, json={"emails": ["x@example.test"], "role": "admin"}).status_code == 403)
    check("agent can't change plan", api(G, "POST", "/billing/plan", tenant=ws, json={"plan_id": "STARTER"}).status_code == 403)
    check("agent can read inbox", api(G, "GET", "/inbox", tenant=ws).status_code == 200)
    check("tenant isolation: agent blocked from demo", api(G, "GET", "/truth/videos", tenant="9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d").status_code == 403)

    # Roles
    members = api(A, "GET", "/team", tenant=ws).json()["members"]
    agent_id = next(m["userId"] for m in members if m["email"] == agent_email)
    admin_id = next(m["userId"] for m in members if m["email"] == admin_email)
    check("last admin can't demote self", api(A, "PATCH", f"/team/members/{admin_id}", tenant=ws, json={"role": "agent"}).status_code == 400)
    check("make agent an analyst", api(A, "PATCH", f"/team/members/{agent_id}", tenant=ws, json={"role": "analyst"}).status_code == 200)
    check("analyst is read-only", api(G, "POST", "/truth/knowledge", tenant=ws, json={"title": "Fact", "statement": "A statement long enough."}).status_code == 403)
    api(A, "PATCH", f"/team/members/{agent_id}", tenant=ws, json={"role": "agent"})
    check("agent can add knowledge", api(G, "POST", "/truth/knowledge", tenant=ws, json={"title": "Battery life", "statement": "SoundMax Pro battery lasts 40 hours with ANC off."}).status_code == 201)

    # Regional pricing on the public API
    pr = httpx.get(f"{API}/public/plans", params={"currency": "INR"}).json()
    check("public INR price list", pr["currency"] == "INR" and pr["plans"][0]["monthlyPrice"] == 7999, pr["plans"][0])
    check("unknown currency falls back to USD", httpx.get(f"{API}/public/plans", params={"currency": "GBP"}).json()["currency"] == "USD")

    # Billing: switch from trial to Starter (India -> INR + GST 18%)
    r = api(A, "POST", "/billing/plan", tenant=ws, json={"plan_id": "STARTER", "interval": "MONTH"})
    check("switch to Starter", r.status_code == 200 and r.json()["status"] == "ACTIVE", r.text[:200])
    inv = api(A, "GET", "/billing/invoices", tenant=ws).json()["invoices"]
    check("INR invoice issued with GST", len(inv) == 1 and inv[0]["currency"] == "INR" and inv[0]["subtotal"] == 7999
          and inv[0]["tax"] == 1439.82 and inv[0]["total"] == 9438.82, inv)
    d = api(A, "GET", f"/billing/invoices/{inv[0]['id']}", tenant=ws).json()
    check("invoice detail has lines + GST", d["lines"][0]["amount"] == 7999 and d["taxLabel"] == "GST 18%", d)
    r = api(A, "POST", "/billing/plan", tenant=ws, json={"plan_id": "PROFESSIONAL", "interval": "YEAR"})
    inv = api(A, "GET", "/billing/invoices", tenant=ws).json()["invoices"]
    d = api(A, "GET", f"/billing/invoices/{inv[0]['id']}", tenant=ws).json()
    check("upgrade prorates old plan (same currency)", d["currency"] == "INR" and any(l["amount"] < 0 for l in d["lines"])
          and d["subtotal"] < 399990, d["lines"])

    # A US workspace bills in USD with no GST
    r = api(A, "POST", "/workspaces", json={"name": f"Acme US {RUN}", "country": "US"})
    us = r.json()["id"]
    check("US workspace trial in USD", api(A, "GET", "/billing", tenant=us).json()["plan"]["currency"] == "USD")
    api(A, "POST", "/billing/plan", tenant=us, json={"plan_id": "STARTER", "interval": "MONTH"})
    inv = api(A, "GET", "/billing/invoices", tenant=us).json()["invoices"]
    check("USD invoice, no GST", inv[0]["currency"] == "USD" and inv[0]["subtotal"] == 99 and inv[0]["tax"] == 0, inv)
    api(A, "POST", "/workspace/delete", tenant=us, json={"confirm_name": f"Acme US {RUN}"})

    # Notifications
    n = api(A, "GET", "/notifications", tenant=ws).json()
    kinds = [x["kind"] for x in n["items"]]
    check("admin notified (welcome + joined)", "welcome" in kinds and "team" in kinds and n["unread"] >= 2, kinds)
    api(A, "POST", "/notifications/read", tenant=ws, json={})
    check("mark all read", api(A, "GET", "/notifications", tenant=ws).json()["unread"] == 0)

    # Demo workspace join (dev feature)
    check("join demo workspace", api(G, "POST", "/workspaces/demo/join").status_code == 200)
    check("workspace switcher lists 2", len(api(G, "GET", "/me").json()["workspaces"]) == 2)
    check("leave demo workspace", api(G, "POST", "/workspace/leave", tenant="9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d").status_code == 204)

    # Delete needs the exact name
    check("delete needs name", api(A, "POST", "/workspace/delete", tenant=ws, json={"confirm_name": "nope"}).status_code == 400)
    check("delete workspace", api(A, "POST", "/workspace/delete", tenant=ws, json={"confirm_name": f"Acme Audio {RUN}"}).status_code == 204)
    check("deleted workspace inaccessible", api(A, "GET", "/workspace", tenant=ws).status_code == 403)
    print("WORKSPACE", ws)
finally:
    h = {"Authorization": f"Bearer {admin_token()}"}
    for uid in created_users:
        httpx.delete(f"{KC}/admin/realms/yudhix/users/{uid}", headers=h)
    print(f"cleaned up {len(created_users)} Keycloak test users")
    print("FAILURES:", failures or "none")
    sys.exit(1 if failures else 0)
