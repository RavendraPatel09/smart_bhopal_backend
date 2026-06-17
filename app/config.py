"""Application configuration, sourced from environment variables with safe defaults."""
import os


class Settings:
    PROJECT_NAME: str = "Smart Bhopal - Grievance Redressal System"
    VERSION: str = "1.0.0"

    # Default to a local SQLite file so the app runs with zero external setup.
    # Override with e.g. postgresql://user@localhost:5432/smart_bhopal in production.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./smart_bhopal.db")

    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-only-secret-change-me-in-production")
    ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")

    # Rewards configuration
    POINTS_ON_SUBMIT: int = int(os.getenv("POINTS_ON_SUBMIT", "10"))
    POINTS_ON_CLOSED: int = int(os.getenv("POINTS_ON_CLOSED", "20"))
    POINTS_WORKER_COMPLETE: int = int(os.getenv("POINTS_WORKER_COMPLETE", "15"))

    # Seed admin credentials (used by seed.py)
    SEED_ADMIN_PHONE: str = os.getenv("SEED_ADMIN_PHONE", "9000000000")
    SEED_ADMIN_PASSWORD: str = os.getenv("SEED_ADMIN_PASSWORD", "Admin@123")


settings = Settings()
