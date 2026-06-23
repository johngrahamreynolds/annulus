from __future__ import annotations

import re

from annulus_core.config import AnnulusSettings
from annulus_core.types import RetrievedChunk

from annulus_retrieval.store import IndexStore


class Retriever:
    def __init__(self, settings: AnnulusSettings) -> None:
        self.settings = settings
        self.store = IndexStore(settings.resolve_index_db())

    def search(self, query: str, *, top_k: int | None = None) -> list[RetrievedChunk]:
        k = top_k or self.settings.agent.retrieval_top_k
        fts_query = _to_fts_query(query)
        if not fts_query:
            return []
        rows = self.store.search(fts_query, limit=k)
        return [
            RetrievedChunk(
                path=row.path,
                start_line=row.start_line,
                end_line=row.end_line,
                content=row.content,
                score=1.0,
            )
            for row in rows
        ]

    def stats(self) -> dict[str, int]:
        return self.store.stats()


def _to_fts_query(query: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9_]+", query)
    if not tokens:
        return ""
    return " OR ".join(f'"{token}"' for token in tokens[:12])
