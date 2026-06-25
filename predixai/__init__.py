"""PredixAI source-layout command bootstrap."""

from __future__ import annotations

from pathlib import Path

__version__ = "0.1.0-foundation"

_SOURCE_PACKAGE = Path(__file__).resolve().parent.parent / "src" / "predixai"
if _SOURCE_PACKAGE.exists():
    __path__.insert(0, str(_SOURCE_PACKAGE))
