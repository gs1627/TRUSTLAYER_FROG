from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = BACKEND_DIR / ".env"


def normalize_database_url(url: str, *, base_dir: Path = BACKEND_DIR) -> str:
    """Normalize PostgreSQL URLs for asyncpg and anchor relative SQLite file paths."""
    cleaned = url.strip()
    if not cleaned:
        raise ValueError("DATABASE_URL cannot be empty")

    if cleaned.startswith("postgres://"):
        return "postgresql+asyncpg://" + cleaned[len("postgres://"):]
    if cleaned.startswith("postgresql://"):
        return "postgresql+asyncpg://" + cleaned[len("postgresql://"):]

    for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
        if cleaned.startswith(prefix):
            raw_path = cleaned[len(prefix):]
            path_part, sep, query_part = raw_path.partition("?")
            if (
                not path_part
                or path_part == ":memory:"
                or path_part.startswith("file:")
                or path_part.startswith("/")
                or path_part.startswith("\\")
                or (len(path_part) >= 2 and path_part[1] == ":")
                or Path(path_part).is_absolute()
            ):
                return cleaned
            resolved = (base_dir / path_part).resolve().as_posix()
            return f"{prefix}{resolved}{sep}{query_part}"

    return cleaned


class Settings(BaseSettings):
    app_name: str = "TRUSTLAYER Backend"
    app_env: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    database_url: str = "sqlite+aiosqlite:///./trustlayer.db"

    detectif_api_key: str | None = None
    detectif_base_url: str = "https://platform.detectif.ai"
    detectif_timeout_seconds: float = 300.0

    detectif_webhook_secret: str | None = None
    webhook_tolerance_seconds: int = 300

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_max_output_tokens: int = 1024

    sarvam_api_key: str | None = None
    sarvam_base_url: str = "https://api.sarvam.ai"
    sarvam_model: str = "saaras:v2.5"
    sarvam_timeout_seconds: float = 60.0
    sarvam_sample_rate: int = 16000
    sarvam_encoding: str = "audio/pcm"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_upload_mb: int = 25
    backend_access_token: str | None = None

    model_config = SettingsConfigDict(
        env_file=DEFAULT_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("DATABASE_URL must be a string")
        return normalize_database_url(value)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
