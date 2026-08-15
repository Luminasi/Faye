"""本地 Ollama Embedding 封装，带 LRU 缓存和重试"""
from __future__ import annotations

from typing import Any, Iterable, List

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from langchain_core.embeddings import Embeddings

from ..config import get_settings
from ..utils.cache import embed_cache, make_embed_key
from ..utils.logger import get_logger

settings = get_settings()
logger = get_logger("ollama_embed")


class OllamaEmbeddingCached(Embeddings):
    """封装 OllamaEmbeddings，增加本地缓存与重试机制，避免重复计算 Embedding"""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        use_cache: bool = True,
    ):
        try:
            from langchain_ollama import OllamaEmbeddings  # 延迟导入
        except ImportError as e:
            raise RuntimeError(
                "缺少 langchain-ollama 依赖，请先 pip install langchain-ollama"
            ) from e
        self._base_url = base_url or settings.OLLAMA_BASE_URL
        self._model = model or settings.OLLAMA_EMBED_MODEL
        self._impl = OllamaEmbeddings(base_url=self._base_url, model=self._model)
        self._use_cache = use_cache

    # --- 单条 Embed：带缓存和重试 ---
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _embed_one(self, text: str) -> List[float]:
        return self._impl.embed_query(text)

    def embed_query(self, text: str) -> List[float]:
        key = make_embed_key(text, self._model)
        if self._use_cache:
            cached = embed_cache.get(key)
            if cached is not None:
                return cached
        vec = self._embed_one(text)
        if self._use_cache:
            embed_cache.set(key, vec)
        return vec

    # --- 批量 Embed：按批大小切分，减少单次网络负载 ---
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        return self._impl.embed_documents(texts)

    def embed_documents(self, texts: List[str], batch_size: int = 64) -> List[List[float]]:
        # 先把命中缓存的挑出来，避免再走网络
        placeholders: List[Any] = [None] * len(texts)
        uncached_indices: List[int] = []
        uncached_texts: List[str] = []

        for i, t in enumerate(texts):
            if self._use_cache:
                key = make_embed_key(t, self._model)
                v = embed_cache.get(key)
                if v is not None:
                    placeholders[i] = v
                    continue
            uncached_indices.append(i)
            uncached_texts.append(t)

        if uncached_texts:
            computed: List[List[float]] = []
            for start in range(0, len(uncached_texts), batch_size):
                batch = uncached_texts[start : start + batch_size]
                try:
                    vecs = self._embed_batch(batch)
                except Exception as e:
                    logger.error("embed_batch_failed", batch_size=len(batch), error=str(e))
                    # 退化成逐条，便于定位哪条失败
                    vecs = []
                    for t in batch:
                        try:
                            vecs.append(self._embed_one(t))
                        except Exception as ee:
                            logger.error("embed_single_failed", text_preview=t[:40], error=str(ee))
                            raise ee
                computed.extend(vecs)

            # 回填：用 enumerate 保证 idx 与 computed 对齐
            for k, idx in enumerate(uncached_indices):
                vec = computed[k]
                placeholders[idx] = vec
                if self._use_cache:
                    key = make_embed_key(uncached_texts[k], self._model)
                    embed_cache.set(key, vec)

        # 兜底：理论上不会再有 None，若有则临时单条补算
        for i, v in enumerate(placeholders):
            if v is None:
                placeholders[i] = self.embed_query(texts[i])

        return placeholders

    def __call__(self, text: str) -> List[float]:
        return self.embed_query(text)
