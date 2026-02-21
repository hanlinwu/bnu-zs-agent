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

  echo "[rollback] cannot access docker daemon. Ensure deploy user is in docker group or has passwordless sudo for docker." >&2
  exit 1
}

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
  ${DOCKER_CMD} compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

ensure_docker_access

echo "[rollback] rolling back to ${ROLLBACK_TAG}"
IMAGE_TAG="${ROLLBACK_TAG}" compose up -d app worker nginx search-service
if ! curl -fsS --max-time 10 http://127.0.0.1/health > /dev/null; then
  echo "[rollback] health check failed after rollback" >&2
  exit 1
fi
if ! IMAGE_TAG="${ROLLBACK_TAG}" compose exec -T app sh -lc 'python - <<'"'"'PY'"'"'
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
  echo "[rollback] search-service health check failed after rollback" >&2
  exit 1
fi

echo "${ROLLBACK_TAG}" > "${CURRENT_RELEASE_FILE}"
echo "[rollback] success"
compose ps
