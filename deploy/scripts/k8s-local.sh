#!/usr/bin/env bash
# Run Yudhix on a local Kubernetes cluster (Docker Desktop, kind, minikube…) -> http://localhost:8081
#
#   ./deploy/scripts/k8s-local.sh up       build images, deploy, wait, open the port-forward
#   ./deploy/scripts/k8s-local.sh status   pods, services, autoscalers
#   ./deploy/scripts/k8s-local.sh down     remove the app (keeps the database volume)
#   ./deploy/scripts/k8s-local.sh wipe     remove everything incl. the database
#
# Images: the cluster must be able to see yudhix/*:local. That works out of the box with Docker
# Desktop's "kubeadm" provisioning, Rancher Desktop and minikube (eval $(minikube docker-env)).
# Docker Desktop's "kind" provisioning does NOT share images: either switch it to kubeadm
# (Settings -> Kubernetes) or push to a registry the cluster can pull from:
#   REGISTRY=ghcr.io/<you> ./deploy/scripts/k8s-local.sh up
source "$(dirname "$0")/lib.sh"
NS=yudhix
OVERLAY="$ROOT/deploy/k8s/overlays/local"
PF_PID="$ROOT/.pids/k8s-port-forward.pid"
PORT="${K8S_PORT:-8081}"
mkdir -p "$ROOT/.pids" "$ROOT/.logs"

render() {
  if [ -n "${REGISTRY:-}" ]; then
    # yudhix/api:local -> $REGISTRY/yudhix-api:$TAG, always pulled
    kubectl kustomize "$OVERLAY" \
      | sed -E "s#image: yudhix/([a-z]+):local#image: ${REGISTRY}/yudhix-\1:${TAG}#; s#imagePullPolicy: IfNotPresent#imagePullPolicy: Always#"
  else
    kubectl kustomize "$OVERLAY"
  fi
}

stop_forward() { [ -f "$PF_PID" ] && kill "$(cat "$PF_PID")" 2>/dev/null || true; rm -f "$PF_PID"; }

image_problems() {
  kubectl -n "$NS" get pods -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.status.containerStatuses[*].state.waiting.reason}{"\n"}{end}' \
    | grep -E "ErrImageNeverPull|ErrImagePull|ImagePullBackOff" || true
}

case "${1:-up}" in
  up)
    [ "${SKIP_BUILD:-}" = "1" ] || build_images
    if [ -n "${REGISTRY:-}" ]; then
      TAG="${TAG}" "$(dirname "$0")/push-images.sh"
    fi
    log "deploying to $(kubectl config current-context)"
    render | kubectl apply -f - >/dev/null
    log "waiting for pods (first start pulls Postgres/Mailpit and creates the schema)"
    for i in $(seq 1 60); do
      bad="$(image_problems)"
      if [ -n "$bad" ]; then
        echo "The cluster can't see the Yudhix images:"; echo "$bad"
        echo "Fix: Docker Desktop -> Settings -> Kubernetes -> provisioning 'kubeadm', or REGISTRY=<registry> $0 up"
        exit 1
      fi
      ready=$(kubectl -n "$NS" get deploy -o jsonpath='{range .items[*]}{.status.readyReplicas}/{.spec.replicas} {end}')
      if kubectl -n "$NS" rollout status deploy/gateway deploy/web deploy/api deploy/keycloak --timeout=5s >/dev/null 2>&1; then break; fi
      printf '  %s\n' "$ready"; sleep 5
    done
    kubectl -n "$NS" rollout status deploy/keycloak --timeout=300s >/dev/null
    stop_forward
    kubectl -n "$NS" port-forward svc/gateway "$PORT":8080 >"$ROOT/.logs/k8s-port-forward.log" 2>&1 &
    echo $! > "$PF_PID"
    wait_http "http://localhost:$PORT/gateway/healthz" 60
    kubectl -n "$NS" get pods -o wide | awk '{print $1, $2, $3, $5}' | column -t
    log "ready: http://localhost:$PORT   (emails: kubectl -n $NS port-forward svc/mailpit 8027:8025)"
    ;;
  status)
    kubectl -n "$NS" get pods,svc,hpa,pdb
    ;;
  down)
    stop_forward
    render | kubectl delete --ignore-not-found -f - 2>/dev/null | grep -v persistentvolumeclaim || true
    log "removed (database volume kept; '$0 wipe' deletes it)"
    ;;
  wipe)
    stop_forward
    kubectl delete namespace "$NS" --ignore-not-found
    ;;
  *) echo "usage: $0 {up|status|down|wipe}"; exit 1 ;;
esac
