#!/bin/bash
# Starts Keycloak in production mode with the build-time optimizations.
# Required at runtime: KC_DB_URL, KC_DB_USERNAME, KC_DB_PASSWORD, KC_HOSTNAME (public URL incl. /auth,
# e.g. https://app.example.com/auth), KEYCLOAK_ADMIN, KEYCLOAK_ADMIN_PASSWORD.
set -e
# Zoho Catalyst assigns the listening port.
if [ -n "${X_ZOHO_CATALYST_LISTEN_PORT}" ]; then
  export KC_HTTP_PORT="${X_ZOHO_CATALYST_LISTEN_PORT}"
fi
# Fit the JVM to the container's memory limit (Catalyst max 2 GB, Kubernetes limits).
export JAVA_OPTS_KC_HEAP="${JAVA_OPTS_KC_HEAP:--XX:MaxRAMPercentage=70 -XX:InitialRAMPercentage=40}"
# Imports realm-yudhix.json only if the realm doesn't exist yet (safe on restarts).
exec /opt/keycloak/bin/kc.sh start --optimized --import-realm "$@"
