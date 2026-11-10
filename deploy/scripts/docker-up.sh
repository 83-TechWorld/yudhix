#!/usr/bin/env bash
# Build and run the whole Yudhix stack in Docker, behind the gateway on http://localhost:8080
source "$(dirname "$0")/lib.sh"
COMPOSE=(docker compose -f "$ROOT/deploy/docker/compose.yaml")
build_images
log "starting containers"
"${COMPOSE[@]}" up -d
log "waiting for the gateway, API and Keycloak"
wait_http "http://localhost:${GATEWAY_PORT:-8080}/gateway/healthz" 120
wait_http "http://localhost:${GATEWAY_PORT:-8080}/health" 180
wait_http "http://localhost:${GATEWAY_PORT:-8080}/auth/realms/yudhix" 300
"${COMPOSE[@]}" ps --format 'table {{.Service}}\t{{.Status}}'
log "ready: http://localhost:${GATEWAY_PORT:-8080}   (emails: http://localhost:8026, Keycloak admin: /auth/admin)"
