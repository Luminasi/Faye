"""多格式文档加载 + 切分，返回 LangChain Documents，metadata 携带 doc_id / doc_name / page 等"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import get_settings
from ..utils.logger import get_logger

logger = get_logger("file_loader")
settings = get_settings()

# 文本分块参数（电商 FAQ/规格书/售后政策都适合 400-600 左右的 chunk）
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 60


def get_extension(file_name: str) -> str:
    return os.path.splitext(file_name)[1].lstrip(".").lower()


def _read_text_with_fallback(path: str) -> str:
    """txt/md 等纯文本文件：多编码兜底读取"""
    last_err: Exception | None = None
    for enc in ("utf-8", "utf-8-sig", "gbk", "gb18030", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError as e:
            last_err = e
    raise RuntimeError(f"无法读取文本文件（已尝试 utf-8/gbk/gb18030 等）: {last_err}")


def load_and_split(
    file_path: str,
    *,
    file_name: str | None = None,
    doc_id: int,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[Document]:
    """
    加载单份文件并切分成 Documents，每个 Document 的 metadata 包含：
      doc_id: int, doc_name: str, file_type: str,
      chunk_index: int, page: int | None
    """
    path_obj = Path(file_path)
    if not path_obj.exists():
        raise FileNotFoundError(file_path)
    if not file_name:
        file_name = path_obj.name
    ext = get_extension(file_name) or get_extension(str(path_obj))
    raw_docs: List[Document] = []

    # === PDF ===
    if ext == "pdf":
        try:
            from langchain_community.document_loaders import PyPDFLoader
        except ImportError as e:
            raise RuntimeError("缺少 pypdf 依赖") from e
        loader = PyPDFLoader(str(path_obj))
        raw_docs = loader.load()
        for d in raw_docs:
            d.metadata["page"] = int(d.metadata.get("page", 0))
    # === DOCX ===
    elif ext in ("docx", "doc"):
        try:
            from langchain_community.document_loaders import Docx2txtLoader
        except ImportError as e:
            raise RuntimeError("缺少 python-docx/docx2txt 依赖") from e
        loader = Docx2txtLoader(str(path_obj))
        raw_docs = loader.load()
        for d in raw_docs:
            d.metadata["page"] = None
    # === HTML / HTM ===
    elif ext in ("html", "htm"):
        try:
            from langchain_community.document_loaders import BSHTMLLoader
        except ImportError as e:
            raise RuntimeError("缺少 unstructured/beautifulsoup4 依赖") from e
        loader = BSHTMLLoader(str(path_obj))
        raw_docs = loader.load()
        for d in raw_docs:
            d.metadata["page"] = None
    # === CSV ===
    elif ext == "csv":
        try:
            from langchain_community.document_loaders import CSVLoader
        except ImportError as e:
            raise RuntimeError("缺少 csv 依赖") from e
        # 尝试多种编码
        last_err = None
        for enc in ("utf-8-sig", "utf-8", "gbk"):
            try:
                loader = CSVLoader(str(path_obj), encoding=enc)
                raw_docs = loader.load()
                break
            except UnicodeDecodeError as e:
                last_err = e
        if last_err and not raw_docs:
            raise last_err
        for d in raw_docs:
            d.metadata["page"] = None
    # === Markdown ===
    elif ext in ("md", "markdown"):
        try:
            from langchain_community.document_loaders import UnstructuredMarkdownLoader
            loader = UnstructuredMarkdownLoader(str(path_obj))
            raw_docs = loader.load()
        except Exception:
            raw_docs = [Document(page_content=_read_text_with_fallback(str(path_obj)), metadata={"page": None})]
    # === TXT 及其他 ===
    else:
        raw_docs = [Document(page_content=_read_text_with_fallback(str(path_obj)), metadata={"page": None})]

    # 按 page 把 page 信息保存在 metadata，后续切分会继承
    for d in raw_docs:
        d.metadata.setdefault("doc_id", int(doc_id))
        d.metadata.setdefault("doc_name", file_name)
        d.metadata.setdefault("file_type", ext)
        d.metadata.setdefault("source", str(path_obj))

    # 切分（使用递归字符切分，保持语义完整）
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", ".", "?", "!", " ", ""],
        length_function=len,
    )
    chunks = splitter.split_documents(raw_docs)

    # 为每个 chunk 打上 chunk_index，清理 LangChain 写入的非 JSON 可序列化字段
    result: List[Document] = []
    for i, c in enumerate(chunks):
        content = (c.page_content or "").strip()
        if not content:
            continue
        md = dict(c.metadata or {})
        # 去掉无法 JSON 化的对象
        md = {k: v for k, v in md.items() if isinstance(v, (str, int, float, bool, type(None)))}
        md["doc_id"] = int(doc_id)
        md["doc_name"] = file_name
        md["chunk_index"] = i
        md["page"] = md.get("page")
        result.append(Document(page_content=content, metadata=md))

    logger.info("file_split_done", doc_id=doc_id, file=file_name, chunks=len(result))
    return result
