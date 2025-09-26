from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    # OpenAI API Settings
    OPENAI_API_KEY: str | None = None # Allow key to be optional to enable server startup
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    OPENAI_MODEL_CHEAT_CHECK: str = "qwen3-235b-a22b"
    KLINE_API_SECRET_KEY: str | None = None # Renamed from API_SECRET_KEY
    APP_LOGIN_SECRET_KEY: str | None = None # New key for UI login

    # JWT Settings for OAuth2
    SECRET_KEY: str = "a_default_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 600

    # Database URL
    DATABASE_URL: str = "sqlite:///./veloera.db"

    # Linux.do OAuth Settings
    LINUXDO_CLIENT_ID: str | None = None
    LINUXDO_CLIENT_SECRET: str | None = None
    LINUXDO_SCOPE: str = "read"

    # Server Settings
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    UVICORN_RELOAD: bool = True

    # Point to the .env file in the 'backend' directory relative to the project root
    model_config = SettingsConfigDict(env_file=".env")

# Create a single instance of the settings
settings = Settings()