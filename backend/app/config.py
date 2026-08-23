"""
Application Configuration and Settings.
"""

import os
from pathlib import Path
from pydantic import BaseModel


class Settings(BaseModel):
    PROJECT_NAME: str = "OptiScan API"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"

    SECRET_KEY: str = os.getenv("SECRET_KEY", "optiscan_super_secret_jwt_key_2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "optiscan_db")

    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    ANNOTATED_DIR: Path = BASE_DIR / "uploads" / "annotated"
    TEMPLATES_DIR: Path = BASE_DIR / "templates"

    CORS_ORIGINS: list = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*",
    ]


settings = Settings()

# Ensure required upload directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)
