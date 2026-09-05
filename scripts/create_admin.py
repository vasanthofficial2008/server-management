import os
import sys
import argparse
import getpass
from pathlib import Path

# Add root directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.database import SessionLocal, engine, Base
from backend.app.models.user import User
from backend.app.security.auth import get_password_hash
from backend.app.security.audit import log_audit_event

def create_admin(username: str = None, email: str = None, password: str = None, full_name: str = "Administrator"):
    # Ensure database schema is created
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        try:
            if not username:
                username = os.getenv("ADMIN_USERNAME") or input("Enter admin username: ").strip()
            if not email:
                email = os.getenv("ADMIN_EMAIL") or input("Enter admin email: ").strip()
            if not password:
                password = os.getenv("ADMIN_PASSWORD") or getpass.getpass("Enter admin password: ").strip()
        except EOFError:
            print("[ERROR] Stdin is non-interactive. Please pass credentials via arguments (--username, --email, --password) or environment variables.")
            sys.exit(1)

        if not username or not email or not password:
            print("[ERROR] Username, email, and password are required.")
            sys.exit(1)

        if len(password) < 8:
            print("[ERROR] Password must be at least 8 characters long.")
            sys.exit(1)

        # Check existing user
        existing_user = db.query(User).filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            existing_user.hashed_password = get_password_hash(password)
            existing_user.is_superuser = True
            existing_user.is_active = True
            db.commit()
            log_audit_event(
                db,
                action="ADMIN_PASSWORD_UPDATE",
                username=existing_user.username,
                user_id=existing_user.id,
                details=f"Updated administrator password for '{existing_user.username}' via CLI script."
            )
            print(f"[SUCCESS] Updated password for administrator user '{existing_user.username}' successfully!")
            return

        hashed = get_password_hash(password)
        new_admin = User(
            username=username,
            email=email,
            hashed_password=hashed,
            full_name=full_name,
            is_active=True,
            is_superuser=True
        )

        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)

        log_audit_event(
            db,
            action="ADMIN_CREATE",
            username=username,
            user_id=new_admin.id,
            details=f"Created administrator account '{username}' ({email}) via CLI script."
        )

        print(f"[SUCCESS] Administrator user '{username}' created successfully!")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to create administrator user: {e}")
        sys.exit(1)
    finally:
        db.close()
        fix_database_permissions()

def fix_database_permissions():
    """Ensure database file and directory are owned and writable by serverpilot system user on Linux."""
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
    parser = argparse.ArgumentParser(description="Create a ServerPilot Control Panel Administrator User.")
    parser.add_argument("--username", "-u", type=str, help="Admin username")
    parser.add_argument("--email", "-e", type=str, help="Admin email address")
    parser.add_argument("--password", "-p", type=str, help="Admin password (min 8 chars)")
    parser.add_argument("--full-name", "-n", type=str, default="Administrator", help="Admin full name")

    args = parser.parse_args()
    create_admin(username=args.username, email=args.email, password=args.password, full_name=args.full_name)
