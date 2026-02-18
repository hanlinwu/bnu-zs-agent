#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/docker-compose.prod.yml"
ENV_FILE="${ROOT_DIR}/.env"
CURRENT_RELEASE_FILE="${ROOT_DIR}/.current_release"
PREVIOUS_RELEASE_FILE="${ROOT_DIR}/.previous_release"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[rollback] ${ENV_FILE} not found" >&2
  exit 1
fi

if [[ ! -f "${PREVIOUS_RELEASE_FILE}" ]]; then
  echo "[rollback] no ${PREVIOUS_RELEASE_FILE} found" >&2
  exit 1
fi

ROLLBACK_TAG="$(cat "${PREVIOUS_RELEASE_FILE}")"
if [[ -z "${ROLLBACK_TAG}" ]]; then
  echo "[rollback] previous release tag is empty" >&2
  exit 1
fi

compose() {
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

echo "[rollback] rolling back to ${ROLLBACK_TAG}"
IMAGE_TAG="${ROLLBACK_TAG}" compose up -d app worker nginx
if ! curl -fsS --max-time 10 http://127.0.0.1/health > /dev/null; then
  echo "[rollback] health check failed after rollback" >&2
  exit 1
fi

echo "${ROLLBACK_TAG}" > "${CURRENT_RELEASE_FILE}"
echo "[rollback] success"
compose ps
