"""LLM 封装：根据配置自动选「DeepSeek 远程 API(ChatOpenAI兼容)」或「本地 Ollama」。

Two singletons are kept (streaming / non-streaming) exactly as before, so the
call-sites in rag_service.py do NOT need any change.

Embeddings intentionally remain on local Ollama (nomic-embed-text) so existing
Chroma collections built with nomic vectors keep working, no rebuild required.
"""
from __future__ import annotations

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from langchain_core.language_models.chat_models import BaseChatModel

from ..config import get_settings
from ..utils.logger import get_logger

settings = get_settings()
logger = get_logger("llm_factory")

_llm_singleton: BaseChatModel | None = None
_llm_streaming_singleton: BaseChatModel | None = None


def _build_openai_compatible(*, streaming: bool) -> BaseChatModel:
    """Remote API provider using LangChain's ChatOpenAI (works for any
    OpenAI-compatible endpoint like DeepSeek / SiliconFlow / Kimi / etc."""
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as e:
        raise RuntimeError(
            "缺少 langchain-openai 依赖，请先执行: pip install langchain-openai>=0.2"
        ) from e

    base_url = settings.OPENAI_COMPAT_BASE_URL
    api_key = settings.OPENAI_COMPAT_API_KEY
    model = settings.OPENAI_COMPAT_MODEL
    if not api_key:
        raise RuntimeError(
            "OPENAI_COMPAT_API_KEY 为空。请在 backend/.env 中配置真实的 API Key。\n"
            "例如（DeepSeek）：OPENAI_COMPAT_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxx"
        )
    if not model:
        raise RuntimeError("OPENAI_COMPAT_MODEL 为空，请在 .env 中配置 model id（如 deepseek-chat）。")

    logger.info(
        "llm_init_remote",
        base_url=base_url,
        model=model,
        streaming=streaming,
    )
    return ChatOpenAI(
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=settings.OPENAI_COMPAT_TEMPERATURE,
        top_p=settings.OPENAI_COMPAT_TOP_P,
        max_tokens=settings.OPENAI_COMPAT_MAX_TOKENS,
        timeout=settings.OPENAI_COMPAT_TIMEOUT_SECS,
        streaming=streaming,
    )


def _build_ollama(*, streaming: bool) -> BaseChatModel:
    """Local Ollama (kept as fallback / for offline use)."""
    try:
        from langchain_ollama import ChatOllama
    except ImportError as e:
        raise RuntimeError("缺少 langchain-ollama 依赖") from e
    logger.info(
        "llm_init_ollama",
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_LLM_MODEL,
        streaming=streaming,
    )
    return ChatOllama(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_LLM_MODEL,
        temperature=0.2,
        top_p=0.8,
        streaming=streaming,
        num_ctx=settings.OLLAMA_NUM_CTX,
        num_predict=2048,
        timeout=300.0,
    )


def _build_llm(*, streaming: bool) -> BaseChatModel:
    provider = (settings.LLM_PROVIDER or "openai_compatible").lower()
    if provider == "ollama":
        return _build_ollama(streaming=streaming)
    if provider == "openai_compatible":
        try:
            return _build_openai_compatible(streaming=streaming)
        except RuntimeError as e:
            # 远程 provider 配置不完整（缺 key / 缺 model 等）时自动回退到本地
            # Ollama，避免整个问答功能不可用。仅影响首次构建，日志可查。
            logger.warning(
                "llm_fallback_to_ollama",
                reason=str(e).splitlines()[0] if str(e) else "unknown",
            )
            return _build_ollama(streaming=streaming)
    raise RuntimeError(
        f"未知的 LLM_PROVIDER=[{provider}]。仅支持 ollama / openai_compatible。"
    )


def get_llm(streaming: bool = False) -> BaseChatModel:
    """获取 LLM 实例（可开关流式）。单例复用。"""
    global _llm_singleton, _llm_streaming_singleton
    if streaming:
        if _llm_streaming_singleton is None:
            _llm_streaming_singleton = _build_llm(streaming=True)
        return _llm_streaming_singleton
    if _llm_singleton is None:
        _llm_singleton = _build_llm(streaming=False)
    return _llm_singleton


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def ainvoke_with_retry(chain, input_data):
    """异步调用（带重试）"""
    return await chain.ainvoke(input_data)
