from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    database_url_readonly: str = ""

    anthropic_api_key: str = ""
    claude_model_smart: str = "claude-sonnet-5-5"
    claude_model_fast: str = "claude-haiku-5-5"

    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    paypal_base_url: str = "https://api-m.sandbox.paypal.com"
    paypal_webhook_id: str = ""

    cloudflare_account_id: str = ""
    cloudflare_ai_token: str = ""

    app_origin: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()
