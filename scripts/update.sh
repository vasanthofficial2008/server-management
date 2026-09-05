#!/usr/bin/env bash
# ServerPilot Production Update Script
set -eo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "[ERROR] This update script must be executed as root (or with sudo)." >&2
    exit 1
fi

APP_DIR="/opt/serverpilot"
VENV_DIR="${APP_DIR}/venv"
SERVICE_NAME="serverpilot.service"

echo "=================================================="
echo "  ServerPilot Control Panel - Update Manager"
echo "=================================================="

echo "[INFO] Stopping ${SERVICE_NAME}..."
systemctl stop "${SERVICE_NAME}" || true

if [ -d "${APP_DIR}/.git" ]; then
    echo "[INFO] Pulling latest git repository updates..."
    git -C "${APP_DIR}" pull origin main || true
fi

echo "[INFO] Updating Python dependencies..."
"${VENV_DIR}/bin/pip" install -r "${APP_DIR}/backend/requirements.txt"

echo "[INFO] Running database migrations and schema initialization..."
"${VENV_DIR}/bin/python" "${APP_DIR}/scripts/init_db.py"

echo "[INFO] Ensuring correct file permissions..."
chown -R serverpilot:serverpilot "${APP_DIR}" /var/lib/serverpilot /var/log/serverpilot
chmod 755 "${APP_DIR}"
chmod 750 /var/lib/serverpilot /var/log/serverpilot

echo "[INFO] Reloading systemd daemon and starting ${SERVICE_NAME}..."
systemctl daemon-reload
systemctl start "${SERVICE_NAME}"

echo "[INFO] Verifying service health..."
sleep 3
if "${APP_DIR}/scripts/healthcheck.sh"; then
    echo "=================================================="
    echo "[SUCCESS] ServerPilot updated and verified healthy!"
    echo "=================================================="
else
    echo "[ERROR] Health check failed after update!" >&2
    exit 1
fi
