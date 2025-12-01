from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    GROQ_API_KEY: str
    GROQ_MODEL: str = "groq-1.0-mini"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    JWT_SECRET: str = "change_me"
    # LangChain settings
    LANC_CHAIN_VERBOSE: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
