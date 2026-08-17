"""问答 API：非流式 + SSE 流式，消息持久化"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import ChatSession, User
from .. import schemas
from ..services import session_service as ss, rag_service as rs
from ..utils.logger import get_logger

router = APIRouter()
logger = get_logger("chat_api")


def _ensure_session(db: Session, session_id: int, user: User) -> ChatSession:
    return ss.get_session_of_user(db, session_id, user)


# ========== 非流式（备用） ==========
@router.post("/{session_id}", response_model=schemas.MessageInfo)
async def chat_sync(
    session_id: int,
    payload: schemas.ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sess = _ensure_session(db, session_id, current_user)

    # 1. 保存用户消息
    ss.create_message(db, sess, role="user", content=payload.question)

    # 2. 走 RAG（async：LLM 调用必须在 FastAPI 全局事件循环中 await，
    #    否则单例 ChatOllama 的 httpx 客户端会报 "Event loop is closed"）
    result = await rs.answer_question(
        db,
        sess,
        current_user,
        question=payload.question,
        kb_ids=payload.kb_ids,
    )

    # 3. 保存 AI 消息
    msg = ss.create_message(
        db,
        sess,
        role="assistant",
        content=result.answer,
        sources=result.sources,
        tokens_used=result.tokens_used,
        latency_ms=result.latency_ms,
        cache_hit=result.cache_hit,
    )
    return msg


# ========== SSE 流式 ==========
@router.post("/{session_id}/stream")
def chat_stream(
    session_id: int,
    payload: schemas.ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sess = _ensure_session(db, session_id, current_user)

    # 立即保存用户消息
    ss.create_message(db, sess, role="user", content=payload.question)

    question = payload.question
    kb_ids = payload.kb_ids

    # ------------------------------------------------------------------
    # 关键修复：所有需要 DB 会话 / ORM 对象（User、ChatSession、外部 db）
    # 的操作，必须在「同步路由函数返回前」完成，避免 FastAPI 关闭依赖
    # 注入的 DB session 后，异步生成器里触发 DetachedInstanceError。
    # 检索、缓存、授权等都在这里（同步块）做完，异步侧只跑 LLM 流式输出。
    # ------------------------------------------------------------------
    from operator import itemgetter as _itemgetter  # noqa: F811
    from ..services import rag_service as rs  # re-import for direct helpers

    cache_key = rs.make_query_key(question, kb_ids)
    cached_answer: str | None = None
    cache_hit = False
    final_sources: list[dict] = []
    final_docs: list = []  # langchain Document (NOT SQLA ORM, safe to cross)

    # 1) 缓存检查
    try:
        cached = rs.query_cache.get(cache_key)
        if cached and isinstance(cached, dict):
            cached_answer = cached.get("answer", "") or ""
            final_sources = list(cached.get("sources", []) or [])
            cache_hit = True
            logger.info("stream_cache_hit", q=question[:30], ans_chars=len(cached_answer))
    except Exception as e:
        logger.warning("stream_cache_check_failed", err=str(e))

    # 2) 没命中缓存 → 授权检查 + 并行检索（同步侧完成，避免异步侧用到 current_user/sess/db）
    if not cache_hit:
        docs = rs._retrieve_multi(db, current_user, question, kb_ids)  # type: ignore[attr-defined]
        final_docs = list(docs or [])
        final_sources = rs.docs_to_sources(final_docs)

    # 3) 纯数据解构成局部变量（都是 int/str/list/dict，没有 SQLA ORM）
    plain_sid = int(session_id)
    plain_q = str(question)
    plain_kb_ids = list(kb_ids) if kb_ids else None

    # ---------- 异步生成器：只依赖上面的纯数据 ----------
    async def event_generator():
        t0 = time.time()
        collected_parts: list[str] = []

        try:
            # ---- 先把 META 推给前端（citations 等） ----
            meta_payload = json.dumps(
                {"sources": final_sources, "cache_hit": cache_hit}, ensure_ascii=False
            )
            yield f"data: META:{meta_payload}\n\n"

            # ---- 缓存命中 → 以 chunk 形式模拟流式吐出 ----
            if cache_hit:
                ans = cached_answer or ""
                if not ans:
                    yield "data: [DONE]\n\n"
                else:
                    chunk_size = max(1, len(ans) // 30)
                    for i in range(0, len(ans), chunk_size):
                        chunk = ans[i : i + chunk_size]
                        collected_parts.append(chunk)
                        yield f"data: {chunk}\n\n"
                        await asyncio.sleep(0.01)
                    yield "data: [DONE]\n\n"
                return

            # ---- 无检索结果 → 直接给出兜底提示，不调 LLM ----
            if not final_docs:
                msg = "当前知识库中暂无相关资料，请换个问题或联系人工客服。"
                collected_parts.append(msg)
                yield f"data: {msg}\n\n"
                # 也写缓存
                try:
                    rs.query_cache.set(cache_key, {"answer": msg, "sources": [], "tokens_used": 0})
                except Exception:
                    pass
                yield "data: [DONE]\n\n"
                return

            # ---- 正常 RAG：LCEL chain 流式 astream ----
            chain = rs._build_chain(streaming=True)  # type: ignore[attr-defined]
            try:
                async for chunk in chain.astream({"question": plain_q, "docs": final_docs}):
                    if chunk:
                        collected_parts.append(chunk)
                        yield f"data: {chunk}\n\n"
            except Exception as e:
                logger.error("stream_llm_chain_failed", err=str(e))
                err_text = f"大模型调用失败：{e}"
                low = str(e).lower()
                if any(k in low for k in ("401", "authentication", "invalid api key", "unauthorized")):
                    err_text += "（提示：远程 API Key 无效/已过期，请在 backend/.env 检查 OPENAI_COMPAT_API_KEY，或将 LLM_PROVIDER 改为 ollama）"
                elif "connect" in low:
                    err_text += "（提示：无法连接模型服务，请检查网络/是否启动 Ollama）"
                yield f"data: [ERROR] {err_text}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error("stream_gen_error", err=type(e).__name__ + ":" + str(e))
            yield f"data: [ERROR] {e}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            # ---- 消息入库：一定使用全新的独立 SessionLocal() ----
            answer_text = "".join(collected_parts)
            lat_ms = int((time.time() - t0) * 1000)
            try:
                from ..database import SessionLocal

                new_db = SessionLocal()
                try:
                    sess2 = (
                        new_db.query(ChatSession).filter(ChatSession.id == plain_sid).first()
                    )
                    if sess2:
                        ss.create_message(
                            new_db,
                            sess2,
                            role="assistant",
                            content=answer_text,
                            sources=final_sources,
                            tokens_used=len(answer_text) // 3,
                            latency_ms=lat_ms,
                            cache_hit=cache_hit,
                        )
                    # 缓存写入（没命中时才写，命中的早就有了）
                    if not cache_hit and answer_text:
                        try:
                            rs.query_cache.set(
                                cache_key,
                                {
                                    "answer": answer_text,
                                    "sources": final_sources,
                                    "tokens_used": len(answer_text) // 3,
                                },
                            )
                        except Exception:
                            pass
                finally:
                    new_db.close()
            except Exception as ee:
                logger.error("persist_ai_msg_failed", err=str(ee))

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return StreamingResponse(event_generator(), headers=headers, media_type="text/event-stream")
