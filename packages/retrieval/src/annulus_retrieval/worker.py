from __future__ import annotations

import time

from annulus_core.config import load_settings

from annulus_retrieval.indexer import Indexer


def main() -> None:
    settings = load_settings()
    indexer = Indexer(settings)
    start = time.perf_counter()
    stats = indexer.index_all(rebuild=True)
    elapsed = time.perf_counter() - start
    print(
        f"Indexed {stats['files']} files, {stats['chunks']} chunks in {elapsed:.2f}s "
        f"-> {settings.resolve_index_db()}"
    )


if __name__ == "__main__":
    main()
