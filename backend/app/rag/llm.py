"""本地 Ollama LLM 封装，带重试和超时"""
from __future__ import annotations

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from langchain_core.language_models.chat_models import BaseChatModel

from ..config import get_settings
from ..utils.logger import get_logger

settings = get_settings()
logger = get_logger("ollama_llm")


_llm_singleton: BaseChatModel | None = None
_llm_streaming_singleton: BaseChatModel | None = None


def _build_llm(*, streaming: bool) -> BaseChatModel:
    try:
        from langchain_ollama import ChatOllama
    except ImportError as e:
        raise RuntimeError("缺少 langchain-ollama 依赖") from e
    return ChatOllama(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_LLM_MODEL,
        temperature=0.2,
        top_p=0.8,
        streaming=streaming,
        # num_ctx 控制上下文窗口，本地 7B 一般 4k-8k 比较稳
        num_ctx=8192,
        num_predict=2048,
        # 增加超时，避免首次模型加载过慢
        timeout=300.0,
    )


def get_llm(streaming: bool = False) -> BaseChatModel:
    """获取 LLM 实例（可开关流式）"""
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
