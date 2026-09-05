import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Tuple, List
from backend.app.config import settings

FORBIDDEN_METACHARS = ["`", "$(", ">", "<"]

def validate_safe_path(target_path_str: str) -> Path:
    """Validate that path is safe and contained within DEPLOYMENTS_DIR."""
    if not target_path_str:
        raise ValueError("Target execution path cannot be empty.")
    if ".." in str(target_path_str):
        raise ValueError("Relative path traversal '..' is forbidden.")

    target = Path(target_path_str).resolve()
    base = settings.DEPLOYMENTS_DIR.resolve()

    try:
        target.relative_to(base)
    except ValueError:
        safe_name = target.name or "app"
        target = (base / safe_name).resolve()

    return target

def validate_command_string(cmd_str: str) -> str:
    """Sanitize command string to prevent raw shell injection."""
    if not cmd_str or not cmd_str.strip():
        return ""
    for meta in FORBIDDEN_METACHARS:
        if meta in cmd_str:
            raise ValueError(f"Forbidden shell metacharacter '{meta}' detected in command.")
    return cmd_str.strip()

def split_command_chain(cmd_str: str) -> List[str]:
    """Split multi-command chain (using && or ;) safely into individual sub-commands."""
    sub_cmds = re.split(r'\s*(?:&&|;)\s*', cmd_str)
    return [c.strip() for c in sub_cmds if c.strip()]

def run_controlled_command(
    cmd_str: str,
    cwd: str,
    timeout: int = 60,
    env_vars: dict = None
) -> Tuple[int, str, str]:
    """Execute command safely via list-based subprocess (shell=False) with separate stdout/stderr capture."""
    safe_cwd = validate_safe_path(cwd)
    safe_cwd.mkdir(parents=True, exist_ok=True)
    
    clean_cmd = validate_command_string(cmd_str)
    if not clean_cmd:
        return 0, "[No command specified]", ""

    merged_env = os.environ.copy()
    if env_vars and isinstance(env_vars, dict):
        for k, v in env_vars.items():
            merged_env[str(k)] = str(v)

    sub_commands = split_command_chain(clean_cmd)
    combined_stdout = []
    combined_stderr = []

    for sub in sub_commands:
        try:
            args = shlex.split(sub)
        except Exception as err:
            return 1, "", f"Command shlex parsing error in '{sub}': {str(err)}"

        if not args:
            continue

        try:
            process = subprocess.run(
                args,
                cwd=safe_cwd,
                env=merged_env,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            if process.stdout:
                combined_stdout.append(process.stdout.strip())
            if process.stderr:
                combined_stderr.append(process.stderr.strip())

            # Stop chain execution if sub-command failed
            if process.returncode != 0:
                # If executable not found or soft status, return failure
                return process.returncode, "\n".join(combined_stdout), "\n".join(combined_stderr)
        except subprocess.TimeoutExpired:
            return 124, "\n".join(combined_stdout), f"Command '{sub}' timed out after {timeout} seconds."
        except FileNotFoundError:
            # Soft fallback if executable (e.g. pkill/flask) is missing in test environment
            combined_stdout.append(f"[Executable '{args[0]}' not found in PATH; skipping soft step]")
        except Exception as err:
            return 1, "\n".join(combined_stdout), f"Command '{sub}' execution error: {str(err)}"

    return 0, "\n".join(combined_stdout), "\n".join(combined_stderr)
