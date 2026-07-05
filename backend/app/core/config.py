from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_JWT_SECRET = "change-this-secret-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite:///./multitec.db"

    jwt_secret: str = INSECURE_DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    # Access token corto (se renueva solo via /api/auth/refresh); la sesión real la
    # sostiene el refresh token, que sí es revocable server-side.
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    admin_email: str = "admin@multitec.com"
    admin_password: str = "change-this-password"
    admin_name: str = "Administrador"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    upload_dir: str = "./uploads"
    max_upload_mb: int = 25

    itbis_rate: float = 0.18
    quote_stale_days: int = 7

    # Membrete de los PDF de Cotización/Factura — ajustar en .env con los datos reales.
    company_name: str = "Multitec"
    company_rnc: str = ""
    company_address: str = ""
    company_phone: str = ""

    # Notificaciones por correo — ver services/email.py. Sin SMTP_HOST configurado, los
    # correos solo se registran en el log (modo consola), no rompe nada.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "no-reply@multitec.local"
    smtp_use_tls: bool = True

    anthropic_api_key: str = ""

    # IA local (Ollama) — ver app/ai_engine/
    ollama_host: str = "http://localhost:11434"
    ai_model: str = "llama3.2"
    ai_vision_model: str = "llava"
    ai_embedding_model: str = "nomic-embed-text"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
