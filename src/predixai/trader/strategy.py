from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class StrategyProfile:
    name: str
    default_expiration: int
    min_confidence: float
    expected_frequency_per_hour: int
    entry_type: str
    cancel_rule: str
    risk_level: str
    technical_filters: List[str]


class StrategySelector:
    def __init__(self):
        self.profiles: Dict[str, StrategyProfile] = {}

    def register(self, profile: StrategyProfile):
        self.profiles[profile.name] = profile

    def select(self, name: str) -> Optional[StrategyProfile]:
        return self.profiles.get(name)
