from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/slippers"
    SECRET_KEY: str = "supersecretkey"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
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

    class Config:
        env_file = ".env"

settings = Settings() 