from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    ok_client_id: str
    ok_client_secret: str = ""
    ok_access_token: str = ""
    ok_public_key: str = ""
    ok_session_key: str = ""
    ok_session_secret_key: str = ""
    
    mongo_uri: str = "mongodb://mongo:27017/"
    mongo_db_name: str = "okdb"
    
    api_base_url: str = "https://api.ok.ru/fb.do"
    rate_limit_delay: float = 1.0


@lru_cache
def get_settings() -> Settings:
    return Settings()

