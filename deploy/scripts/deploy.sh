#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/docker-compose.prod.yml"
ENV_FILE="${ROOT_DIR}/.env"
CURRENT_RELEASE_FILE="${ROOT_DIR}/.current_release"
PREVIOUS_RELEASE_FILE="${ROOT_DIR}/.previous_release"

DOCKER_CMD="docker"

ensure_docker_access() {
  if docker info >/dev/null 2>&1; then
    DOCKER_CMD="docker"
    return
  fi
  if sudo -n docker info >/dev/null 2>&1; then
    DOCKER_CMD="sudo docker"
    return
  fi

  echo "[deploy] cannot access docker daemon. Ensure deploy user is in docker group or has passwordless sudo for docker." >&2
  exit 1
}

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[deploy] ${ENV_FILE} not found. Copy deploy/.env.example to deploy/.env and fill real values." >&2
  exit 1
fi

set -a
source "${ENV_FILE}"
set +a

required_vars=(APP_IMAGE NGINX_IMAGE SEARCH_SERVICE_IMAGE IMAGE_TAG)
for name in "${required_vars[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    echo "[deploy] missing required env: ${name}" >&2
    exit 1
  fi
done

registry_from_image() {
  local image_ref="$1"
  local first_part="${image_ref%%/*}"
  if [[ "${first_part}" == *.* || "${first_part}" == *:* || "${first_part}" == "localhost" ]]; then
    echo "${first_part}"
  else
    echo "docker.io"
  fi
}

if [[ -f "${CURRENT_RELEASE_FILE}" ]]; then
  PREVIOUS_TAG="$(cat "${CURRENT_RELEASE_FILE}")"
else
  PREVIOUS_TAG=""
fi

compose() {
  ${DOCKER_CMD} compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

wait_for_service_healthy() {
  local service="$1"
  local timeout="${2:-120}"
  local waited=0

  local container_id
  container_id="$(compose ps -q "${service}")"
  if [[ -z "${container_id}" ]]; then
    echo "[deploy] service ${service} has no container id" >&2
    return 1
  fi

  while (( waited < timeout )); do
    local status
    status="$(${DOCKER_CMD} inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${container_id}")"
    if [[ "${status}" == "healthy" || "${status}" == "running" ]]; then
      return 0
    fi
    sleep 3
    waited=$(( waited + 3 ))
  done

  echo "[deploy] service ${service} not healthy within ${timeout}s" >&2
  return 1
}

rollback_to_previous() {
  if [[ -z "${PREVIOUS_TAG}" ]]; then
    echo "[deploy] no previous release found, cannot auto rollback" >&2
    return 1
  fi

  echo "[deploy] rolling back to ${PREVIOUS_TAG}"
  IMAGE_TAG="${PREVIOUS_TAG}" compose up -d app worker nginx search-service
  IMAGE_TAG="${PREVIOUS_TAG}" compose ps
}

print_runtime_diagnostics() {
  echo "[deploy] diagnostics: compose ps"
  compose ps || true
  echo "[deploy] diagnostics: nginx logs"
  compose logs --tail=120 nginx || true
  echo "[deploy] diagnostics: app logs"
  compose logs --tail=120 app || true
  echo "[deploy] diagnostics: search-service logs"
  compose logs --tail=120 search-service || true
  echo "[deploy] diagnostics: meilisearch logs"
  compose logs --tail=120 meilisearch || true
}

health_check_with_retry() {
  local url="$1"
  local timeout="${2:-90}"
  local interval="${3:-3}"
  local waited=0

  while (( waited < timeout )); do
    local http_code
    http_code="$(curl -sS --max-time 10 -o /dev/null -w '%{http_code}' "${url}" 2>/dev/null || true)"
    if [[ "${http_code}" =~ ^2[0-9][0-9]$ || "${http_code}" =~ ^3[0-9][0-9]$ ]]; then
      return 0
    fi
    sleep "${interval}"
    waited=$(( waited + interval ))
  done

  return 1
}

persist_release_metadata() {
  local release_tag="$1"

  if [[ -f "${CURRENT_RELEASE_FILE}" ]]; then
    if ! cp "${CURRENT_RELEASE_FILE}" "${PREVIOUS_RELEASE_FILE}"; then
      if sudo -n cp "${CURRENT_RELEASE_FILE}" "${PREVIOUS_RELEASE_FILE}"; then
        echo "[deploy] metadata copied with sudo: ${PREVIOUS_RELEASE_FILE}"
      else
        echo "[deploy] warning: failed to update ${PREVIOUS_RELEASE_FILE} (permission denied or read-only)" >&2
      fi
    fi
  fi

  if ! printf '%s\n' "${release_tag}" > "${CURRENT_RELEASE_FILE}"; then
    if printf '%s\n' "${release_tag}" | sudo -n tee "${CURRENT_RELEASE_FILE}" >/dev/null; then
      echo "[deploy] metadata written with sudo: ${CURRENT_RELEASE_FILE}"
    else
      echo "[deploy] warning: failed to update ${CURRENT_RELEASE_FILE} (permission denied or read-only)" >&2
    fi
  fi
}

ensure_docker_access
REGISTRY_HOST="$(registry_from_image "${APP_IMAGE}")"
REGISTRY_USERNAME="${REGISTRY_USERNAME:-${GHCR_USERNAME:-}}"
REGISTRY_PASSWORD="${REGISTRY_PASSWORD:-${GHCR_TOKEN:-}}"

if [[ -n "${REGISTRY_USERNAME}" && -n "${REGISTRY_PASSWORD}" ]]; then
  echo "[deploy] docker login ${REGISTRY_HOST}"
  echo "${REGISTRY_PASSWORD}" | ${DOCKER_CMD} login "${REGISTRY_HOST}" -u "${REGISTRY_USERNAME}" --password-stdin
else
  echo "[deploy] skip docker login (REGISTRY_USERNAME/REGISTRY_PASSWORD not provided)"
fi

echo "[deploy] pulling target images"
compose pull app worker nginx search-service

echo "[deploy] ensuring db/redis/meilisearch/search-service are running"
compose up -d db redis meilisearch search-service
wait_for_service_healthy db 180
wait_for_service_healthy redis 120
wait_for_service_healthy meilisearch 120
wait_for_service_healthy search-service 120

echo "[deploy] ensure pgvector extension"
compose exec -T db bash -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;"'

echo "[deploy] running migrations"
if ! compose run --rm app sh -lc 'cd /app && PYTHONPATH=/app alembic -c /app/alembic.ini upgrade head'; then
  echo "[deploy] migration failed" >&2
  rollback_to_previous || true
  exit 1
fi

echo "[deploy] starting app/worker/nginx/search-service"
if ! compose up -d app worker nginx search-service; then
  echo "[deploy] failed to start services" >&2
  print_runtime_diagnostics
  rollback_to_previous || true
  exit 1
fi

echo "[deploy] health check"
HEALTH_HOST="${BIND_IP:-127.0.0.1}"
if [[ "${HEALTH_HOST}" == "0.0.0.0" || "${HEALTH_HOST}" == "::" || "${HEALTH_HOST}" == "[::]" ]]; then
  HEALTH_HOST="127.0.0.1"
fi
HEALTH_PORT="${HTTP_PORT:-80}"
HEALTH_URL="http://${HEALTH_HOST}:${HEALTH_PORT}/health"

if ! health_check_with_retry "${HEALTH_URL}" 120 3; then
  echo "[deploy] health check failed" >&2
  echo "[deploy] checked url: ${HEALTH_URL}" >&2
  print_runtime_diagnostics
  rollback_to_previous || true
  exit 1
fi

persist_release_metadata "${IMAGE_TAG}"

echo "[deploy] verify search-service health"
if ! compose exec -T app sh -lc 'python - <<'"'"'PY'"'"'
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
PY'; then
  echo "[deploy] search-service health check failed from app container" >&2
  print_runtime_diagnostics
  rollback_to_previous || true
  exit 1
fi

echo "[deploy] success: ${IMAGE_TAG}"
compose ps
