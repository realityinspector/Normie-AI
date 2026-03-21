from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://localhost:5432/normalizer"
    openrouter_api_key: str = ""
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24 * 30  # 30 days
    apple_team_id: str = ""
    apple_bundle_id: str = "com.normalaizer.app"
    # Credits given to new users
    initial_credits: int = 50
    # Set to "true" to enable /auth/dev endpoint (disable in production!)
    dev_auth_enabled: str = "true"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
