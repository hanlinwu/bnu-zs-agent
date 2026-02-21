#!/usr/bin/env bash
set -euo pipefail

# One-click host smoke test for production deployment flow.
# It builds local images, starts the stack with docker-compose.prod.yml,
# runs Alembic migrations, performs health check, and prints key logs.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEPLOY_DIR="${ROOT_DIR}/deploy"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.prod.yml"
ENV_TEMPLATE="${DEPLOY_DIR}/.env.example"
ENV_FILE="${DEPLOY_DIR}/.env.local.hosttest"

PROJECT_NAME="bnu-hosttest"
HTTP_PORT="18080"
KEEP_STACK="false"
IMAGE_TAG="hosttest"
APP_IMAGE="local/bnu-admission-chatbot-app"
NGINX_IMAGE="local/bnu-admission-chatbot-nginx"
SEARCH_SERVICE_IMAGE="local/bnu-search-service"

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Options:
  --port <port>       Host port for nginx (default: 18080)
  --project <name>    Docker Compose project name (default: bnu-hosttest)
  --keep              Keep containers/volumes after success (default: cleanup)
  --tag <tag>         Local image tag (default: hosttest)
  -h, --help          Show this help

Examples:
  ./deploy/scripts/host-prod-smoke.sh
  ./deploy/scripts/host-prod-smoke.sh --port 18081 --keep
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      HTTP_PORT="$2"
      shift 2
      ;;
    --project)
      PROJECT_NAME="$2"
      shift 2
      ;;
    --keep)
      KEEP_STACK="true"
      shift
      ;;
    --tag)
      IMAGE_TAG="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[host-smoke] unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if ! command -v docker >/dev/null 2>&1; then
  echo "[host-smoke] docker command not found. Run this on host with Docker installed." >&2
  exit 1
fi

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "[host-smoke] missing compose file: ${COMPOSE_FILE}" >&2
  exit 1
fi

if [[ ! -f "${ENV_TEMPLATE}" ]]; then
  echo "[host-smoke] missing env template: ${ENV_TEMPLATE}" >&2
  exit 1
fi

compose() {
  docker compose -p "${PROJECT_NAME}" --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

wait_for_service_healthy() {
  local service="$1"
  local timeout="${2:-180}"
  local waited=0

  local container_id
  container_id="$(compose ps -q "${service}")"
  if [[ -z "${container_id}" ]]; then
    echo "[host-smoke] service ${service} has no container id" >&2
    return 1
  fi

  while (( waited < timeout )); do
    local status
    status="$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${container_id}")"
    if [[ "${status}" == "healthy" || "${status}" == "running" ]]; then
      return 0
    fi
    sleep 3
    waited=$(( waited + 3 ))
  done

  echo "[host-smoke] service ${service} not healthy within ${timeout}s" >&2
  return 1
}

cleanup() {
  if [[ "${KEEP_STACK}" == "true" ]]; then
    echo "[host-smoke] keeping stack and volumes (project: ${PROJECT_NAME})"
    return 0
  fi

  echo "[host-smoke] cleaning up stack and volumes"
  compose down -v --remove-orphans || true
  rm -f "${ENV_FILE}"
}

on_error() {
  local exit_code="$?"
  echo "[host-smoke] failed with exit code ${exit_code}" >&2
  echo "[host-smoke] dumping recent logs..."
  compose logs --tail=120 app worker nginx db redis || true
  cleanup
  exit "${exit_code}"
}

trap on_error ERR

cd "${ROOT_DIR}"

echo "[host-smoke] build app image: ${APP_IMAGE}:${IMAGE_TAG}"
docker build -t "${APP_IMAGE}:${IMAGE_TAG}" ./server

echo "[host-smoke] build nginx image: ${NGINX_IMAGE}:${IMAGE_TAG}"
docker build -t "${NGINX_IMAGE}:${IMAGE_TAG}" -f ./nginx/Dockerfile.prod .

echo "[host-smoke] build search-service image: ${SEARCH_SERVICE_IMAGE}:${IMAGE_TAG}"
docker build -t "${SEARCH_SERVICE_IMAGE}:${IMAGE_TAG}" -f ./search-service/Dockerfile ./search-service

echo "[host-smoke] prepare env file: ${ENV_FILE}"
cp "${ENV_TEMPLATE}" "${ENV_FILE}"

sed -i "s#^APP_IMAGE=.*#APP_IMAGE=${APP_IMAGE}#" "${ENV_FILE}"
sed -i "s#^NGINX_IMAGE=.*#NGINX_IMAGE=${NGINX_IMAGE}#" "${ENV_FILE}"
sed -i "s#^SEARCH_SERVICE_IMAGE=.*#SEARCH_SERVICE_IMAGE=${SEARCH_SERVICE_IMAGE}#" "${ENV_FILE}"
sed -i "s#^IMAGE_TAG=.*#IMAGE_TAG=${IMAGE_TAG}#" "${ENV_FILE}"
sed -i "s#^BIND_IP=.*#BIND_IP=127.0.0.1#" "${ENV_FILE}"
sed -i "s#^HTTP_PORT=.*#HTTP_PORT=${HTTP_PORT}#" "${ENV_FILE}"

echo "[host-smoke] reset old stack for project ${PROJECT_NAME}"
compose down -v --remove-orphans || true

echo "[host-smoke] start db and redis"
compose up -d db redis
wait_for_service_healthy db 180
wait_for_service_healthy redis 120

echo "[host-smoke] ensure pgvector extension"
compose exec -T db bash -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;"'

echo "[host-smoke] run migrations"
compose run --rm app sh -lc 'cd /app && PYTHONPATH=/app alembic -c /app/alembic.ini upgrade head'

echo "[host-smoke] start app, worker, nginx, meilisearch, search-service"
compose up -d app worker nginx meilisearch search-service
wait_for_service_healthy app 180
wait_for_service_healthy meilisearch 120
wait_for_service_healthy search-service 120

echo "[host-smoke] health check"
curl -fsS --max-time 10 "http://127.0.0.1:${HTTP_PORT}/health" >/dev/null
compose exec -T app sh -lc 'python - <<'"'"'PY'"'"'
import os
import sys
import urllib.request

url = (os.getenv("SEARCH_SERVICE_URL") or "http://search-service:8002").rstrip("/") + "/health"
try:
    with urllib.request.urlopen(url, timeout=10) as resp:
        if 200 <= resp.status < 400:
            sys.exit(0)
except Exception:
    pass
sys.exit(1)
PY'

echo "[host-smoke] smoke test passed"
compose ps
compose logs --tail=80 app worker nginx search-service meilisearch

cleanup
