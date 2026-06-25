"""OCR provider selector."""

from __future__ import annotations

from predixai.ocr.providers.base_provider import BaseOCRProvider
from predixai.ocr.providers.provider_registry import ProviderRegistry


class ProviderSelector:
    """Select the configured OCR provider."""

    def __init__(self, registry: ProviderRegistry) -> None:
        self.registry = registry

    def select(self, provider_name: str) -> BaseOCRProvider:
        """Select one provider from the registry."""
        return self.registry.get(provider_name)
