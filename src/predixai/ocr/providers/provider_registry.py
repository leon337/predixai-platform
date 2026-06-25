"""OCR provider registry."""

from __future__ import annotations

from predixai.ocr.providers.base_provider import BaseOCRProvider


class ProviderRegistry:
    """Register and expose available OCR providers."""

    def __init__(self) -> None:
        self._providers: dict[str, BaseOCRProvider] = {}

    @property
    def provider_names(self) -> tuple[str, ...]:
        """Return registered provider names."""
        return tuple(sorted(self._providers))

    def register(self, provider: BaseOCRProvider) -> None:
        """Register one OCR provider by name."""
        if provider.name in self._providers:
            raise ValueError(f"OCR provider already registered: {provider.name}")
        self._providers[provider.name] = provider

    def get(self, provider_name: str) -> BaseOCRProvider:
        """Return one registered OCR provider."""
        try:
            return self._providers[provider_name]
        except KeyError as exc:
            available = ", ".join(self.provider_names)
            raise ValueError(
                f"OCR provider not registered: {provider_name}. "
                f"Available providers: {available}"
            ) from exc
