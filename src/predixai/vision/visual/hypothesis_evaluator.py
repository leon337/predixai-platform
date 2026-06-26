"""Evaluate market hypotheses with structural rules."""

from __future__ import annotations

from predixai.vision.visual.hypothesis_score import HypothesisScore
from predixai.vision.visual.market_hypothesis import MarketHypotheses


class HypothesisEvaluator:
    def evaluate(self, hypotheses: MarketHypotheses) -> tuple[HypothesisScore, ...]:
        return tuple(
            HypothesisScore(
                value=1.0,
                rule="structural_hypothesis_rule",
                confidence=hypothesis.confidence,
                status="STRUCTURAL_READY",
            )
            for hypothesis in hypotheses.hypotheses
        )
