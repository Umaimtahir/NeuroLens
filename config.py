from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080
    ENCRYPTION_KEY: str
    ALLOWED_ORIGINS: str = "http://localhost,http://localhost:8080"
    
    # Email settings
    EMAIL_ENABLED: bool = True
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_USER: str = ""
    EMAIL_PASSWORD: str = ""
    EMAIL_FROM: str = "NeuroLens <noreply@neurolens.app>"
    
    class Config:
        env_file = ".env"
    
    @property
    def allowed_origins_list(self) -> List[str]:
        origins = [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
        origins.extend(["http://10.0.2.2:8000", "http://10.0.2.2"])
        return origins

settings = Settings()