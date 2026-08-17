from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# DeepSeek API compatible model IDs (shown in console as "V4-Flash", but actual
# model parameter you must send is always `deepseek-chat` / `deepseek-reasoner`)
_DS_MODEL_FLASH = "deepseek-chat"
_DS_MODEL_REASONER = "deepseek-reasoner"
_DS_BASE_URL = "https://api.deepseek.com/v1"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    APP_NAME: str = "电商RAG知识库问答系统"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8002

    # Database
    DATABASE_URL: str = "sqlite:///./data/app.db"

    # JWT
    JWT_SECRET_KEY: str = "dev-secret-key-change-me-please"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ------------------------------------------------------------------
    # LLM provider: "openai_compatible" (DeepSeek remote API) or "ollama"
    # (Defaults to local Ollama; set LLM_PROVIDER=openai_compatible + real
    # key in .env to switch to a remote API.)
    # ------------------------------------------------------------------
    LLM_PROVIDER: Literal["openai_compatible", "ollama"] = "ollama"

    # ---- Remote (OpenAI-compatible API, e.g. DeepSeek) ----
    OPENAI_COMPAT_BASE_URL: str = _DS_BASE_URL
    OPENAI_COMPAT_API_KEY: str = ""
    OPENAI_COMPAT_MODEL: str = _DS_MODEL_FLASH
    OPENAI_COMPAT_TEMPERATURE: float = 0.2
    OPENAI_COMPAT_TOP_P: float = 0.9
    OPENAI_COMPAT_MAX_TOKENS: int = 4096
    OPENAI_COMPAT_TIMEOUT_SECS: float = 120.0

    # ---- Local Ollama ----
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    # 本地 128k 上下文模型（用 ollama create 从 qwen2.5:7b 权重创建，
    # 无需重新下载）：
    #   printf 'FROM qwen2.5:7b\nPARAMETER num_ctx 131072\n' | ollama create qwen2.5:7b-128k
    OLLAMA_LLM_MODEL: str = "qwen2.5:7b-128k"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    # 上下文窗口：128k = 131072。内存不足可调小（如 32768 为原生 32k）。
    OLLAMA_NUM_CTX: int = 131072

    # Embeddings provider (keep Ollama by default — switching embeddings
    # provider would require rebuilding ALL vector collections, so we leave
    # this local unless user explicitly opts in.)
    EMBED_PROVIDER: Literal["ollama"] = "ollama"

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

    @field_validator("OPENAI_COMPAT_BASE_URL", mode="before")
    @classmethod
    def _normalize_base_url(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            return ""
        # Strip ALL trailing slashes so we never end up with "..//v1/chat"
        return v.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
