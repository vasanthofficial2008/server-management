from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    APP_NAME: str = "ServerPilot Control Panel"
    APP_VERSION: str = "1.0.0"
    ENV: str = "development"
    DEBUG: bool = True
    
    SECRET_KEY: str = "serverpilot-jwt-secret-key-production-ready-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/data/serverpilot.db"
    
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "logs"
    DEPLOYMENTS_DIR: Path = BASE_DIR / "deployments"
    
    model_config = SettingsConfigDict(env_file=("/etc/serverpilot/.env", ".env"), extra="ignore")

settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
settings.DEPLOYMENTS_DIR.mkdir(parents=True, exist_ok=True)

def setup_logging():
    """Configure structured logging for ServerPilot production & development environments."""
    import logging
    import sys
    
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    log_format = "%(asctime)s [%(levelname)s] %(name)s (%(process)d): %(message)s"
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    log_file = settings.LOGS_DIR / "serverpilot.log"
    try:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)
    except Exception as err:
        print(f"Notice: File logger at {log_file} could not be initialized: {err}")
        
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers,
        force=True
    )

setup_logging()

