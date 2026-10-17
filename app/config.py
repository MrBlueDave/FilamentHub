"""Application configuration module for FilamentHub 3D."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

# Load .env file if it exists
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

# App server settings
APP_VERSION: str = "1.1"
APP_PORT: int = int(os.getenv("APP_PORT", "8085"))

# Security and Auth settings
# 64-char hex default fallback for development if SECRET_KEY is not defined
DEFAULT_DEV_SECRET = "b47e2c9f1a8d3e5f7a9c0b2d4e6f8a1c3e5a7b9d0e2f4a6c8e0b2d4f6a8c0e2a"
SECRET_KEY: str = os.getenv("SECRET_KEY", "").strip() or DEFAULT_DEV_SECRET
COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").strip().lower() in ("true", "1", "yes")

# Initial Admin bootstrap credentials
INITIAL_ADMIN_USER: str = os.getenv("INITIAL_ADMIN_USER", "admin").strip() or "admin"
INITIAL_ADMIN_PASSWORD: str = os.getenv("INITIAL_ADMIN_PASSWORD", "CambiaSubitoQuestaPassword123!").strip() or "CambiaSubitoQuestaPassword123!"

# Google Gemini Vision API
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"

# Home Assistant Webhook URL
HA_WEBHOOK_URL: str = os.getenv("HA_WEBHOOK_URL", "").strip()

# Storage and Database paths
DATA_DIR: Path = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data"))).resolve()
DB_PATH: Path = DATA_DIR / "filaments.db"
SECURITY_LOG_PATH: Path = DATA_DIR / "security.log"

# Ensure data directory exists on startup
os.makedirs(DATA_DIR, exist_ok=True)
