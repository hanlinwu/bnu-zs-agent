#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/docker-compose.prod.yml"
ENV_FILE="${ROOT_DIR}/.env"
CURRENT_RELEASE_FILE="${ROOT_DIR}/.current_release"
PREVIOUS_RELEASE_FILE="${ROOT_DIR}/.previous_release"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[deploy] ${ENV_FILE} not found. Copy deploy/.env.example to deploy/.env and fill real values." >&2
  exit 1
fi

set -a
source "${ENV_FILE}"
set +a

required_vars=(GHCR_USERNAME GHCR_TOKEN APP_IMAGE NGINX_IMAGE IMAGE_TAG)
for name in "${required_vars[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    echo "[deploy] missing required env: ${name}" >&2
    exit 1
  fi
done

if [[ -f "${CURRENT_RELEASE_FILE}" ]]; then
  PREVIOUS_TAG="$(cat "${CURRENT_RELEASE_FILE}")"
else
  PREVIOUS_TAG=""
fi

compose() {
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
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
    status="$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${container_id}")"
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
  IMAGE_TAG="${PREVIOUS_TAG}" compose up -d app worker nginx
  IMAGE_TAG="${PREVIOUS_TAG}" compose ps
}

echo "[deploy] docker login ghcr.io"
echo "${GHCR_TOKEN}" | docker login ghcr.io -u "${GHCR_USERNAME}" --password-stdin

echo "[deploy] pulling target images"
compose pull app worker nginx

echo "[deploy] ensuring db/redis are running"
compose up -d db redis
wait_for_service_healthy db 180
wait_for_service_healthy redis 120

echo "[deploy] ensure pgvector extension"
compose exec -T db bash -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;"'

echo "[deploy] bootstrap base schema via app startup"
compose up -d app
wait_for_service_healthy app 180

echo "[deploy] running migrations"
if ! compose exec -T app sh -lc 'cd /app && PYTHONPATH=/app alembic -c /app/alembic.ini upgrade head'; then
  echo "[deploy] migration failed" >&2
  rollback_to_previous || true
  exit 1
fi

echo "[deploy] starting app/worker/nginx"
if ! compose up -d app worker nginx; then
  echo "[deploy] failed to start services" >&2
  rollback_to_previous || true
  exit 1
fi

echo "[deploy] health check"
if ! curl -fsS --max-time 10 http://127.0.0.1/health > /dev/null; then
  echo "[deploy] health check failed" >&2
  rollback_to_previous || true
  exit 1
fi

if [[ -f "${CURRENT_RELEASE_FILE}" ]]; then
  cp "${CURRENT_RELEASE_FILE}" "${PREVIOUS_RELEASE_FILE}"
fi
echo "${IMAGE_TAG}" > "${CURRENT_RELEASE_FILE}"

echo "[deploy] success: ${IMAGE_TAG}"
compose ps
