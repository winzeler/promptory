from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # GitHub OAuth
    github_client_id: str = ""
    github_client_secret: str = ""

    # App
    app_secret_key: str = "change-me-in-production"
    app_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"

    # Database
    database_path: str = "./data/promptory.db"

    # Logging
    log_level: str = "info"

    # Rate limiting
    rate_limit_per_minute: int = 100

    # CORS
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
