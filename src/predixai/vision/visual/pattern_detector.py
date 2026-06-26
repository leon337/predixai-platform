"""Detect structural patterns from market structures."""

from __future__ import annotations

from predixai.vision.visual.market_structure import MarketStructure
from predixai.vision.visual.pattern import Patterns
from predixai.vision.visual.pattern_builder import PatternBuilder
from predixai.vision.visual.pattern_matcher import PatternMatcher


class PatternDetector:
    """Detect patterns using deterministic structural rules."""

    def __init__(self) -> None:
        self.matcher = PatternMatcher()
        self.builder = PatternBuilder()

    def detect(self, market_structure: MarketStructure) -> Patterns:
        """Detect structural patterns without AI."""
        matched_patterns = self.matcher.match(market_structure)
        if matched_patterns is not None:
            return matched_patterns
        return self.builder.build(market_structure)
