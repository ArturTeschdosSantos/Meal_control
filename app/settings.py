from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = 'sqlite:///./meal_control.db'
    jwt_secret: str = 'development-only-change-me-before-deploying'
    access_token_minutes: int = 60
    timezone: str = 'America/Sao_Paulo'
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

settings = Settings()
