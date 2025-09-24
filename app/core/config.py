from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Any

class Settings(BaseSettings):
    # Pydantic v2 settings: read from .env and ignore extra keys to prevent crashes from unused env vars
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/slippers"
    SECRET_KEY: str = "supersecretkey"
    ALGORITHM: str = "HS256"
    # CALLBACK_BASIC_AUTH_USERNAME and CALLBACK_BASIC_AUTH_PASSWORD removed (payment system)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,https://www.optomoyoqkiyim.uz/"
    LOGIN_RATE_LIMIT: int = 5  # попыток
    LOGIN_RATE_WINDOW_SEC: int = 300  # окно в секундах (5 минут)
    COOKIE_SAMESITE: str = "lax"  # options: 'lax', 'strict', 'none'
    COOKIE_SECURE: bool = True
    COOKIE_DOMAIN: str | None = None
    # Global rate limiting
    RATE_LIMIT_REQUESTS: int = 100  # запросов за окно
    RATE_LIMIT_WINDOW_SEC: int = 60  # окно, секунд
    RATE_LIMIT_EXCLUDE_PATHS: str = "/docs,/redoc,/openapi.json,/favicon.ico,/static"
    TRUST_PROXY: bool = False  # если True, брать IP из X-Forwarded-For
    DEBUG: bool = True  # для разработки
    PHONE_ALLOWED_PREFIXES: str = "+,+998"  # допустимые префиксы телефонов
    # OCTO payment configuration
    OCTO_API_BASE: str = "https://secure.octo.uz"  # Base API URL per docs 
    OCTO_SHOP_ID: str = ""  
    OCTO_SECRET: str = ""   
    OCTO_RETURN_URL: str = "https://www.optomoyoqkiyim.uz/"  # Your site success URL
    OCTO_NOTIFY_URL: str = ""  # Webhook/notify URL from OCTO to us
    OCTO_LANGUAGE: str = "ru"
    OCTO_AUTO_CAPTURE: bool = True  # one-stage payment
    OCTO_CURRENCY: str = "UZS"
    OCTO_USD_UZS_RATE: float | None = None  # Set to enforce min refund >= 1 USD
    OCTO_TEST: bool = False  # Use test mode payments when true
    # Optional: pass-through params merged into prepare_payment payload
    # Provide as JSON in .env, e.g. OCTO_EXTRA_PARAMS={"ui": {"ask_for_email": false}}
    OCTO_EXTRA_PARAMS: dict[str, Any] | None = None
    # App runtime settings (production deploy alignment)
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_WORKERS: int = 1  # only used if a process manager launches multiple workers

settings = Settings() 