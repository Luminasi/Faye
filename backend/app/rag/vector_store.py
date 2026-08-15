"""ChromaDB 向量库封装：按知识库分 collection，支持 CRUD"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable, List, Optional

from langchain_core.documents import Document

from ..config import get_settings
from ..utils.logger import get_logger

logger = get_logger("vector_store")
settings = get_settings()

_client_singleton = None
_embed_instance = None


def _get_chroma_client():
    """全局唯一 Chroma 持久化客户端"""
    global _client_singleton
    if _client_singleton is not None:
        return _client_singleton
    import chromadb  # 延迟导入

    Path(settings.CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
    _client_singleton = chromadb.PersistentClient(path=os.path.abspath(settings.CHROMA_PERSIST_DIR))
    logger.info("chroma_client_init", path=settings.CHROMA_PERSIST_DIR)
    return _client_singleton


def get_embeddings():
    """获取全局唯一 Embedding 实例（带缓存）"""
    global _embed_instance
    if _embed_instance is None:
        from .embeddings import OllamaEmbeddingCached

        _embed_instance = OllamaEmbeddingCached()
    return _embed_instance


def _lc_collection(collection_name: str):
    """返回 LangChain 封装的 Chroma（基于统一 client）"""
    try:
        from langchain_community.vectorstores import Chroma
    except ImportError as e:
        raise RuntimeError("缺少 langchain-community") from e

    return Chroma(
        client=_get_chroma_client(),
        collection_name=collection_name,
        embedding_function=get_embeddings(),
    )


def ensure_collection(collection_name: str) -> None:
    """确保 collection 存在（Chroma 首次 add_documents 会自动创建，这里做显式健康检查）"""
    client = _get_chroma_client()
    try:
        client.get_or_create_collection(collection_name)
    except Exception as e:
        logger.error("ensure_collection_failed", collection=collection_name, error=str(e))
        raise


def delete_collection(collection_name: str) -> None:
    client = _get_chroma_client()
    try:
        client.delete_collection(collection_name)
        logger.info("collection_deleted", collection=collection_name)
    except Exception as e:
        logger.warning("delete_collection_warn", collection=collection_name, error=str(e))


def add_documents(
    collection_name: str,
    documents: Iterable[Document],
) -> int:
    """将 Documents 写入向量库，返回实际写入条数"""
    docs: List[Document] = list(documents)
    if not docs:
        return 0
    # ChromaDB 要求 metadata 只能是 str/int/float/bool，不能有 None/list/dict
    # 先用 langchain-community 自带工具过滤复杂字段，再把剩余 None 统一替换为空字符串
    try:
        from langchain_community.vectorstores.utils import filter_complex_metadata
        docs = filter_complex_metadata(docs)
    except Exception:
        pass
    cleaned: List[Document] = []
    for d in docs:
        meta = {}
        for k, v in (d.metadata or {}).items():
            if v is None:
                meta[k] = ""
            elif isinstance(v, (str, int, float, bool)):
                meta[k] = v
            # 其它类型（list/dict 等）直接丢弃，避免 upsert 失败
        cleaned.append(Document(page_content=d.page_content, metadata=meta))
    vector_store = _lc_collection(collection_name)
    vector_store.add_documents(cleaned)
    logger.info("docs_added_to_collection", collection=collection_name, count=len(cleaned))
    return len(cleaned)


def delete_by_metadata(
    collection_name: str,
    *,
    doc_id: Optional[int] = None,
) -> int:
    """按 doc_id 元数据删除某文档的所有向量"""
    if doc_id is None:
        return 0
    client = _get_chroma_client()
    try:
        col = client.get_collection(collection_name)
    except Exception:
        return 0
    # 分页删除，防止一次性量太大
    total = 0
    offset = 0
    batch = 500
    while True:
        res = col.get(
            where={"doc_id": int(doc_id)},
            limit=batch,
            offset=offset,
            include=[],
        )
        ids = res.get("ids") or []
        if not ids:
            break
        col.delete(ids=ids)
        total += len(ids)
        if len(ids) < batch:
            break
    logger.info("docs_deleted_by_metadata", collection=collection_name, doc_id=doc_id, count=total)
    return total


def get_retriever(collection_name: str, k: int = 6):
    """获取 LangChain Retriever（MMR 去重）"""
    vector_store = _lc_collection(collection_name)
    return vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={"k": k, "fetch_k": k * 3, "lambda_mult": 0.6},
    )
