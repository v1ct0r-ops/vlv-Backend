from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    API_TITLE: str = "Inventario de Gas"
    DEBUG: bool = False
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Auth / JWT
    SECRET_KEY: str                        # obligatoria: firma los tokens. Si falta, la app no arranca.
    ALGORITHM: str = "HS256"               # HMAC-SHA256: firma simétrica con SECRET_KEY
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # vida del access token

    # Seed del admin inicial (opcional)
    SEED_ADMIN_EMAIL: str | None = None
    SEED_ADMIN_PASSWORD: str | None = None
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parsea CORS_ORIGINS (coma-separado) limpiando espacios y vacíos.
        Evita que 'http://a, http://b' deje un origin ' http://b' que nunca machea."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"  # ignora variables del .env que no estén declaradas aquí

settings = Settings()