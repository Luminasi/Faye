from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "电商RAG知识库问答系统"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # Database
    DATABASE_URL: str = "sqlite:///./data/app.db"

    # JWT
    JWT_SECRET_KEY: str = "dev-secret-key-change-me-please"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_LLM_MODEL: str = "qwen2.5:7b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./data/chroma"

    # File upload
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # Seed admin
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "123456"
    ADMIN_EMAIL: str = "admin@example.com"

    # Cache
    QUERY_CACHE_MAXSIZE: int = 1000
    QUERY_CACHE_TTL_SECONDS: int = 3600
    EMBED_CACHE_MAXSIZE: int = 10000


@lru_cache
def get_settings() -> Settings:
    return Settings()
