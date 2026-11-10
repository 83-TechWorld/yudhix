#!/usr/bin/env bash
# Tag and push the four images to a registry (for any real cluster, or Zoho Catalyst's console).
#   REGISTRY=ghcr.io/83-techworld TAG=v1.0.0 PLATFORM=linux/amd64 ./deploy/scripts/push-images.sh
# Log in first, e.g.:  echo $GITHUB_TOKEN | docker login ghcr.io -u <github-user> --password-stdin
source "$(dirname "$0")/lib.sh"
: "${REGISTRY:?Set REGISTRY, e.g. ghcr.io/83-techworld}"
if [ "${BUILD:-1}" = "1" ] && ! docker image inspect "yudhix/api:$TAG" >/dev/null 2>&1; then build_images; fi
for name in api web gateway keycloak; do
  target="$REGISTRY/yudhix-$name:$TAG"
  log "pushing $target"
  docker tag "yudhix/$name:$TAG" "$target"
  docker push -q "$target"
done
