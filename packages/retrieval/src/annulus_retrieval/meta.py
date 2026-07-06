from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class IndexMeta:
    last_commit: str | None = None
    strategy: str = "git"
    indexed_at: str | None = None

    @classmethod
    def load(cls, path: Path) -> IndexMeta | None:
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        if not isinstance(data, dict):
            return None
        return cls(
            last_commit=data.get("last_commit"),
            strategy=str(data.get("strategy") or "git"),
            indexed_at=data.get("indexed_at"),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")
