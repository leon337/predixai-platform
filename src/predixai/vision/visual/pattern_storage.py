"""Storage metadata for structural patterns."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PatternStorage:
    """Path metadata for future pattern persistence."""

    base_directory: str
    registry_directory: str
    benchmark_directory: str

    def to_dict(self) -> dict[str, str]:
        return {
            "base_directory": self.base_directory,
            "registry_directory": self.registry_directory,
            "benchmark_directory": self.benchmark_directory,
        }
