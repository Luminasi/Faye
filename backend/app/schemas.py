"""Pydantic 请求/响应 Schema"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict

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
    title: str = "新对话"
    default_kb_ids: Optional[list[int]] = None


class SessionRename(BaseModel):
    title: str


class SessionInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    default_kb_ids: Optional[list[int]]
    created_at: datetime
    updated_at: datetime


class MessageInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    content: str
    sources: Optional[list[SourceItem]]
    created_at: datetime


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
