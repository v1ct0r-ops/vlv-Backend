from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    API_TITLE: str = "Inventario de Gas"
    DEBUG: bool = False
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # ignora variables del .env que no estén declaradas aquí

settings = Settings()