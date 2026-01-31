from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    PROJECT_NAME: str = "LLM Recommendation Engine"
    API_V1_STR: str = "/api/v1"
    
    MONGODB_URL: str
    DATABASE_NAME: str
    
    REDIS_URL: str
    
    OPENAI_API_KEY: str
    MODEL_PATH: str = "backend/app/ml/models"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
