"""Pattern analysis orchestration."""

from __future__ import annotations

from predixai.vision.visual.pattern_analysis import PatternAnalysis
from predixai.vision.visual.pattern_analysis_validator import PatternAnalysisValidator


class PatternAnalyzer:
    def __init__(self) -> None:
        self.validator = PatternAnalysisValidator()

    def analyze(self, analysis: PatternAnalysis) -> PatternAnalysis:
        self.validator.validate(analysis)
        return analysis
