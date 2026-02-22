#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

TCR_REGISTRY="${TCR_REGISTRY:-ccr.ccs.tencentyun.com}"
TCR_NAMESPACE="${TCR_NAMESPACE:-}"
TCR_USERNAME="${TCR_USERNAME:-}"
TCR_PASSWORD="${TCR_PASSWORD:-}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"

if [[ -z "$TCR_NAMESPACE" || -z "$TCR_USERNAME" || -z "$TCR_PASSWORD" ]]; then
	echo "[build] missing required env vars: TCR_NAMESPACE, TCR_USERNAME, TCR_PASSWORD" >&2
	echo "[build] example:" >&2
	echo "TCR_REGISTRY=ccr.ccs.tencentyun.com TCR_NAMESPACE=your-namespace TCR_USERNAME=xxx TCR_PASSWORD=xxx ./build_and_push.sh" >&2
	exit 1
fi

DOCKER_CMD="docker"
if ! docker info >/dev/null 2>&1; then
	if sudo -n docker info >/dev/null 2>&1; then
		DOCKER_CMD="sudo docker"
	else
		echo "[build] docker permission denied. Add user to docker group or use passwordless sudo docker." >&2
		exit 1
	fi
fi

APP_IMAGE="${TCR_REGISTRY}/${TCR_NAMESPACE}/bnu-admission-chatbot-app"
NGINX_IMAGE="${TCR_REGISTRY}/${TCR_NAMESPACE}/bnu-admission-chatbot-nginx"

echo "[build] login ${TCR_REGISTRY}"
echo "$TCR_PASSWORD" | $DOCKER_CMD login "$TCR_REGISTRY" -u "$TCR_USERNAME" --password-stdin

echo "[build] build app image"
$DOCKER_CMD build \
	-t "${APP_IMAGE}:${IMAGE_TAG}" \
	-t "${APP_IMAGE}:latest" \
	-f server/Dockerfile \
	server

echo "[build] build nginx image"
$DOCKER_CMD build \
	-t "${NGINX_IMAGE}:${IMAGE_TAG}" \
	-t "${NGINX_IMAGE}:latest" \
	-f nginx/Dockerfile.prod \
	.

echo "[build] push app image"
$DOCKER_CMD push "${APP_IMAGE}:${IMAGE_TAG}"
$DOCKER_CMD push "${APP_IMAGE}:latest"

echo "[build] push nginx image"
$DOCKER_CMD push "${NGINX_IMAGE}:${IMAGE_TAG}"
$DOCKER_CMD push "${NGINX_IMAGE}:latest"

echo "[build] done"
echo "[build] app:   ${APP_IMAGE}:${IMAGE_TAG}"
echo "[build] nginx: ${NGINX_IMAGE}:${IMAGE_TAG}"
