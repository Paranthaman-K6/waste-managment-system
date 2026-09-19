"""Application configuration using pydantic BaseSettings.
Loads environment variables from a .env file if present.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    # Core settings (defaults to SQLite for zero-config deployment)
    DATABASE_URL: str = "sqlite+aiosqlite:///./test.db"
    JWT_SECRET_KEY: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # Cookie names for auth (optional, can be overridden)
    ACCESS_COOKIE_NAME: str = "access_token"
    REFRESH_COOKIE_NAME: str = "refresh_token"
    # Optional upload directory
    UPLOAD_DIR: str = "uploads"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

# ---------------------------------------------------------------------------
# Reward rates (points per kg, per waste type)
# Source of truth for the reward system. Exposed via GET /rewards/rates.
# Covers the six canonical types used by the app (organic/plastic/e-waste/
# metal/paper/glass) plus spec fallback aliases so any waste type awards points.
# ---------------------------------------------------------------------------
REWARD_RATES: dict[str, int] = {
    # canonical app types
    "organic": 5,
    "plastic": 10,
    "e-waste": 15,
    "ewaste": 15,  # alias
    "metal": 10,
    "paper": 8,
    "glass": 5,
    # spec fallback/alias types
    "recyclable": 10,
    "hazardous": 8,
    "general": 3,
}

DEFAULT_REWARD_RATE: int = 3


def reward_rate_for(waste_type: str) -> int:
    return REWARD_RATES.get((waste_type or "").strip().lower(), DEFAULT_REWARD_RATE)


def calculate_points(weight_kg: float, waste_type: str) -> int:
    """Points = floor(weight_kg * rate). Rejects non-positive weight."""
    weight = float(weight_kg)
    if weight <= 0:
        raise ValueError("weight must be greater than zero")
    return int(weight * reward_rate_for(waste_type))


settings = Settings()

def get_settings() -> Settings:
    return settings
