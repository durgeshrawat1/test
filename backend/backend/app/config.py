import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "NexusCore Banking API"
    DEV_MODE: bool = False  # Default False; avoid enabling in production
    
    # AWS Aurora PostgreSQL Credentials
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "password")
    DB_HOST: str = os.getenv("DB_HOST", "")  # Your Aurora Endpoint (required in production)
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "banking_core")
    
    # Construct the Async Database URL
    @property
    def DATABASE_URL(self) -> str:
        # Allow explicit DATABASE_URL override (used in production). If not provided,
        # construct the URL from component parts (useful for simple local dev).
        explicit = os.getenv("DATABASE_URL")
        if explicit:
            return explicit
        # In production require either a full DATABASE_URL or a DB_HOST value
        if not self.DB_HOST:
            raise RuntimeError("DATABASE_URL or DB_HOST must be set in the environment for production deployments")
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"

    # DEV_MODE remains False by default. Avoid enabling DEV_MODE in production.
    def __init__(self, **values):
        # If the caller provided DEV_MODE via env/config, Pydantic will populate it.
        super().__init__(**values)

settings = Settings()
