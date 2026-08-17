"""RAG 问答服务层：多库检索、LCEL Chain、流式/非流式调用、缓存"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import AsyncIterable, List, Optional

from fastapi import HTTPException
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import ChatSession, User, UserRole
from ..services import knowledge_service as ks
from ..utils.cache import make_query_key, query_cache
from ..utils.logger import get_logger

from ..rag.llm import get_llm
from ..rag.prompts import build_rag_prompt, format_docs_for_context
from ..rag import vector_store as vs

settings = get_settings()
logger = get_logger("rag_service")


def _looks_like_auth_error(exc: Exception) -> bool:
    """401 / Authentication / invalid api key 等关键词 → 远程 key 配置问题"""
    text = f"{type(exc).__name__}: {exc}".lower()
    return any(k in text for k in ("401", "authentication", "invalid api key", "unauthorized"))


@dataclass
class RAGResult:
    answer: str
    sources: list[dict]  # 引用来源列表
    latency_ms: int
    cache_hit: bool
    tokens_used: int = 0


# ----------- 多库合并检索 -----------

def _get_authorized_collections(
    db: Session, user: User, kb_ids: Optional[List[int]] = None
) -> list[tuple[str, int]]:
    """返回 [(collection_name, kb_id)]。校验所选 kb 必须在用户授权范围"""
    authorized = ks.list_user_authorized_kbs(db, user)
    auth_ids = {kb.id for kb in authorized}
    target_ids: List[int]
    if kb_ids:
        invalid = [x for x in kb_ids if x not in auth_ids]
        if invalid:
            raise HTTPException(403, detail=f"无权访问知识库: {invalid}")
        target_ids = kb_ids
    else:
        target_ids = list(auth_ids)
    id_to_col = {kb.id: kb.collection_name for kb in authorized}
    return [(id_to_col[i], i) for i in target_ids if i in id_to_col]


def _retrieve_multi(
    db: Session, user: User, question: str, kb_ids: Optional[List[int]], k: int = 6
) -> List[Document]:
    """从多个 collection 并行检索并合并去重（按内容前60字 hash 去重），最终保留 top_k 条"""
    collections = _get_authorized_collections(db, user, kb_ids)
    if not collections:
        return []
    all_docs: List[Document] = []
    failed = 0
    for col_name, kb_id in collections:
        try:
            ret = vs.get_retriever(col_name, k=k)
            docs = ret.invoke(question) or []
            for d in docs:
                d.metadata.setdefault("kb_id", kb_id)
            all_docs.extend(docs)
        except Exception as e:
            failed += 1
            logger.error("retrieve_collection_failed", collection=col_name, error=str(e))
    # 所有集合检索都失败（通常是 Ollama 嵌入服务没启动）时，不能静默当成
    # "知识库没有资料"，否则用户会误以为系统坏了/没数据。
    if failed == len(collections) and not all_docs:
        raise HTTPException(
            503,
            detail=(
                "向量检索失败：无法连接本地嵌入模型（Ollama）。"
                "请确认 Ollama 已启动（右下角托盘图标 / 运行 ollama serve），"
                "并已执行 ollama pull nomic-embed-text"
            ),
        )
    # 去重：基于内容指纹
    seen: set[str] = set()
    unique: List[Document] = []
    for d in all_docs:
        sig = (d.page_content or "").strip()[:100]
        if sig in seen:
            continue
        seen.add(sig)
        unique.append(d)
    # 这里的 docs 没有显式 score（Retriever 返回已排序），按返回顺序截断
    return unique[: k * 2 if len(collections) > 1 else k]


# ----------- 来源提取 -----------

def docs_to_sources(docs: List[Document], max_per_answer: int = 5) -> list[dict]:
    """从检索到的 docs 生成前端可展示的 sources 列表（与 LLM 返回解耦）"""
    out = []
    for i, d in enumerate(docs):
        if i >= max_per_answer:
            break
        md = d.metadata or {}
        snippet = (d.page_content or "").strip()
        if len(snippet) > 260:
            snippet = snippet[:260] + "…"
        out.append({
            "doc_id": md.get("doc_id"),
            "doc_name": md.get("doc_name") or md.get("source") or "未知来源",
            "page": md.get("page"),
            "chunk_index": md.get("chunk_index"),
            "snippet": snippet,
        })
    return out


# ----------- 构建 LCEL Chain -----------

def _build_chain(*, streaming: bool):
    prompt = build_rag_prompt()
    llm = get_llm(streaming=streaming)
    chain = (
        {
            "context": RunnableLambda(lambda x: format_docs_for_context(x["docs"])),
            "question": itemgetter_question(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain


def itemgetter_question():
    """等价于 itemgetter('question')，返回一个 Runnable"""
    return RunnableLambda(lambda dic: dic["question"])


# ----------- 核心问答 -----------

async def answer_question(
    db: Session,
    sess: ChatSession,
    user: User,
    *,
    question: str,
    kb_ids: Optional[List[int]] = None,
    use_cache: bool = True,
) -> RAGResult:
    """非流式：用于回退或缓存写入。

    注意：这是 async def —— LLM 调用必须 await。LangChain 的 ChatOllama
    (langchain_ollama) 底层 httpx 异步客户端绑定在「创建时的」事件循环上，
    而 get_llm() 返回单例，所以绝不能像以前那样在同步函数里
    asyncio.new_event_loop() + loop.close()（第二次调用就会报
    "Event loop is closed"）。统一让 FastAPI 的 async 端点直接 await 即可。
    """
    t0 = time.time()

    # 1. 缓存检查
    cache_key = make_query_key(question, kb_ids)
    if use_cache:
        cached = query_cache.get(cache_key)
        if cached and isinstance(cached, dict):
            lat = int((time.time() - t0) * 1000)
            logger.info("query_cache_hit", user_id=user.id, q=question[:30])
            return RAGResult(
                answer=cached.get("answer", ""),
                sources=cached.get("sources", []),
                latency_ms=lat,
                cache_hit=True,
                tokens_used=cached.get("tokens_used", 0),
            )

    # 2. 检索
    docs = _retrieve_multi(db, user, question, kb_ids)
    sources = docs_to_sources(docs)

    # 3. 无资料提示：不用调 LLM，直接返回
    if not docs:
        answer = "当前知识库中暂无相关资料，请换个问题或联系人工客服。"
        lat = int((time.time() - t0) * 1000)
        return RAGResult(answer=answer, sources=[], latency_ms=lat, cache_hit=False)

    # 4. LCEL 调用（在调用方的事件循环里 await；调用方必须是 async 端点）
    chain = _build_chain(streaming=False)
    try:
        answer = await chain.ainvoke({"question": question, "docs": docs})
    except Exception as e:
        logger.error("llm_invoke_failed", error=str(e))
        detail = f"大模型调用失败: {e}"
        if _looks_like_auth_error(e):
            detail += "（提示：远程 API Key 无效/已过期，请在 backend/.env 中检查 OPENAI_COMPAT_API_KEY，或将 LLM_PROVIDER 改为 ollama 使用本地模型）"
        elif "connect" in str(e).lower() and settings.LLM_PROVIDER == "openai_compatible":
            detail += "（提示：无法连接远程 API，请检查网络；或改用本地模型：LLM_PROVIDER=ollama）"
        raise HTTPException(500, detail=detail)

    answer = (answer or "").strip()
    lat = int((time.time() - t0) * 1000)
    result = RAGResult(
        answer=answer,
        sources=sources,
        latency_ms=lat,
        cache_hit=False,
        tokens_used=len(answer) // 3,  # 本地 Ollama token 使用量不好精确取，用粗估算
    )

    # 5. 写缓存
    if use_cache:
        query_cache.set(
            cache_key,
            {"answer": result.answer, "sources": result.sources, "tokens_used": result.tokens_used},
        )
    return result


async def answer_question_stream(
    db: Session,
    sess: ChatSession,
    user: User,
    *,
    question: str,
    kb_ids: Optional[List[int]] = None,
    use_cache: bool = True,
) -> AsyncIterable[tuple[str, str]]:
    """
    流式生成器，yield (event_type, payload)
      - 'meta'  : JSON 字符串，包含 sources 等元信息
      - 'token' : 单段文本 chunk
      - 'done'  : 空
    """
    t0 = time.time()
    cache_key = make_query_key(question, kb_ids)

    # 缓存命中：一次性 yield 文本（以 token 事件模拟流式）
    if use_cache:
        cached = query_cache.get(cache_key)
        if cached and isinstance(cached, dict):
            answer = cached.get("answer", "") or ""
            sources = cached.get("sources", [])
            yield "meta", __import__("json").dumps({"sources": sources, "cache_hit": True}, ensure_ascii=False)
            chunk_size = max(1, len(answer) // 30)
            for i in range(0, len(answer), chunk_size):
                yield "token", answer[i : i + chunk_size]
                await asyncio.sleep(0.01)
            yield "done", ""
            return

    # 检索
    docs = _retrieve_multi(db, user, question, kb_ids)
    sources = docs_to_sources(docs)
    yield "meta", __import__("json").dumps({"sources": sources, "cache_hit": False}, ensure_ascii=False)

    if not docs:
        msg = "当前知识库中暂无相关资料，请换个问题或联系人工客服。"
        yield "token", msg
        yield "done", ""
        # 也写缓存
        if use_cache:
            query_cache.set(cache_key, {"answer": msg, "sources": [], "tokens_used": 0})
        return

    # LCEL 流式
    chain = _build_chain(streaming=True)
    full_answer = []
    try:
        async for chunk in chain.astream({"question": question, "docs": docs}):
            if chunk:
                full_answer.append(chunk)
                yield "token", chunk
    except Exception as e:
        logger.error("llm_stream_failed", error=str(e))
        err_msg = f"[大模型调用失败] {e}"
        yield "token", err_msg
        yield "done", ""
        return

    yield "done", ""

    # 写入缓存（后台异步也可以，这里同步做）
    answer_text = "".join(full_answer)
    if use_cache and answer_text:
        query_cache.set(
            cache_key,
            {
                "answer": answer_text,
                "sources": sources,
                "tokens_used": len(answer_text) // 3,
                "latency_ms": int((time.time() - t0) * 1000),
            },
        )
