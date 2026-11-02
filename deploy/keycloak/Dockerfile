# Yudhix Keycloak: Postgres-backed, served under /auth behind the gateway, Yudhix theme + realm baked in.
# Build from the repository root:
#   docker build -f deploy/keycloak/Dockerfile -t yudhix/keycloak:local .
FROM quay.io/keycloak/keycloak:25.0.6 AS builder
ENV KC_DB=postgres \
    KC_HEALTH_ENABLED=true \
    KC_METRICS_ENABLED=true \
    KC_HTTP_RELATIVE_PATH=/auth \
    KC_CACHE=ispn
COPY keycloak/themes/yudhix /opt/keycloak/themes/yudhix
RUN /opt/keycloak/bin/kc.sh build

FROM quay.io/keycloak/keycloak:25.0.6
COPY --from=builder /opt/keycloak/ /opt/keycloak/
COPY keycloak/realm-yudhix.json /opt/keycloak/data/import/realm-yudhix.json
COPY --chmod=755 deploy/keycloak/entrypoint.sh /opt/keycloak/bin/yudhix-entrypoint.sh
ENV KC_HTTP_ENABLED=true \
    KC_PROXY_HEADERS=xforwarded \
    KC_HTTP_PORT=8080
# 8080: app traffic (through the gateway) · 9000: health & metrics (probes)
EXPOSE 8080 9000
ENTRYPOINT ["/opt/keycloak/bin/yudhix-entrypoint.sh"]
