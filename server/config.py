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
    database_path: str = "./data/promptdis.db"

    # Logging
    log_level: str = "info"

    # Rate limiting
    rate_limit_per_minute: int = 100

    # CORS
    cors_origins: str = "http://localhost:5173"

    # Deployment mode: "container" (default) or "lambda"
    deployment_mode: str = "container"

    # AWS (Lambda mode only)
    aws_region: str = "us-west-2"
    dynamodb_state_table: str = "promptdis-oauth-states"
    s3_tts_bucket: str = ""

    # ElevenLabs TTS (global fallback — prefer per-app keys via provider_configs)
    elevenlabs_api_key: str = ""
    elevenlabs_default_model: str = "eleven_multilingual_v2"
    elevenlabs_default_voice_id: str = ""
    tts_cache_dir: str = "./data/tts_cache"
    tts_cache_max_entries: int = 100
    tts_cache_ttl_hours: int = 24

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def cookie_domain(self) -> str | None:
        """Return shared cookie domain for cross-subdomain auth, or None for localhost."""
        from urllib.parse import urlparse
        host = urlparse(self.frontend_url).hostname or ""
        if host in ("localhost", "127.0.0.1") or host.startswith("localhost:"):
            return None
        parts = host.split(".")
        if len(parts) >= 2:
            return "." + ".".join(parts[-2:])
        return None

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
