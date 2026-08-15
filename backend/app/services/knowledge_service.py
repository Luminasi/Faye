"""知识库与文档服务层"""
from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import BackgroundTasks, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Document, DocStatus, KnowledgeBase, User, UserKBPermission, UserRole
from ..rag import file_loader as fl
from ..rag import vector_store as vs
from ..utils.logger import get_logger

settings = get_settings()
logger = get_logger("kb_service")

ALLOWED_EXTS = {"pdf", "docx", "doc", "txt", "md", "markdown", "html", "htm", "csv"}


# ============ 知识库 CRUD ============

def list_kbs(db: Session) -> List[KnowledgeBase]:
    return db.query(KnowledgeBase).order_by(KnowledgeBase.id.desc()).all()


def list_user_authorized_kbs(db: Session, user: User) -> List[KnowledgeBase]:
    """admin 可以看到所有，普通用户只能看到被授权的"""
    if user.role == UserRole.ADMIN:
        return list_kbs(db)
    rows = (
        db.query(KnowledgeBase)
        .join(UserKBPermission, UserKBPermission.kb_id == KnowledgeBase.id)
        .filter(UserKBPermission.user_id == user.id)
        .all()
    )
    return rows


def create_kb(db: Session, *, name: str, description: Optional[str] = None) -> KnowledgeBase:
    if db.query(KnowledgeBase).filter(KnowledgeBase.name == name).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="知识库名称已存在")
    # 先创建，拿到 id，再根据 id 生成 collection_name，保证唯一
    kb = KnowledgeBase(
        name=name,
        description=description,
        collection_name="__placeholder__",
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    kb.collection_name = f"kb_{kb.id}"
    db.commit()
    db.refresh(kb)
    try:
        vs.ensure_collection(kb.collection_name)
    except Exception as e:
        logger.error("ensure_collection_failed", kb_id=kb.id, error=str(e))
    logger.info("kb_created", kb_id=kb.id, name=kb.name, collection=kb.collection_name)
    return kb


def get_kb(db: Session, kb_id: int) -> KnowledgeBase:
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")
    return kb


def update_kb(db: Session, kb: KnowledgeBase, *, name: Optional[str] = None, description: Optional[str] = None) -> KnowledgeBase:
    if name is not None:
        existed = db.query(KnowledgeBase).filter(KnowledgeBase.name == name, KnowledgeBase.id != kb.id).first()
        if existed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="知识库名称已存在")
        kb.name = name
    if description is not None:
        kb.description = description
    kb.updated_at = datetime.now()
    db.commit()
    db.refresh(kb)
    return kb


def delete_kb(db: Session, kb: KnowledgeBase) -> None:
    # 1. 删除上传文件
    for doc in kb.documents:
        try:
            if os.path.exists(doc.file_path):
                os.remove(doc.file_path)
        except Exception:
            pass
    # 2. 删除预览 chunk 缓存目录中的所有对应 doc_*.json
    chunks_dir = _chunks_dir()
    if chunks_dir.exists():
        for doc in kb.documents:
            p = chunks_dir / f"doc_{doc.id}.json"
            if p.exists():
                try: os.remove(p)
                except Exception: pass
    # 3. 删除向量 collection
    try:
        vs.delete_collection(kb.collection_name)
    except Exception as e:
        logger.warning("delete_collection_skip", kb_id=kb.id, error=str(e))
    # 4. DB 级联删除
    db.delete(kb)
    db.commit()
    logger.info("kb_deleted", kb_id=kb.id, name=kb.name)


# ============ 文档 ============

def _chunks_dir() -> Path:
    p = Path(settings.UPLOAD_DIR) / "chunks"
    p.mkdir(parents=True, exist_ok=True)
    return p


def list_documents(db: Session, kb: KnowledgeBase) -> List[Document]:
    return (
        db.query(Document)
        .filter(Document.kb_id == kb.id)
        .order_by(Document.id.desc())
        .all()
    )


def get_document(db: Session, kb: KnowledgeBase, doc_id: int) -> Document:
    doc = db.query(Document).filter(Document.id == doc_id, Document.kb_id == kb.id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")
    return doc


def _save_upload_file(dest_dir: Path, file: UploadFile) -> tuple[Path, str]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1]
    new_name = f"{uuid.uuid4().hex}{ext}"
    target = dest_dir / new_name
    with open(target, "wb") as out:
        shutil.copyfileobj(file.file, out)
    return target, new_name


def upload_document(
    db: Session,
    kb: KnowledgeBase,
    file: UploadFile,
    background: BackgroundTasks,
) -> Document:
    ext = (os.path.splitext(file.filename or "")[1]).lstrip(".").lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"不支持的文件类型: .{ext}")
    # 大小限制（FastAPI 层最好再加一层限制，这里是兜底）
    dest_dir = Path(settings.UPLOAD_DIR) / f"kb_{kb.id}"
    saved_path, _ = _save_upload_file(dest_dir, file)
    file_size = saved_path.stat().st_size
    if file_size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        try: os.remove(saved_path)
        except Exception: pass
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"文件超过 {settings.MAX_UPLOAD_SIZE_MB}MB")

    doc = Document(
        kb_id=kb.id,
        file_name=file.filename or "unknown",
        file_path=str(saved_path),
        file_type=ext,
        file_size=file_size,
        status=DocStatus.PROCESSING,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # 异步执行解析 + 分块 + 向量化
    background.add_task(_process_document, doc.id, kb.collection_name)
    logger.info("doc_uploaded", doc_id=doc.id, kb_id=kb.id, file=doc.file_name)
    return doc


def _process_document(doc_id: int, collection_name: str) -> None:
    """后台任务：切分 + 向量化 + 入库"""
    from ..database import SessionLocal  # 避免循环导入

    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return
        chunks = fl.load_and_split(doc.file_path, file_name=doc.file_name, doc_id=doc.id)
        # 写入预览文件
        chunks_path = _chunks_dir() / f"doc_{doc.id}.json"
        preview = [
            {"chunk_index": c.metadata.get("chunk_index", i), "content": c.page_content, "metadata": c.metadata}
            for i, c in enumerate(chunks)
        ]
        with open(chunks_path, "w", encoding="utf-8") as f:
            json.dump(preview, f, ensure_ascii=False, indent=2)
        # 写入向量库
        added = 0
        if chunks:
            added = vs.add_documents(collection_name, chunks)
        doc.chunk_count = added
        doc.status = DocStatus.READY
        doc.updated_at = datetime.now()
        db.commit()
        logger.info("doc_processed", doc_id=doc.id, chunks=added)
    except Exception as e:
        logger.error("doc_process_failed", doc_id=doc_id, error=str(e))
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc.status = DocStatus.FAILED
            doc.error_msg = (str(e) or "unknown")[:512]
            db.commit()
    finally:
        db.close()


def delete_document(db: Session, kb: KnowledgeBase, doc: Document) -> None:
    # 1. 删除文件
    try:
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
    except Exception as e:
        logger.warning("remove_uploaded_file_failed", doc_id=doc.id, error=str(e))
    # 2. 删除预览 JSON
    p = _chunks_dir() / f"doc_{doc.id}.json"
    if p.exists():
        try: os.remove(p)
        except Exception: pass
    # 3. 从向量库按 doc_id 元数据删除
    try:
        vs.delete_by_metadata(kb.collection_name, doc_id=doc.id)
    except Exception as e:
        logger.warning("vector_delete_skip", doc_id=doc.id, error=str(e))
    # 4. DB
    db.delete(doc)
    db.commit()
    logger.info("doc_deleted", doc_id=doc.id, kb_id=kb.id, file=doc.file_name)


def preview_chunks(doc_id: int) -> list[dict]:
    p = _chunks_dir() / f"doc_{doc.id}.json"
    if not p.exists():
        return []
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


# ============ 权限 ============

def grant_permission(db: Session, kb: KnowledgeBase, user_id: int) -> UserKBPermission:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if user.role == UserRole.ADMIN:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="管理员默认拥有所有知识库权限")
    existed = (
        db.query(UserKBPermission)
        .filter(UserKBPermission.kb_id == kb.id, UserKBPermission.user_id == user.id)
        .first()
    )
    if existed:
        return existed
    p = UserKBPermission(kb_id=kb.id, user_id=user.id)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def revoke_permission(db: Session, kb: KnowledgeBase, user_id: int) -> None:
    p = (
        db.query(UserKBPermission)
        .filter(UserKBPermission.kb_id == kb.id, UserKBPermission.user_id == user_id)
        .first()
    )
    if p:
        db.delete(p)
        db.commit()


def list_all_users(db: Session) -> List[User]:
    return db.query(User).order_by(User.id.asc()).all()
