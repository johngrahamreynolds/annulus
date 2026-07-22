from __future__ import annotations

import time

from annulus_core.config import load_settings

from annulus_retrieval.indexer import Indexer


def run_watch(*, interval_seconds: float, once: bool = False) -> None:
    settings = load_settings()
    indexer = Indexer(settings)
    while True:
        start = time.perf_counter()
        stats = indexer.index_incremental()
        elapsed = time.perf_counter() - start
        print(
            f"Index {stats.get('mode', 'incremental')}: "
            f"{stats.get('files', 0)} files, {stats.get('chunks', 0)} chunks, "
            f"{stats.get('removed', 0)} removed, {stats.get('skipped', 0)} skipped "
            f"({stats.get('strategy', '?')}) "
            f"in {elapsed:.2f}s -> {settings.resolve_index_db()}"
        )
        if once:
            return
        time.sleep(interval_seconds)


def main() -> None:
    settings = load_settings()
    interval = float(settings.retrieval.index_watch_interval_seconds)
    run_watch(interval_seconds=interval, once=True)


if __name__ == "__main__":
    main()
