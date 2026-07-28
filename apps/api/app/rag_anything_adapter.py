from __future__ import annotations

import asyncio
from functools import partial
from pathlib import Path

from .config import settings
from .db import ROOT
from .errors import DomainError


def status() -> str:
    if not settings.rag_anything_enabled:
        return "disabled_by_configuration"
    if not settings.rag_anything_api_key:
        return "missing_model_configuration"
    try:
        import raganything  # noqa: F401
        import lightrag  # noqa: F401
        return "ready"
    except Exception as exc:
        return f"dependency_unavailable:{type(exc).__name__}"


async def _insert(course_id: str, blocks: list[dict]) -> None:
    from raganything import RAGAnything, RAGAnythingConfig
    from lightrag.llm.openai import openai_complete_if_cache, openai_embed
    from lightrag.utils import EmbeddingFunc

    workdir = ROOT / settings.rag_anything_workdir / course_id
    config = RAGAnythingConfig(working_dir=str(workdir), enable_image_processing=True, enable_table_processing=True, enable_equation_processing=True)
    llm = partial(openai_complete_if_cache, settings.rag_anything_llm_model, api_key=settings.rag_anything_api_key, base_url=settings.rag_anything_base_url or None)
    embed = EmbeddingFunc(embedding_dim=3072, max_token_size=8192, func=partial(openai_embed.func, model=settings.rag_anything_embedding_model, api_key=settings.rag_anything_api_key, base_url=settings.rag_anything_base_url or None))
    rag = RAGAnything(config=config, llm_model_func=llm, embedding_func=embed)
    content_list = [{"type": "text", "text": block["normalized_text"], "page_idx": block["page_number"] - 1} for block in blocks if block["normalized_text"]]
    await rag.insert_content_list(content_list=content_list, file_path=f"course-{course_id}-source-blocks", doc_id=f"course-{course_id}", display_stats=False)


def sync(course_id: str, blocks: list[dict]) -> str:
    current = status()
    if current != "ready":
        return current
    try:
        asyncio.run(_insert(course_id, blocks))
        return "indexed"
    except Exception as exc:
        raise DomainError("RAG_ANYTHING_SYNC_FAILED", "RAG-Anything could not index the source blocks.", {"reason": str(exc)}, 502) from exc
