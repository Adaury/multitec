from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite:///./multitec.db"

    jwt_secret: str = "change-this-secret-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    admin_email: str = "admin@multitec.com"
    admin_password: str = "change-this-password"
    admin_name: str = "Administrador"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    upload_dir: str = "./uploads"

    itbis_rate: float = 0.18
    quote_stale_days: int = 7

    anthropic_api_key: str = ""

    # IA local (Ollama) — ver services/ai_client.py
    ollama_host: str = "http://localhost:11434"
    ai_model: str = "llama3.2"
    ai_vision_model: str = "llava"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
