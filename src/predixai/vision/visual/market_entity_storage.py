"""Storage definition for structural market entities."""

from __future__ import annotations

from pathlib import Path


class EntityStorage:
    """Define storage locations for future market entity persistence."""

    def __init__(self, root_path: str | Path = "data/market_entities") -> None:
        self.root_path = Path(root_path)

    def resolve(self, registry_id: str) -> Path:
        """Return the intended storage path for a registry identifier."""
        return self.root_path / f"{registry_id}.json"
