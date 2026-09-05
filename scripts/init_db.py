import sys
import os
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.database import engine, Base, SessionLocal
from backend.app.models import User, Project, ServiceModel, Deployment, Domain, SystemEvent, Setting
from backend.app.security.auth import get_password_hash
from backend.app.schemas.project import sanitize_and_validate_path, get_default_commands

def init_db(reset: bool = True):
    print("Recreating database schema...")
    try:
        Base.metadata.drop_all(bind=engine)
    except Exception as err:
        print(f"Notice on drop_all: {err}")

    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Create initial admin user from env or default seed if not exists
        admin_user = os.getenv("ADMIN_USERNAME", "admin")
        admin_email = os.getenv("ADMIN_EMAIL", "admin@serverpilot.local")
        admin_pass = os.getenv("ADMIN_PASSWORD")

        admin = db.query(User).filter(User.username == admin_user).first()
        if not admin:
            admin = User(
                username=admin_user,
                email=admin_email,
                hashed_password=get_password_hash(admin_pass or "admin123"),
                full_name="ServerPilot Admin",
                is_active=True,
                is_superuser=True
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"Default admin created: username '{admin_user}'")
        elif admin_pass:
            admin.hashed_password = get_password_hash(admin_pass)
            db.commit()
            print(f"Updated password for admin user '{admin_user}'")

        # Create sample services
        services_data = [
            {"name": "nginx", "display_name": "Nginx Web Gateway", "systemd_name": "nginx.service", "type": "web", "status": "running", "port": 80, "memory_mb": 42.5, "cpu_percent": 0.8},
            {"name": "postgresql", "display_name": "PostgreSQL Database Engine", "systemd_name": "postgresql.service", "type": "database", "status": "running", "port": 5432, "memory_mb": 158.2, "cpu_percent": 1.4},
            {"name": "redis", "display_name": "Redis Memory Store", "systemd_name": "redis-server.service", "type": "cache", "status": "running", "port": 6379, "memory_mb": 34.1, "cpu_percent": 0.2},
            {"name": "docker", "display_name": "Docker Container Daemon", "systemd_name": "docker.service", "type": "daemon", "status": "running", "port": None, "memory_mb": 210.8, "cpu_percent": 2.1},
            {"name": "serverpilot-api", "display_name": "ServerPilot Control API", "systemd_name": "serverpilot.service", "type": "web", "status": "running", "port": 8000, "memory_mb": 85.0, "cpu_percent": 0.5}
        ]
        
        for s in services_data:
            existing = db.query(ServiceModel).filter(ServiceModel.name == s["name"]).first()
            if not existing:
                db.add(ServiceModel(**s))
                
        # Create sample projects
        projects_data = [
            {
                "name": "Acme API Service",
                "description": "Core REST backend for enterprise customer applications.",
                "repo_url": "https://github.com/acme/api-service.git",
                "branch": "main",
                "app_type": "Python FastAPI",
                "status": "active",
                "port": 8001,
                "domain": "api.acme.local",
                "service_name": "serverpilot-acme-api.service",
                "deployment_directory": sanitize_and_validate_path("acme-api", "Acme API Service"),
                "environment_vars": {"ENV": "production", "DATABASE_URL": "postgresql://acme:secret@localhost:5432/acmedb"},
                **get_default_commands("Python FastAPI", 8001)
            },
            {
                "name": "Dashboard Storefront",
                "description": "Public ecommerce web frontend.",
                "repo_url": "https://github.com/acme/storefront.git",
                "branch": "production",
                "app_type": "Static HTML/CSS/JavaScript",
                "status": "active",
                "port": 3000,
                "domain": "storefront.acme.local",
                "service_name": "serverpilot-storefront.service",
                "deployment_directory": sanitize_and_validate_path("storefront", "Dashboard Storefront"),
                "environment_vars": {"NODE_ENV": "production", "PORT": 3000},
                **get_default_commands("Static HTML/CSS/JavaScript", 3000)
            }
        ]

        for p in projects_data:
            existing = db.query(Project).filter(Project.name == p["name"]).first()
            if not existing:
                proj = Project(**p)
                db.add(proj)
                db.flush()
                
                dep = Deployment(
                    project_id=proj.id,
                    project_name=proj.name,
                    commit_hash="e94c8b2",
                    commit_message="Initial release deployment v1.0",
                    status="success",
                    log="[INFO] Build started...\n[INFO] Dependencies resolved.\n[SUCCESS] Health check OK.\n[SUCCESS] Deployment complete.",
                    duration_seconds=14
                )
                db.add(dep)

        db.commit()
        print("Database initialized & seeded successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_db(reset=True)
