#!/usr/bin/env bash
# ServerPilot Production Installation Script for Ubuntu
set -eo pipefail

echo "=================================================="
echo "  ServerPilot Control Panel - Ubuntu Installer"
echo "=================================================="

if [ "$(id -u)" -ne 0 ]; then
    echo "[ERROR] This installer must be executed as root (or via sudo)." >&2
    exit 1
fi

APP_DIR="/opt/serverpilot"
CONF_DIR="/etc/serverpilot"
DATA_BASE_DIR="/var/lib/serverpilot"
DATA_DIR="${DATA_BASE_DIR}/data"
DEPLOYMENTS_DIR="${DATA_BASE_DIR}/deployments"
LOG_DIR="/var/log/serverpilot"
VENV_DIR="${APP_DIR}/venv"
SERVICE_FILE="/etc/systemd/system/serverpilot.service"

# 1. Install System Dependencies
echo "[1/9] Installing required Ubuntu packages..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv git curl ufw systemd

# 2. Create Dedicated System User
echo "[2/9] Creating dedicated system user 'serverpilot'..."
if ! id -u serverpilot &>/dev/null; then
    useradd -r -m -d "${DATA_BASE_DIR}" -s /bin/bash serverpilot
    echo "[SUCCESS] User 'serverpilot' created."
else
    echo "[INFO] User 'serverpilot' already exists."
fi

# 3. Create Application Directories
echo "[3/9] Creating application directories..."
mkdir -p "${APP_DIR}"
mkdir -p "${CONF_DIR}"
mkdir -p "${DATA_DIR}"
mkdir -p "${DEPLOYMENTS_DIR}"
mkdir -p "${LOG_DIR}"

# 4. Copy Codebase to Application Directory
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ "${SOURCE_DIR}" != "${APP_DIR}" ]; then
    echo "[INFO] Copying application codebase to ${APP_DIR}..."
    cp -r "${SOURCE_DIR}"/* "${APP_DIR}/"
fi

# 5. Create Python Virtual Environment & Install Dependencies
echo "[4/9] Setting up Python virtual environment..."
python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/pip" install --upgrade pip -q
"${VENV_DIR}/bin/pip" install -r "${APP_DIR}/backend/requirements.txt" -q

# 6. Configure Environment Secrets
echo "[5/9] Configuring environment settings at ${CONF_DIR}/.env..."
if [ ! -f "${CONF_DIR}/.env" ]; then
    SECRET_KEY=$("${VENV_DIR}/bin/python" -c "import secrets; print(secrets.token_hex(32))")
    cat <<EOF > "${CONF_DIR}/.env"
APP_NAME=ServerPilot Control Panel
APP_VERSION=1.0.0
ENV=production
DEBUG=false
SECRET_KEY=${SECRET_KEY}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=sqlite:////var/lib/serverpilot/data/serverpilot.db
HOST=0.0.0.0
PORT=8000
DATA_DIR=/var/lib/serverpilot/data
LOGS_DIR=/var/log/serverpilot
DEPLOYMENTS_DIR=/var/lib/serverpilot/deployments
EOF
    echo "[SUCCESS] Environment secrets configuration created."
else
    echo "[INFO] Existing ${CONF_DIR}/.env found. Preserving secrets."
fi

# 7. Apply Secure File & Directory Permissions
echo "[6/9] Applying secure file permissions..."
chown -R serverpilot:serverpilot "${APP_DIR}"
chown -R serverpilot:serverpilot "${DATA_BASE_DIR}"
chown -R serverpilot:serverpilot "${LOG_DIR}"

chown -R root:serverpilot "${CONF_DIR}"
chmod 750 "${CONF_DIR}"
chmod 640 "${CONF_DIR}/.env"

chmod 755 "${APP_DIR}"
chmod -R 750 "${DATA_BASE_DIR}"
chmod -R 750 "${LOG_DIR}"

# Initialize Database and Default Admin
echo "[7/9] Initializing SQLite database schema..."
PYTHONPATH="${APP_DIR}" "${VENV_DIR}/bin/python" "${APP_DIR}/scripts/init_db.py"

if [ -n "${ADMIN_USERNAME}" ] && [ -n "${ADMIN_PASSWORD}" ]; then
    echo "[INFO] Creating admin user '${ADMIN_USERNAME}'..."
    PYTHONPATH="${APP_DIR}" "${VENV_DIR}/bin/python" "${APP_DIR}/scripts/create_admin.py" \
        --username "${ADMIN_USERNAME}" \
        --email "${ADMIN_EMAIL:-admin@serverpilot.local}" \
        --password "${ADMIN_PASSWORD}"
fi

# 8. Create and Configure Systemd Service
echo "[8/9] Installing systemd unit file..."
cp "${APP_DIR}/scripts/serverpilot.service" "${SERVICE_FILE}"
chmod 644 "${SERVICE_FILE}"

systemctl daemon-reload
systemctl enable serverpilot.service
systemctl restart serverpilot.service

# 9. Perform Health Check Verification
echo "[9/9] Verifying installation health..."
sleep 3
chmod +x "${APP_DIR}/scripts/healthcheck.sh"

if "${APP_DIR}/scripts/healthcheck.sh"; then
    echo ""
    echo "=================================================================="
    echo "  [SUCCESS] ServerPilot Control Panel Installed Successfully!"
    echo "=================================================================="
    echo "  Web Interface URL : http://$(hostname -I | awk '{print $1}'):8000"
    echo "  Systemd Service   : systemctl status serverpilot"
    echo "  Logs Directory    : /var/log/serverpilot"
    echo "  Config File       : /etc/serverpilot/.env"
    echo "=================================================================="
else
    echo "[ERROR] Installation complete but health check failed. Check systemctl status serverpilot." >&2
    exit 1
fi
