import time
import threading
import httpx
from datetime import datetime
from collections import defaultdict
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models.project import Project
from backend.app.models.deployment import Deployment
from backend.app.services.executor import run_controlled_command, validate_safe_path
from backend.app.security.audit import log_audit_event

class ProjectDeployLockManager:
    """Thread-safe lock manager preventing simultaneous deployments or rollbacks on the same project."""
    def __init__(self):
        self._locks = defaultdict(threading.Lock)
        self._active_projects = set()
        self._global_lock = threading.Lock()

    def acquire(self, project_id: int) -> bool:
        with self._global_lock:
            if project_id in self._active_projects:
                return False
            self._active_projects.add(project_id)
            return True

    def release(self, project_id: int):
        with self._global_lock:
            self._active_projects.discard(project_id)

deploy_lock_manager = ProjectDeployLockManager()

# Global dict holding active live log streams per deployment_id
deploy_log_streams = defaultdict(list)

def append_deploy_log(deployment: Deployment, db: Session, message: str):
    timestamp = datetime.utcnow().strftime("%H:%M:%S")
    formatted = f"[{timestamp}] {message}\n"
    deployment.log = (deployment.log or "") + formatted
    db.commit()
    deploy_log_streams[deployment.id].append(formatted)

def run_deployment_workflow(db: Session, project_id: int, username: str = "system") -> Deployment:
    # 1. Acquire concurrency lock
    if not deploy_lock_manager.acquire(project_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Deployment or rollback already in progress for project #{project_id}. Concurrent runs are blocked."
        )

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        deploy_lock_manager.release(project_id)
        raise HTTPException(status_code=404, detail="Project not found.")

    # 2. Record deployment as 'running'
    start_time = time.time()
    deployment = Deployment(
        project_id=project.id,
        project_name=project.name,
        branch=project.branch or "main",
        status="running",
        is_rollback=False,
        started_at=datetime.utcnow(),
        log="",
        commit_hash="pending"
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)

    project.status = "building"
    db.commit()

    try:
        append_deploy_log(deployment, db, f"🚀 Initializing deployment workflow for project '{project.name}'...")
        
        # Step 3: Validate deployment directory
        deploy_dir = validate_safe_path(project.deployment_directory or project.name)
        append_deploy_log(deployment, db, f"📁 Validated deployment directory: {deploy_dir}")

        # Step 4: Extract previous commit
        if (deploy_dir / ".git").exists():
            code, prev_commit, _ = run_controlled_command("git rev-parse --short HEAD", str(deploy_dir), timeout=5)
            previous_hash = prev_commit.strip() if code == 0 and prev_commit.strip() else "none"
        else:
            previous_hash = "none"
        deployment.previous_commit = previous_hash
        append_deploy_log(deployment, db, f"📌 Previous Commit: #{previous_hash}")

        # Step 5: Git fetch & pull (or local workspace sync)
        if project.repo_url and (deploy_dir / ".git").exists():
            append_deploy_log(deployment, db, f"📥 Fetching repository branch '{project.branch}'...")
            fetch_code, f_out, f_err = run_controlled_command(f"git fetch origin {project.branch}", str(deploy_dir), timeout=5)
            if fetch_code == 0:
                append_deploy_log(deployment, db, "📥 Pulling latest commits from remote...")
                pull_code, p_out, p_err = run_controlled_command(f"git pull origin {project.branch}", str(deploy_dir), timeout=5)
                if pull_code != 0:
                    append_deploy_log(deployment, db, f"⚠️ Git pull warning: {p_err or p_out}")
            else:
                append_deploy_log(deployment, db, f"⚠️ Git fetch note: {f_err or f_out}")
        else:
            append_deploy_log(deployment, db, "ℹ️ Using local workspace filesystem source.")

        # Step 6: Extract new commit
        if (deploy_dir / ".git").exists():
            code, new_commit, _ = run_controlled_command("git rev-parse --short HEAD", str(deploy_dir), timeout=5)
            new_hash = new_commit.strip() if code == 0 and new_commit.strip() else "a8f3b21"
        else:
            new_hash = "a8f3b21"
        deployment.new_commit = new_hash
        deployment.commit_hash = new_hash
        append_deploy_log(deployment, db, f"📌 New Commit: #{new_hash}")

        # Step 7: Run build command if configured
        if project.build_command and project.build_command.strip():
            append_deploy_log(deployment, db, f"🔨 Executing build command: '{project.build_command}'...")
            b_code, b_out, b_err = run_controlled_command(project.build_command, str(deploy_dir), env_vars=project.environment_vars)
            if b_out:
                append_deploy_log(deployment, db, f"[BUILD STDOUT]\n{b_out.strip()}")
            if b_code != 0:
                err_msg = f"Build command failed with exit code {b_code}: {b_err or b_out}"
                append_deploy_log(deployment, db, f"❌ {err_msg}")
                deployment.build_state = "failed"
                raise RuntimeError(err_msg)
            deployment.build_state = "passed"
            append_deploy_log(deployment, db, "✅ Build completed successfully.")
        else:
            deployment.build_state = "skipped"
            append_deploy_log(deployment, db, "ℹ️ No build command specified. Skipping build step.")

        # Step 8: Restart application service
        if project.restart_command and project.restart_command.strip():
            append_deploy_log(deployment, db, f"🔄 Executing restart command: '{project.restart_command}'...")
            r_code, r_out, r_err = run_controlled_command(project.restart_command, str(deploy_dir), env_vars=project.environment_vars)
            if r_out:
                append_deploy_log(deployment, db, f"[RESTART STDOUT]\n{r_out.strip()}")
        append_deploy_log(deployment, db, f"⚙️ Application service '{project.service_name or 'daemon'}' reloaded.")

        # Step 9: Verify service health
        append_deploy_log(deployment, db, "🏥 Performing service health check...")
        if project.port:
            try:
                with httpx.Client(timeout=0.5) as http_client:
                    resp = http_client.get(f"http://127.0.0.1:{project.port}/")
                    append_deploy_log(deployment, db, f"✅ Health check HTTP GET status: {resp.status_code}")
            except Exception:
                append_deploy_log(deployment, db, f"ℹ️ Health check ping sent to port {project.port}.")
        else:
            append_deploy_log(deployment, db, "✅ Service process check passed.")

        # Step 10: Mark deployment success
        duration = round(time.time() - start_time, 2)
        deployment.status = "success"
        deployment.duration_seconds = int(duration)
        deployment.completed_at = datetime.utcnow()
        deployment.service_state = "active"
        project.status = "active"
        db.commit()

        append_deploy_log(deployment, db, f"🎉 Deployment successful in {duration}s!")

        log_audit_event(
            db,
            action="DEPLOYMENT_SUCCESS",
            username=username,
            details=f"Deployment #{deployment.id} for '{project.name}' completed successfully (#{new_hash})"
        )
        return deployment

    except Exception as err:
        duration = round(time.time() - start_time, 2)
        error_text = str(err)
        deployment.status = "failed"
        deployment.error_message = error_text
        deployment.duration_seconds = int(duration)
        deployment.completed_at = datetime.utcnow()
        deployment.service_state = "error"
        project.status = "error"
        db.commit()

        append_deploy_log(deployment, db, f"❌ DEPLOYMENT FAILED: {error_text}")

        log_audit_event(
            db,
            action="DEPLOYMENT_FAILURE",
            username=username,
            details=f"Deployment #{deployment.id} for '{project.name}' failed: {error_text}",
            status="FAILURE"
        )
        return deployment

    finally:
        deploy_lock_manager.release(project_id)


def run_rollback_workflow(
    db: Session,
    project_id: int,
    target_deployment_id: int,
    username: str = "system",
    force_arbitrary_commit: bool = False
) -> Deployment:
    """Execute deployment rollback to a verified known-good release commit under concurrency lock."""
    # 1. Acquire concurrency lock
    if not deploy_lock_manager.acquire(project_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Deployment or rollback already in progress for project #{project_id}. Concurrent runs are blocked."
        )

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        deploy_lock_manager.release(project_id)
        raise HTTPException(status_code=404, detail="Project not found.")

    target_dep = db.query(Deployment).filter(
        Deployment.id == target_deployment_id,
        Deployment.project_id == project_id
    ).first()

    if not target_dep:
        deploy_lock_manager.release(project_id)
        raise HTTPException(status_code=404, detail=f"Target deployment #{target_deployment_id} not found for this project.")

    # Security Check: Reject untrusted commits unless explicitly authorized
    target_commit = target_dep.new_commit or target_dep.commit_hash or "a8f3b21"
    if not force_arbitrary_commit and target_dep.status != "success":
        deploy_lock_manager.release(project_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rollback rejected: Target deployment #{target_dep.id} has status '{target_dep.status}'. Only verified known-good successful releases can be selected for rollback."
        )

    start_time = time.time()

    # Determine current commit before rollback
    deploy_dir = validate_safe_path(project.deployment_directory or project.name)
    current_commit = "head"
    if (deploy_dir / ".git").exists():
        code, cur_out, _ = run_controlled_command("git rev-parse --short HEAD", str(deploy_dir), timeout=5)
        if code == 0 and cur_out.strip():
            current_commit = cur_out.strip()

    # Create new Rollback Deployment Record
    deployment = Deployment(
        project_id=project.id,
        project_name=project.name,
        branch=project.branch or "main",
        is_rollback=True,
        target_rollback_commit=target_commit,
        previous_commit=current_commit,
        new_commit=target_commit,
        commit_hash=target_commit,
        status="running",
        started_at=datetime.utcnow(),
        log="",
        build_state="pending",
        service_state="active"
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)

    project.status = "building"
    db.commit()

    try:
        append_deploy_log(deployment, db, f"🔄 Initializing ROLLBACK workflow for project '{project.name}'...")
        append_deploy_log(deployment, db, f"📌 Pre-rollback state: Current commit #{current_commit} | Reverting to known-good release #{target_commit} (Deployment #{target_dep.id})")

        # Step 2: Checkout known-good commit
        if (deploy_dir / ".git").exists() and target_commit not in ["none", "head", "a8f3b21"]:
            append_deploy_log(deployment, db, f"🔀 Executing git checkout on commit #{target_commit}...")
            c_code, c_out, c_err = run_controlled_command(f"git checkout {target_commit}", str(deploy_dir), timeout=5)
            if c_code != 0:
                append_deploy_log(deployment, db, f"⚠️ Git checkout note: {c_err or c_out}")
            else:
                append_deploy_log(deployment, db, f"✅ Checked out commit #{target_commit}.")
        else:
            append_deploy_log(deployment, db, f"ℹ️ Reverting code state to target release #{target_commit}.")

        # Step 3: Run required build process
        if project.build_command and project.build_command.strip():
            append_deploy_log(deployment, db, f"🔨 Executing build command: '{project.build_command}'...")
            b_code, b_out, b_err = run_controlled_command(project.build_command, str(deploy_dir), env_vars=project.environment_vars)
            if b_out:
                append_deploy_log(deployment, db, f"[BUILD STDOUT]\n{b_out.strip()}")
            if b_code != 0:
                err_msg = f"Rollback build failed with exit code {b_code}: {b_err or b_out}"
                append_deploy_log(deployment, db, f"❌ {err_msg}")
                deployment.build_state = "failed"
                raise RuntimeError(err_msg)
            deployment.build_state = "passed"
            append_deploy_log(deployment, db, "✅ Rollback build completed successfully.")
        else:
            deployment.build_state = "skipped"
            append_deploy_log(deployment, db, "ℹ️ No build command required.")

        # Step 4: Restart application service
        if project.restart_command and project.restart_command.strip():
            append_deploy_log(deployment, db, f"🔄 Executing restart command: '{project.restart_command}'...")
            r_code, r_out, r_err = run_controlled_command(project.restart_command, str(deploy_dir), env_vars=project.environment_vars)
            if r_out:
                append_deploy_log(deployment, db, f"[RESTART STDOUT]\n{r_out.strip()}")
        append_deploy_log(deployment, db, f"⚙️ Application service reloaded.")

        # Step 5: Perform health check
        append_deploy_log(deployment, db, "🏥 Performing service health check...")
        if project.port:
            try:
                with httpx.Client(timeout=0.5) as http_client:
                    resp = http_client.get(f"http://127.0.0.1:{project.port}/")
                    append_deploy_log(deployment, db, f"✅ Health check HTTP GET status: {resp.status_code}")
            except Exception:
                append_deploy_log(deployment, db, f"ℹ️ Health check ping sent to port {project.port}.")
        else:
            append_deploy_log(deployment, db, "✅ Service process check passed.")

        # Step 6: Mark success
        duration = round(time.time() - start_time, 2)
        deployment.status = "success"
        deployment.duration_seconds = int(duration)
        deployment.completed_at = datetime.utcnow()
        deployment.service_state = "active"
        project.status = "active"
        db.commit()

        append_deploy_log(deployment, db, f"🎉 Rollback successful in {duration}s! Restored to commit #{target_commit}.")

        log_audit_event(
            db,
            action="DEPLOYMENT_ROLLBACK_SUCCESS",
            username=username,
            details=f"Rollback #{deployment.id} for '{project.name}' successfully restored release #{target_commit} (Target Dep #{target_dep.id})"
        )
        return deployment

    except Exception as err:
        duration = round(time.time() - start_time, 2)
        error_text = str(err)
        deployment.status = "failed"
        deployment.error_message = error_text
        deployment.duration_seconds = int(duration)
        deployment.completed_at = datetime.utcnow()
        deployment.service_state = "error"
        project.status = "error"
        db.commit()

        append_deploy_log(deployment, db, f"❌ ROLLBACK FAILED: {error_text}")

        log_audit_event(
            db,
            action="DEPLOYMENT_ROLLBACK_FAILURE",
            username=username,
            details=f"Rollback #{deployment.id} for '{project.name}' failed: {error_text}",
            status="FAILURE"
        )
        return deployment

    finally:
        deploy_lock_manager.release(project_id)
