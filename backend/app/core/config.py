from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    app_env: str = "development"
    log_level: str = "INFO"
    # Comma-separated list of UI origins allowed by CORS.
    cors_origins: str = "http://localhost:5173"
    # Lets reviewers override "now" with the X-Test-Clock header.
    allow_test_clock: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        """Hosts hand out postgres:// or postgresql:// URLs; this app uses the psycopg driver."""
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix) :]
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
