from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache

class Settings(BaseSettings):
    saying_db_user: Optional[str] = None
    saying_db_pass: Optional[str] = None
    saying_db_host: Optional[str] = None
    saying_db_port: Optional[int] = 3306
    saying_db_name: Optional[str] = None
    saying_db_enable: str = "0" # Default to disabled
    vestaboard_api_key: Optional[str] = None
    vestaboard_api_secret: Optional[str] = None

    class Config:
        env_file = '.env'
        extra = 'ignore'

@lru_cache()
def get_settings() -> Settings:
    """Loads and returns the application settings."""
    return Settings()