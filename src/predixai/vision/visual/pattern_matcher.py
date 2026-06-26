"""Match structural market patterns using deterministic rules."""

from __future__ import annotations

from predixai.vision.visual.market_structure import MarketStructure
from predixai.vision.visual.pattern import Patterns
from predixai.vision.visual.pattern_builder import PatternBuilder


class PatternMatcher:
    """Deterministically match patterns from market structure metadata."""

    def __init__(self) -> None:
        self.builder = PatternBuilder()

    def match(self, market_structure: MarketStructure) -> Patterns | None:
        """Return patterns when structural criteria are satisfied."""
        if market_structure.entity_count <= 0:
            return None
        return self.builder.build(market_structure)
