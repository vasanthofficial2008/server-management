# ServerPilot Control Panel

A production-ready, lightweight, web-based Ubuntu Server Control Panel & Application Deployment Engine built with **FastAPI**, **SQLite**, and **Vanilla HTML5/CSS3/JavaScript**.

---

## 🌟 Key Features

* **Real-Time System Metrics**: Live CPU, RAM, Disk, Uptime, and load average telemetry over WebSockets (`/ws/stats`).
* **10 Initial Views**:
  1. **Login**: Authentication page with JWT session support (`login.html`).
  2. **Dashboard**: Live gauge metrics, project counts, running services, recent deployments, and system activity feed.
  3. **Projects**: Deploy & manage web apps, git repositories, ports, and environment variables.
  4. **Services**: Monitor and toggle system services and background daemons (start, stop, restart).
  5. **Deployments**: Execution history pipeline with full build output log inspection modal.
  6. **Terminal**: Interactive web console with WebSocket streaming (`/ws/terminal`).
  7. **Logs**: Real-time log file stream over WebSockets (`/ws/logs`).
  8. **Domains**: Configure proxy routes, port bindings, and Let's Encrypt SSL certificates.
  9. **Server**: Hardware breakdown, multi-core statistics, and top process manager.
  10. **Settings**: Platform configuration, security controls, and site settings.
* **REST API**: Health endpoint (`GET /api/health`), CRUD for projects, services, domains, deployments, and settings.
* **Zero npm / Zero Node.js / Zero Frontend Build Step**: Clean modular Vanilla JS single-page application router served directly by FastAPI.

---

## 📁 Directory Structure

```text
serverpilot/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app setup & static route host
│   │   ├── config.py            # Environment configuration
│   │   ├── database.py          # SQLite database connection engine
│   │   ├── models/              # SQLAlchemy database ORM models
│   │   ├── schemas/             # Pydantic schemas & data validation
│   │   ├── services/            # Hardware metrics (psutil) & deploy runner
│   │   ├── api/                 # REST API endpoints (health, auth, projects, etc.)
│   │   ├── websocket/           # Real-time WebSocket handlers
│   │   └── security/            # JWT token & password hashing
│   └── requirements.txt
├── frontend/
│   ├── index.html               # Main SPA dashboard host
│   ├── login.html               # Standalone login page
│   ├── css/                     # Vanilla CSS design system & glassmorphism
│   └── js/                      # SPA router, API client, WS manager & 9 views
├── scripts/
│   ├── init_db.py               # Database schema initialization & seeder
│   └── seed_data.py
├── data/                        # SQLite storage directory (`serverpilot.db`)
├── logs/                        # Log files directory
├── deployments/                 # Application build workspace
├── tests/                       # Pytest automated test suite
├── .env.example
├── README.md
└── install.sh                   # Ubuntu installation bash script
```

---

## 🚀 Quick Start & Installation

### Option A: Automatic Ubuntu Installation (Recommended)

Run the one-touch installer script on your Ubuntu 22.04 / 24.04 LTS server:

```bash
chmod +x install.sh
./install.sh
```

### Option B: Manual Setup

1. **Create and Activate Python Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate    # On Linux/macOS
   # venv\Scripts\activate     # On Windows PowerShell
   ```

2. **Install Backend Dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. **Initialize Database & Create Default Admin User**:
   ```bash
   python3 scripts/init_db.py
   ```
   * **Default Admin Username**: `admin`
   * **Default Admin Password**: `admin123`

4. **Launch the FastAPI Server**:
   ```bash
   uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. **Access the Control Panel**:
   * **Web Dashboard**: [http://localhost:8000/](http://localhost:8000/)
   * **Login Page**: [http://localhost:8000/login.html](http://localhost:8000/login.html)
   * **Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)
   * **API Docs (Swagger UI)**: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

---

## 🧪 Running Automated Tests

Run `pytest` to execute unit tests for API endpoints, health check, authentication, projects, and services:

```bash
pytest tests/
```

---

## 🔒 Security Note

Privileged raw bash execution is safely restricted by default in non-privileged mode. All hardware stats are sourced directly from Linux `psutil`. When deploying to production on Ubuntu, customize `SECRET_KEY` in `.env`.
