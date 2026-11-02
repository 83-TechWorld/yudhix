#!/usr/bin/env python3
"""Apply Yudhix's SaaS login settings to a running Keycloak (idempotent).

Keycloak only imports realm-yudhix.json when the realm doesn't exist yet, so changes
to an existing install go through the Admin REST API. Safe to re-run.

    python3 keycloak/configure_realm.py
    KC_URL=https://auth.example.com KC_ADMIN_PASSWORD=... APP_ORIGINS=https://app.example.com python3 keycloak/configure_realm.py

What it sets:
  realm  : self-service sign-up, email as username, email verification, password reset,
           remember me, brute-force protection, password policy, SMTP, Yudhix login theme
  client : yudhix-web is a public client using Authorization Code + PKCE (S256) only;
           the password grant and implicit flow are disabled
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

KC_URL = os.getenv("KC_URL", "http://localhost:8180").rstrip("/")
REALM = os.getenv("KC_REALM", "yudhix")
ADMIN_USER = os.getenv("KC_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("KC_ADMIN_PASSWORD", "admin_yudhix_2026")
APP_ORIGINS = [o.strip() for o in os.getenv(
    "APP_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200,capacitor://localhost,http://localhost").split(",") if o.strip()]
# SMTP as seen from inside the Keycloak container (Mailpit in docker-compose).
SMTP_HOST = os.getenv("KC_SMTP_HOST", "mailpit")
SMTP_PORT = os.getenv("KC_SMTP_PORT", "1025")
SMTP_FROM = os.getenv("KC_SMTP_FROM", "no-reply@yudhix.local")
SMTP_USER = os.getenv("KC_SMTP_USER", "")          # e.g. Zoho ZeptoMail: "emailapikey"
SMTP_PASSWORD = os.getenv("KC_SMTP_PASSWORD", "")
SMTP_STARTTLS = os.getenv("KC_SMTP_STARTTLS", "false").lower() == "true"
SMTP_SSL = os.getenv("KC_SMTP_SSL", "false").lower() == "true"
WAIT_SECONDS = int(os.getenv("KC_WAIT_SECONDS", "0"))  # jobs: wait for Keycloak to come up
VERIFY_EMAIL = os.getenv("KC_VERIFY_EMAIL", "true").lower() == "true"


def call(method, path, token=None, body=None, form=None):
    data, headers = None, {}
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{KC_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            raw = res.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} failed: {e.code} {e.read().decode()[:300]}")


def wait_for_keycloak():
    import time
    deadline = time.time() + WAIT_SECONDS
    while True:
        try:
            with urllib.request.urlopen(f"{KC_URL}/realms/master", timeout=5):
                return
        except Exception as e:
            if time.time() > deadline:
                sys.exit(f"Keycloak not reachable at {KC_URL}: {e}")
            print("waiting for Keycloak…", flush=True)
            time.sleep(5)


def main():
    wait_for_keycloak()
    token = call("POST", "/realms/master/protocol/openid-connect/token", form={
        "client_id": "admin-cli", "username": ADMIN_USER, "password": ADMIN_PASSWORD, "grant_type": "password",
    })["access_token"]

    realm = call("GET", f"/admin/realms/{REALM}", token)
    realm.update({
        "displayName": "Yudhix",
        "registrationAllowed": True,
        "registrationEmailAsUsername": True,
        "loginWithEmailAllowed": True,
        "duplicateEmailsAllowed": False,
        "verifyEmail": VERIFY_EMAIL,
        "resetPasswordAllowed": True,
        "rememberMe": True,
        "bruteForceProtected": True,
        "failureFactor": 10,
        "passwordPolicy": "length(10) and notUsername and notEmail",
        "loginTheme": "yudhix",
        "accessTokenLifespan": 300,
        "ssoSessionIdleTimeout": 60 * 60 * 8,
        "smtpServer": {"host": SMTP_HOST, "port": SMTP_PORT, "from": SMTP_FROM, "fromDisplayName": "Yudhix",
                       "auth": "true" if SMTP_USER else "false", "user": SMTP_USER, "password": SMTP_PASSWORD,
                       "ssl": "true" if SMTP_SSL else "false", "starttls": "true" if SMTP_STARTTLS else "false"},
    })
    call("PUT", f"/admin/realms/{REALM}", token, realm)
    print(f"realm '{REALM}': sign-up, email verification={VERIFY_EMAIL}, brute-force protection, SMTP {SMTP_HOST}:{SMTP_PORT}, theme yudhix")

    clients = call("GET", f"/admin/realms/{REALM}/clients?clientId=yudhix-web", token)
    if not clients:
        sys.exit("client yudhix-web not found; import keycloak/realm-yudhix.json first")
    client = clients[0]
    client.update({
        "publicClient": True,
        "standardFlowEnabled": True,
        "implicitFlowEnabled": False,
        "directAccessGrantsEnabled": False,
        "redirectUris": [f"{o}/*" for o in APP_ORIGINS],
        "webOrigins": APP_ORIGINS,
        "rootUrl": APP_ORIGINS[0],
        "baseUrl": "/",
    })
    attrs = client.setdefault("attributes", {})
    attrs["pkce.code.challenge.method"] = "S256"
    attrs["post.logout.redirect.uris"] = "##".join(f"{o}/*" for o in APP_ORIGINS)
    call("PUT", f"/admin/realms/{REALM}/clients/{client['id']}", token, client)
    print(f"client 'yudhix-web': PKCE S256, password grant off, origins {', '.join(APP_ORIGINS)}")


if __name__ == "__main__":
    main()
