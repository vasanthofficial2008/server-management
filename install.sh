#!/usr/bin/env bash
# ServerPilot Control Panel - One-Touch Ubuntu Installation & Setup Script

set -e

echo "=========================================================="
echo "         ServerPilot Control Panel Installer              "
echo "=========================================================="

# 1. Update package repos & install system dependencies
echo "[1/5] Updating Ubuntu packages and installing Python 3..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip curl git sqlite3

# 2. Setup Python virtual environment
echo "[2/5] Setting up Python virtual environment (venv)..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# 3. Upgrade pip and install backend requirements
echo "[3/5] Installing backend dependencies from backend/requirements.txt..."
pip install --upgrade pip
pip install -r backend/requirements.txt

# 4. Initialize database and seed initial data
echo "[4/5] Initializing SQLite database and default admin user..."
python3 scripts/init_db.py

# 5. Summary & startup instruction
echo "=========================================================="
echo " [SUCCESS] ServerPilot Control Panel installation complete! "
echo "=========================================================="
echo ""
echo "To start the FastAPI ServerPilot daemon:"
echo "  source venv/bin/activate"
echo "  uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "Then open your web browser at:"
echo "  http://<your-server-ip>:8000/"
echo ""
