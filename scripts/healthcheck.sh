#!/usr/bin/env bash
# ServerPilot Health Check Script
set -eo pipefail

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
HEALTH_URL="http://${HOST}:${PORT}/api/health"

echo "[INFO] Checking ServerPilot Control Panel health at ${HEALTH_URL}..."

if ! command -v curl &>/dev/null; then
    echo "[ERROR] curl is required for health check." >&2
    exit 1
fi

RESPONSE=$(curl -s -w "\n%{http_code}" --connect-timeout 5 "${HEALTH_URL}" 2>/dev/null || echo "000")
HTTP_BODY=$(echo "$RESPONSE" | head -n -1)
HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)

if [ "${HTTP_CODE}" -eq 200 ]; then
    echo "[SUCCESS] Health check passed (HTTP 200)."
    echo "Response: ${HTTP_BODY}"
    exit 0
else
    echo "[ERROR] Health check failed with HTTP status code ${HTTP_CODE}." >&2
    echo "Response: ${HTTP_BODY}" >&2
    exit 1
fi
