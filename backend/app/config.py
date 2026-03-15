"""Application configuration using pydantic settings."""

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    APP_NAME: str = "FarmTrust AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # API
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "changeme-in-production-use-random-32-char-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    ALLOWED_HOSTS: List[str] = ["*"]

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://farmtrust:farmtrust@localhost:5432/farmtrust"
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 300  # 5 minutes

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_NOTIFICATIONS: str = "farmtrust.notifications"
    KAFKA_TOPIC_AUDIT: str = "farmtrust.audit"
    KAFKA_TOPIC_TRUST_UPDATES: str = "farmtrust.trust_updates"

    # ML Model
    ML_MODEL_PATH: str = "/app/ml/models/tft_model.pt"
    ML_SERVICE_URL: str = "http://ml-service:8001"

    # File Storage
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET: str = "farmtrust-documents"
    AWS_REGION: str = "ap-south-1"

    # Notification
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FCM_SERVER_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
