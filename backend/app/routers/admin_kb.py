"""管理员：知识库管理 API"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_admin, get_current_user
from ..models import User
from .. import schemas
from ..services import knowledge_service as ks

router = APIRouter()


# ============ 知识库 ============

@router.get("", response_model=List[schemas.KBInfo])
def list_kbs(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return ks.list_kbs(db)


@router.post("", response_model=schemas.KBInfo)
def create_kb(
    payload: schemas.KBCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return ks.create_kb(db, name=payload.name, description=payload.description)


@router.patch("/{kb_id}", response_model=schemas.KBInfo)
def update_kb(
    kb_id: int,
    payload: schemas.KBUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    kb = ks.get_kb(db, kb_id)
    return ks.update_kb(db, kb, name=payload.name, description=payload.description)


@router.delete("/{kb_id}", response_model=schemas.SuccessResp)
def delete_kb(
    kb_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    kb = ks.get_kb(db, kb_id)
    ks.delete_kb(db, kb)
    return schemas.SuccessResp(message="知识库已删除")


# ============ 用户列表（用于授权） ============

@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    users = ks.list_all_users(db)
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role.value,
            "is_active": u.is_active,
        }
        for u in users
    ]


# ============ 文档 ============

@router.get("/{kb_id}/documents", response_model=List[schemas.DocumentInfo])
def list_documents(
    kb_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    kb = ks.get_kb(db, kb_id)
    return ks.list_documents(db, kb)


@router.post("/{kb_id}/documents/upload", response_model=schemas.DocumentInfo)
def upload_document(
    kb_id: int,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    kb = ks.get_kb(db, kb_id)
    return ks.upload_document(db, kb, file, background)


@router.delete("/{kb_id}/documents/{doc_id}", response_model=schemas.SuccessResp)
def delete_document(
    kb_id: int,
    doc_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    kb = ks.get_kb(db, kb_id)
    doc = ks.get_document(db, kb, doc_id)
    ks.delete_document(db, kb, doc)
    return schemas.SuccessResp(message="文档已删除")


@router.get("/{kb_id}/documents/{doc_id}/chunks", response_model=List[schemas.ChunkPreview])
def preview_chunks(
    kb_id: int,
    doc_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    kb = ks.get_kb(db, kb_id)
    ks.get_document(db, kb, doc_id)  # 存在性校验
    return ks.preview_chunks(doc_id)


# ============ 授权 ============

@router.post("/{kb_id}/permissions", response_model=schemas.SuccessResp)
def grant_permission(
    kb_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="缺少 user_id")
    kb = ks.get_kb(db, kb_id)
    ks.grant_permission(db, kb, user_id)
    return schemas.SuccessResp(message="已授权")


@router.delete("/{kb_id}/permissions/{user_id}", response_model=schemas.SuccessResp)
def revoke_permission(
    kb_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    kb = ks.get_kb(db, kb_id)
    ks.revoke_permission(db, kb, user_id)
    return schemas.SuccessResp(message="已撤销授权")
