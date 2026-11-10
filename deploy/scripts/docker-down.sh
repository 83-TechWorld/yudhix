#!/usr/bin/env bash
# Stop the Docker stack. Add --wipe to also delete its database volume.
source "$(dirname "$0")/lib.sh"
if [ "${1:-}" = "--wipe" ]; then
  docker compose -f "$ROOT/deploy/docker/compose.yaml" down -v
else
  docker compose -f "$ROOT/deploy/docker/compose.yaml" down
fi
