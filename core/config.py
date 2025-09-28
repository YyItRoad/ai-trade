from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import Optional

class Settings(BaseSettings):
    # --- 数据库设置 ---
    # 优先使用 DATABASE_URL。如果未提供，则会根据下面的分项自动构建。
    DATABASE_URL: Optional[str] = None
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[int] = 3306
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    DB_NAME: Optional[str] = None

    # --- OpenAI API 设置 ---
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4-turbo"
    
    # --- K-line API 设置 ---
    KLINE_API_SECRET_KEY: Optional[str] = None
    KLINE_API_BASE_URL: str = ""
    
    # --- 应用安全设置 ---
    APP_LOGIN_SECRET_KEY: Optional[str] = None

    # model_config 指向 .env 文件
    model_config = SettingsConfigDict(env_file=".env", extra='ignore')

    @model_validator(mode='after')
    def assemble_db_connection(self) -> 'Settings':
        if self.DATABASE_URL is None:
            if all([self.DB_HOST, self.DB_USER, self.DB_PASSWORD, self.DB_NAME]):
                self.DATABASE_URL = (
                    f"mysql://{self.DB_USER}:{self.DB_PASSWORD}"
                    f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
                )
            else:
                # 如果两种配置都不完整，则回退到默认的 SQLite 数据库
                default_db_path = "default_trade_analysis.db"
                self.DATABASE_URL = f"sqlite:///{default_db_path}"
                # 使用 print 因为此时 logger 可能还未完全配置好
                print(f"警告: 未找到完整的数据库配置。将回退使用默认的 SQLite 数据库: {default_db_path}")
        return self

# 创建 settings 的单例
settings = Settings()