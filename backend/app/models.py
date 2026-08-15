"""ORM 数据模型"""
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


class UserRole(str, PyEnum):
    USER = "user"
    ADMIN = "admin"


class DocStatus(str, PyEnum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(128), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # 关系
    sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    kb_permissions = relationship("UserKBPermission", back_populates="user", cascade="all, delete-orphan")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False, default="新对话")
    # 默认参与检索的知识库 id 列表，JSON 存储，可空表示所有授权库
    default_kb_ids = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    user = relationship("User", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role = Column(String(16), nullable=False)  # user / assistant
    content = Column(Text, nullable=False)
    # 存储引用来源：[{ "id", "doc_name", "page", "chunk_index", "snippet" }]
    sources = Column(JSON, nullable=True)
    tokens_used = Column(Integer, default=0, nullable=True)
    latency_ms = Column(Integer, default=0, nullable=True)
    cache_hit = Column(Boolean, default=False, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    session = relationship("ChatSession", back_populates="messages")


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), unique=True, nullable=False)
    description = Column(String(512), nullable=True)
    # ChromaDB collection 名，用 kb_{id} 确保唯一
    collection_name = Column(String(128), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    documents = relationship("Document", back_populates="kb", cascade="all, delete-orphan")
    permissions = relationship("UserKBPermission", back_populates="kb", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    kb_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_type = Column(String(32), nullable=False)  # pdf/docx/txt/md/html
    file_size = Column(Integer, default=0)  # bytes
    chunk_count = Column(Integer, default=0)
    status = Column(Enum(DocStatus), default=DocStatus.PROCESSING, nullable=False)
    error_msg = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    kb = relationship("KnowledgeBase", back_populates="documents")


class UserKBPermission(Base):
    """用户-知识库授权表；若表为空，admin之外的用户默认看不到任何知识库"""
    __tablename__ = "user_kb_permissions"
    __table_args__ = (UniqueConstraint("user_id", "kb_id", name="uq_user_kb"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    kb_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False, index=True)
    granted_at = Column(DateTime, default=datetime.now, nullable=False)

    user = relationship("User", back_populates="kb_permissions")
    kb = relationship("KnowledgeBase", back_populates="permissions")
