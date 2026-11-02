#!/usr/bin/env bash
# Shared helpers for the deploy scripts.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TAG="${TAG:-local}"
PLATFORM="${PLATFORM:-}"            # e.g. linux/amd64 for Zoho Catalyst
BASE_IMAGES=(python:3.12-slim node:22-alpine nginxinc/nginx-unprivileged:1.27-alpine quay.io/keycloak/keycloak:25.0.6)

log() { printf '\033[38;5;208m[yudhix]\033[0m %s\n' "$*"; }

# Pull base images first with a time limit: BuildKit can hang on registry metadata otherwise.
prepull() {
  for img in "${BASE_IMAGES[@]}"; do
    if docker image inspect "$img" >/dev/null 2>&1 && [ -z "$PLATFORM" ]; then continue; fi
    log "pulling $img"
    perl -e 'alarm shift; exec @ARGV' 300 docker pull ${PLATFORM:+--platform "$PLATFORM"} -q "$img" >/dev/null \
      || { echo "Could not pull $img (network?). Retry, or pull it manually."; exit 1; }
  done
}

# Build the four Yudhix images: yudhix/{api,web,gateway,keycloak}:$TAG
build_images() {
  prepull
  local plat=(); [ -n "$PLATFORM" ] && plat=(--platform "$PLATFORM")
  log "building yudhix/api:$TAG";      docker build ${plat[@]+"${plat[@]}"} -q -f "$ROOT/services/yudhix-sense/Dockerfile" -t "yudhix/api:$TAG" "$ROOT" >/dev/null
  log "building yudhix/web:$TAG";      docker build ${plat[@]+"${plat[@]}"} -q -t "yudhix/web:$TAG" "$ROOT/frontend/yudhix-web" >/dev/null
  log "building yudhix/gateway:$TAG";  docker build ${plat[@]+"${plat[@]}"} -q -t "yudhix/gateway:$TAG" "$ROOT/deploy/gateway" >/dev/null
  log "building yudhix/keycloak:$TAG"; docker build ${plat[@]+"${plat[@]}"} -q -f "$ROOT/deploy/keycloak/Dockerfile" -t "yudhix/keycloak:$TAG" "$ROOT" >/dev/null
  docker images --format '  {{.Repository}}:{{.Tag}}  {{.Size}}' | grep "yudhix/.*:$TAG" || true
}

wait_http() {  # wait_http URL SECONDS
  local url="$1" deadline=$(( $(date +%s) + ${2:-180} ))
  until curl -fs -o /dev/null "$url"; do
    [ "$(date +%s)" -gt "$deadline" ] && { echo "Timed out waiting for $url"; return 1; }
    sleep 3
  done
}
