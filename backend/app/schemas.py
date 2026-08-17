"""Pydantic 请求/响应 Schema"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

from .models import DocStatus, UserRole


# ========== Auth ==========
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=64)
    email: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class ChangePassword(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=64)


class TokenResp(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class UserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: Optional[str]
    role: UserRole
    is_active: bool
    created_at: datetime


# ========== Chat Session & Message ==========
class SourceItem(BaseModel):
    doc_id: Optional[int] = None
    doc_name: str
    page: Optional[int] = None
    chunk_index: Optional[int] = None
    snippet: str


class SessionCreate(BaseModel):
    title: str = Field("新对话", min_length=1, max_length=255)
    default_kb_ids: Optional[list[int]] = None


class SessionRename(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


def _coerce_int_list_or_none(v: Any) -> Optional[list[int]]:
    """SQLAlchemy JSON column may contain weird legacy values; sanitize."""
    if v is None:
        return None
    if isinstance(v, list):
        out: list[int] = []
        for item in v:
            try:
                out.append(int(item))
            except (ValueError, TypeError):
                pass
        return out
    # Fallback: anything else (dict, str, 0, True, ...) becomes None
    return None


class SessionInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    default_kb_ids: Optional[list[int]]
    created_at: datetime
    updated_at: datetime

    @field_validator("default_kb_ids", mode="before")
    @classmethod
    def _clean_default_kb_ids(cls, v: Any) -> Optional[list[int]]:
        return _coerce_int_list_or_none(v)


def _coerce_source_list(v: Any) -> Optional[list[dict]]:
    if v is None:
        return None
    if isinstance(v, list):
        cleaned: list[dict] = []
        for item in v:
            if isinstance(item, dict):
                cleaned.append(item)
            else:
                try:
                    cleaned.append(dict(item))
                except Exception:
                    pass
        return cleaned
    return None


class MessageInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    content: str
    sources: Optional[list[SourceItem]]
    created_at: datetime

    @field_validator("sources", mode="before")
    @classmethod
    def _clean_sources(cls, v: Any) -> Any:
        """Pydantic will validate against list[SourceItem]; we just coerce shape."""
        return _coerce_source_list(v)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    kb_ids: Optional[list[int]] = None
    stream: bool = True


# ========== Knowledge Base ==========
class KBCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None


class KBUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class KBInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: Optional[str]
    collection_name: str
    created_at: datetime
    updated_at: datetime


class DocumentInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kb_id: int
    file_name: str
    file_type: str
    file_size: int
    chunk_count: int
    status: DocStatus
    error_msg: Optional[str]
    created_at: datetime


class ChunkPreview(BaseModel):
    chunk_index: int
    content: str
    metadata: dict[str, Any]


# ========== Common ==========
class SuccessResp(BaseModel):
    success: bool = True
    message: str = "ok"
