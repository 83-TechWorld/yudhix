#!/usr/bin/env bash
# Deploy the four Yudhix containers to Zoho Catalyst AppSail (custom runtime).
# Catalyst needs linux/amd64 images and runs each one as its own AppSail app.
#
#   npm install -g zcatalyst-cli && catalyst login      # once
#   cd <your Catalyst project folder>                     # created with `catalyst init`
#   /path/to/yudhix/deploy/zoho/deploy-catalyst.sh
#
# Then set each app's environment variables in the Catalyst console (see deploy/zoho/README.md).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
export PLATFORM=linux/amd64 TAG="${TAG:-catalyst}"
source "$HERE/../scripts/lib.sh"

build_images
OUT="${OUT:-$PWD/.yudhix-images}"
mkdir -p "$OUT"
for name in gateway web api keycloak; do
  log "exporting yudhix/$name:$TAG -> $OUT/yudhix-$name.tar.gz"
  docker save "yudhix/$name:$TAG" | gzip > "$OUT/yudhix-$name.tar.gz"
done

if ! command -v catalyst >/dev/null 2>&1; then
  log "Catalyst CLI not found. Install it (npm i -g zcatalyst-cli), then run:"
  for name in gateway web api keycloak; do
    echo "  catalyst deploy appsail --name yudhix-$name --source docker-archive://$OUT/yudhix-$name.tar.gz"
  done
  exit 0
fi
for name in keycloak api web gateway; do      # dependencies first
  log "deploying yudhix-$name to Catalyst AppSail"
  catalyst deploy appsail --name "yudhix-$name" --source "docker-archive://$OUT/yudhix-$name.tar.gz"
done
log "done. Next: environment variables + custom domain on yudhix-gateway (deploy/zoho/README.md)"
