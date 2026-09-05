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

        # Discover REAL systemd services & processes running on the machine
        print("[INFO] Auto-discovering REAL system services...")
        from backend.app.services.project_discovery import discover_system_services, discover_real_projects
        services = discover_system_services(db)
        print(f"[SUCCESS] Discovered {len(services)} real system services on host.")

        # Discover REAL projects running/present on the machine
        print("[INFO] Auto-discovering REAL projects on host machine...")
        projects = discover_real_projects(db)
        print(f"[SUCCESS] Discovered {len(projects)} real application projects.")

        db.commit()
        print("Database initialized successfully with REAL server telemetry!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()
        try:
            import pwd, grp
            sp_user = pwd.getpwnam("serverpilot")
            sp_group = grp.getgrnam("serverpilot")
            from backend.app.config import settings
            data_dir = settings.DATA_DIR
            if data_dir.exists():
                os.chown(data_dir, sp_user.pw_uid, sp_group.gr_gid)
                os.chmod(data_dir, 0o770)
                for root, dirs, files in os.walk(data_dir):
                    for d in dirs:
                        p = os.path.join(root, d)
                        os.chown(p, sp_user.pw_uid, sp_group.gr_gid)
                        os.chmod(p, 0o770)
                    for f in files:
                        p = os.path.join(root, f)
                        os.chown(p, sp_user.pw_uid, sp_group.gr_gid)
                        os.chmod(p, 0o660)
        except Exception:
            pass

if __name__ == "__main__":
    init_db(reset=True)
