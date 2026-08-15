"""会话管理 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import User
from .. import schemas
from ..services import session_service

router = APIRouter()


@router.get("", response_model=list[schemas.SessionInfo])
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return session_service.list_user_sessions(db, current_user)


@router.post("", response_model=schemas.SessionInfo)
def create_session(
    payload: schemas.SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return session_service.create_session(
        db, current_user, title=payload.title, default_kb_ids=payload.default_kb_ids
    )


@router.patch("/{session_id}", response_model=schemas.SessionInfo)
def rename_session(
    session_id: int,
    payload: schemas.SessionRename,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sess = session_service.get_session_of_user(db, session_id, current_user)
    return session_service.rename_session(db, sess, payload.title)


@router.delete("/{session_id}", response_model=schemas.SuccessResp)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sess = session_service.get_session_of_user(db, session_id, current_user)
    session_service.delete_session(db, sess)
    return schemas.SuccessResp(message="会话已删除")


@router.get("/{session_id}/messages", response_model=list[schemas.MessageInfo])
def get_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sess = session_service.get_session_of_user(db, session_id, current_user)
    return session_service.list_messages(db, sess)
