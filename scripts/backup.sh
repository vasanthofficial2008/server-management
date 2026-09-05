#!/usr/bin/env bash
# ServerPilot Backup Script
set -eo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/serverpilot}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="serverpilot_backup_${TIMESTAMP}.tar.gz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

DATA_DIR="${DATA_DIR:-/var/lib/serverpilot/data}"
CONFIG_FILE="${CONFIG_FILE:-/etc/serverpilot/.env}"
DEPLOYMENTS_DIR="${DEPLOYMENTS_DIR:-/var/lib/serverpilot/deployments}"

echo "=================================================="
echo "  ServerPilot Control Panel - Production Backup"
echo "=================================================="

mkdir -p "${BACKUP_DIR}"
chmod 700 "${BACKUP_DIR}"

TEMP_STAGE=$(mktemp -d)
trap 'rm -rf "${TEMP_STAGE}"' EXIT

echo "[INFO] Staging files for backup..."

if [ -d "${DATA_DIR}" ]; then
    mkdir -p "${TEMP_STAGE}/data"
    cp -r "${DATA_DIR}"/* "${TEMP_STAGE}/data/" 2>/dev/null || true
fi

if [ -f "${CONFIG_FILE}" ]; then
    mkdir -p "${TEMP_STAGE}/etc"
    cp "${CONFIG_FILE}" "${TEMP_STAGE}/etc/.env"
fi

if [ -d "${DEPLOYMENTS_DIR}" ]; then
    mkdir -p "${TEMP_STAGE}/deployments"
    cp -r "${DEPLOYMENTS_DIR}"/* "${TEMP_STAGE}/deployments/" 2>/dev/null || true
fi

echo "[INFO] Creating compressed archive at ${BACKUP_PATH}..."
tar -czf "${BACKUP_PATH}" -C "${TEMP_STAGE}" .

chmod 600 "${BACKUP_PATH}"

echo "[SUCCESS] Backup completed successfully!"
echo "Archive: ${BACKUP_PATH}"
echo "Size:    $(du -h "${BACKUP_PATH}" | cut -f1)"
