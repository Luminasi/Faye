"""会话与消息服务层"""
from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models import ChatSession, ChatMessage, User
from ..utils.logger import get_logger

logger = get_logger("session_service")


def list_user_sessions(db: Session, user: User) -> list[ChatSession]:
    return (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )


def create_session(db: Session, user: User, *, title: str, default_kb_ids: Optional[list[int]] = None) -> ChatSession:
    sess = ChatSession(
        user_id=user.id,
        title=title or "新对话",
        default_kb_ids=default_kb_ids,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    logger.info("session_created", session_id=sess.id, user_id=user.id)
    return sess


def get_session_of_user(db: Session, session_id: int, user: User) -> ChatSession:
    sess = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not sess or sess.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    return sess


def rename_session(db: Session, sess: ChatSession, title: str) -> ChatSession:
    sess.title = title
    sess.updated_at = datetime.now()
    db.commit()
    db.refresh(sess)
    return sess


def delete_session(db: Session, sess: ChatSession) -> None:
    db.delete(sess)
    db.commit()
    logger.info("session_deleted", session_id=sess.id, user_id=sess.user_id)


def list_messages(db: Session, sess: ChatSession) -> list[ChatMessage]:
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == sess.id)
        .order_by(ChatMessage.id.asc())
        .all()
    )


def create_message(
    db: Session,
    sess: ChatSession,
    *,
    role: str,
    content: str,
    sources: Optional[list[dict[str, Any]]] = None,
    tokens_used: int = 0,
    latency_ms: int = 0,
    cache_hit: bool = False,
) -> ChatMessage:
    msg = ChatMessage(
        session_id=sess.id,
        role=role,
        content=content,
        sources=sources,
        tokens_used=tokens_used,
        latency_ms=latency_ms,
        cache_hit=cache_hit,
    )
    db.add(msg)
    # 同步更新会话时间
    sess.updated_at = datetime.now()
    db.commit()
    db.refresh(msg)
    return msg
