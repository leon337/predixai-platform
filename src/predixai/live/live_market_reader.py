"""Read basic live market fields from OCR text."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
import re

from predixai.live.live_market_reading import LiveMarketReading


@dataclass(frozen=True)
class FieldNormalizationResult:
    field_id: str
    raw_text: str
    normalized_text: str
    valid: bool
    reasons: tuple[str, ...] = ()

    def to_dict(self, *, redact_raw_text: bool = False) -> dict[str, object]:
        return {
            "FIELD_ID": self.field_id,
            "RAW_TEXT": "REDACTED_LOCAL_VALUE" if redact_raw_text else self.raw_text,
            "NORMALIZED_TEXT": self.normalized_text,
            "FIELD_VALID": "YES" if self.valid else "NO",
            "REASONS": self.reasons,
        }


class LiveMarketReader:
    def normalize_field(self, field_id: str, raw_text: str) -> FieldNormalizationResult:
        """Normalize one isolated authorized crop without cross-field fallbacks."""
        normalized_id = field_id.strip().upper()
        handlers = {
            "ASSET": self._normalize_asset,
            "PRICE": self._normalize_price,
            "PAYOUT": self._normalize_payout,
            "PRICE_SOURCE_BROWSER_TAB": self._normalize_price_source_browser_tab,
            "COUNTDOWN": self._normalize_countdown,
            "TIMEFRAME": self._normalize_timeframe,
            "ENTRY_VALUE": lambda text: self._normalize_numeric("ENTRY_VALUE", text),
            "DURATION": self._normalize_duration,
            "PROFIT_DISPLAY": lambda text: self._normalize_numeric("PROFIT_DISPLAY", text),
            "ACCOUNT_BALANCE": lambda text: self._normalize_numeric("ACCOUNT_BALANCE", text),
            "ACCOUNT_TYPE": self._normalize_account_type,
            "PROFITABILITY_FILTER": self._normalize_profitability_filter,
            "OPENING_TIME": lambda text: self._normalize_clock("OPENING_TIME", text),
        }
        try:
            handler = handlers[normalized_id]
        except KeyError as exc:
            raise ValueError(f"unsupported calibrated field: {normalized_id}") from exc
        return handler(raw_text or "")

    def read(self, ocr_text: str, ocr_confidence: float, timeframe: str) -> LiveMarketReading:
        text = ocr_text or ""

        asset = self._match(
            text,
            [
                r"\bLATAM Index\b",
                r"\b[A-Z]{3,6}/[A-Z]{3,6}(?:\s+OTC)?\b",
                r"\b[A-Z]{3,6}\b",
            ],
        )
        price = self._match(
            text,
            [
                r"Price[:\s]*(\d+[.,]\d+)",
                r"Window_Title:.*?\b(\d+[.,]\d+)\b",
                r"\b\d+[.,]\d+\b",
            ],
        )
        time_value = self._match(text, [r"\b\d{2}:\d{2}(?::\d{2})?\b"])
        balance = self._match(
            text,
            [
                r"Balance[:\s]*((?:R\$|RS|D)\s*\d+(?:[.,]\d+)*)",
                r"\b((?:R\$|RS|D)\s*\d+(?:[.,]\d+)*)\b",
                r"\bsaldo\b",
            ],
        )
        payout = self._match(
            text,
            [
                r"Payout[:\s]*(\d+%)",
                r"\b(\d+%)\b",
            ],
        )
        trade_value = self._match(
            text,
            [
                r"Trade[_\s-]*Value[:\s]*((?:R\$|RS|D)\s*\d+(?:[.,]\d+)*)",
                r"\b((?:R\$|RS|D)\s*\d+(?:[.,]\d+)*)\b",
            ],
        )
        duration = self._match(
            text,
            [
                r"Duration[:\s]*(\d+\s*min\.?)",
                r"\b(\d+\s*min\.?)\b",
            ],
        )

        return LiveMarketReading(
            asset=asset,
            price=price,
            time=time_value,
            balance=balance,
            payout=payout,
            timeframe=timeframe if timeframe else "UNKNOWN",
            confidence=ocr_confidence,
            source_ocr_text=text,
            trade_value=trade_value,
            duration=duration,
            metadata={
                "unknown_fields": [
                    key
                    for key, value in {
                        "asset": asset,
                        "price": price,
                        "balance": balance,
                        "payout": payout,
                        "trade_value": trade_value,
                        "duration": duration,
                        "timeframe": timeframe,
                    }.items()
                    if value == "UNKNOWN"
                ]
            },
        )

    def _match(self, text: str, patterns: list[str]) -> str:
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = [value for value in match.groups() if value]
                value = groups[0] if groups else match.group(0)
                return value.strip().replace("RS", "R$")
        return "UNKNOWN"

    @staticmethod
    def _clean(text: str) -> str:
        return " ".join(text.replace("\n", " ").split())

    def _normalize_asset(self, raw_text: str) -> FieldNormalizationResult:
        clean = self._clean(raw_text)
        matches: list[str] = []
        patterns = (
            r"\b[A-Z0-9]{2,12}/[A-Z0-9]{2,12}(?:\s+OTC)?\b",
            r"\b[A-Z][A-Z0-9]*(?:\s+[A-Z][A-Z0-9]*){0,3}\s+OTC\b",
            r"\b[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9]*(?:\s+[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9]*){0,3}\s+Index\b",
        )
        for pattern in patterns:
            matches.extend(match.group(0) for match in re.finditer(pattern, clean, re.IGNORECASE))
        unique = tuple(dict.fromkeys(" ".join(item.split()).upper() for item in matches))
        if len(unique) != 1:
            reason = "ASSET_NOT_FOUND" if not unique else "MULTIPLE_ASSETS"
            return FieldNormalizationResult("ASSET", raw_text, "", False, (reason,))
        return FieldNormalizationResult("ASSET", raw_text, unique[0], True)

    def _normalize_price(self, raw_text: str) -> FieldNormalizationResult:
        clean = self._clean(raw_text)
        matches = re.findall(r"(?<!\d)\d+(?:[.,]\d+)?(?!\d)", clean)
        if len(matches) != 1:
            reason = "PRICE_NOT_FOUND" if not matches else "MULTIPLE_PRICE_VALUES"
            return FieldNormalizationResult("PRICE", raw_text, "", False, (reason,))
        value = matches[0]
        if value.count(".") + value.count(",") > 1:
            return FieldNormalizationResult("PRICE", raw_text, "", False, ("AMBIGUOUS_PRICE",))
        return FieldNormalizationResult("PRICE", raw_text, value.replace(",", "."), True)

    def _normalize_price_source_browser_tab(
        self,
        raw_text: str,
    ) -> FieldNormalizationResult:
        """Normalize exactly one price captured from the active browser tab."""
        price = self._normalize_price(raw_text)

        if not price.valid:
            return FieldNormalizationResult(
                "PRICE_SOURCE_BROWSER_TAB",
                raw_text,
                "",
                False,
                tuple(f"TAB_{reason}" for reason in price.reasons),
            )

        return FieldNormalizationResult(
            "PRICE_SOURCE_BROWSER_TAB",
            raw_text,
            price.normalized_text,
            True,
        )

    def _normalize_payout(self, raw_text: str) -> FieldNormalizationResult:
        clean = self._clean(raw_text)
        matches = re.findall(r"(?<!\d)(\d+(?:[.,]\d+)?)\s*%", clean)
        if len(matches) != 1:
            reason = "PAYOUT_NOT_FOUND" if not matches else "MULTIPLE_PAYOUT_VALUES"
            return FieldNormalizationResult("PAYOUT", raw_text, "", False, (reason,))
        number_text = matches[0].replace(",", ".")
        value = float(number_text)
        if not 0.0 <= value <= 100.0:
            return FieldNormalizationResult("PAYOUT", raw_text, "", False, ("PAYOUT_OUT_OF_RANGE",))
        return FieldNormalizationResult("PAYOUT", raw_text, f"{number_text}%", True)

    def _normalize_clock(self, field_id: str, raw_text: str) -> FieldNormalizationResult:
        clean = self._clean(raw_text)
        matches = re.findall(r"(?<!\d)(\d{2}:\d{2}(?::\d{2})?)(?!\d)", clean)
        if len(matches) != 1:
            reason = f"{field_id}_NOT_FOUND" if not matches else f"MULTIPLE_{field_id}_VALUES"
            return FieldNormalizationResult(field_id, raw_text, "", False, (reason,))
        value = matches[0]
        parts = [int(part) for part in value.split(":")]
        try:
            time(parts[0], parts[1], parts[2] if len(parts) == 3 else 0)
        except ValueError:
            return FieldNormalizationResult(field_id, raw_text, "", False, (f"INVALID_{field_id}",))
        return FieldNormalizationResult(field_id, raw_text, value, True)

    def _normalize_countdown(self, raw_text: str) -> FieldNormalizationResult:
        clean = self._clean(raw_text)
        matches = re.findall(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)", clean)
        if len(matches) != 1:
            reason = "COUNTDOWN_NOT_FOUND" if not matches else "MULTIPLE_COUNTDOWN_VALUES"
            return FieldNormalizationResult("COUNTDOWN", raw_text, "", False, (reason,))
        minutes, seconds = (int(value) for value in matches[0])
        if seconds >= 60:
            return FieldNormalizationResult("COUNTDOWN", raw_text, "", False, ("INVALID_COUNTDOWN",))
        return FieldNormalizationResult("COUNTDOWN", raw_text, f"{minutes:02d}:{seconds:02d}", True)

    def validate_countdown_sequence(self, raw_values: tuple[str, ...]) -> FieldNormalizationResult:
        """Accept decreasing countdown frames and one explicit near-zero reset."""
        if len(raw_values) < 3:
            return FieldNormalizationResult(
                "COUNTDOWN_SEQUENCE", " ".join(raw_values), "", False, ("COUNTDOWN_SEQUENCE_TOO_SHORT",)
            )
        seconds_values: list[int] = []
        normalized_values: list[str] = []
        for raw_value in raw_values:
            normalized = self._normalize_countdown(raw_value)
            if not normalized.valid:
                return FieldNormalizationResult(
                    "COUNTDOWN_SEQUENCE", " ".join(raw_values), "", False, normalized.reasons
                )
            minutes, seconds = (int(value) for value in normalized.normalized_text.split(":"))
            seconds_values.append(minutes * 60 + seconds)
            normalized_values.append(normalized.normalized_text)
        for previous, current in zip(seconds_values, seconds_values[1:]):
            if current < previous:
                continue
            if previous <= 2 and current > previous:
                continue
            return FieldNormalizationResult(
                "COUNTDOWN_SEQUENCE",
                " ".join(raw_values),
                "",
                False,
                ("COUNTDOWN_NOT_DECREASING_OR_EXPLICIT_RESET",),
            )
        return FieldNormalizationResult(
            "COUNTDOWN_SEQUENCE",
            " ".join(raw_values),
            "|".join(normalized_values),
            True,
        )

    def _normalize_timeframe(self, raw_text: str) -> FieldNormalizationResult:
        clean = self._clean(raw_text)
        matches = re.findall(r"(?<!\w)(\d{1,4})\s*([smhd])(?!\w)", clean, re.IGNORECASE)
        if len(matches) != 1:
            reason = "TIMEFRAME_NOT_FOUND" if not matches else "MULTIPLE_TIMEFRAMES"
            return FieldNormalizationResult("TIMEFRAME", raw_text, "", False, (reason,))
        amount, unit = matches[0]
        if int(amount) <= 0:
            return FieldNormalizationResult("TIMEFRAME", raw_text, "", False, ("INVALID_TIMEFRAME",))
        return FieldNormalizationResult("TIMEFRAME", raw_text, f"{int(amount)}{unit.lower()}", True)

    def _normalize_numeric(self, field_id: str, raw_text: str) -> FieldNormalizationResult:
        clean = self._clean(raw_text)
        matches = re.findall(r"(?<![\w\d])(?:R\$\s*)?[-+]?\s*\d+(?:[.,]\d+)*(?![\w\d])", clean, re.IGNORECASE)
        if len(matches) != 1:
            reason = f"{field_id}_NOT_FOUND" if not matches else f"MULTIPLE_{field_id}_VALUES"
            return FieldNormalizationResult(field_id, raw_text, "", False, (reason,))
        token = re.sub(r"R\$\s*", "", matches[0], flags=re.IGNORECASE).replace(" ", "")
        sign = ""
        if token[:1] in {"+", "-"}:
            sign, token = token[0], token[1:]
        if "." in token and "," in token:
            if re.fullmatch(r"\d{1,3}(?:\.\d{3})+,\d+", token) is None:
                return FieldNormalizationResult(field_id, raw_text, "", False, (f"AMBIGUOUS_{field_id}_FORMAT",))
            normalized = token.replace(".", "").replace(",", ".")
        elif "," in token:
            if token.count(",") != 1:
                return FieldNormalizationResult(field_id, raw_text, "", False, (f"AMBIGUOUS_{field_id}_FORMAT",))
            normalized = token.replace(",", ".")
        elif token.count(".") > 1:
            if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", token) is None:
                return FieldNormalizationResult(field_id, raw_text, "", False, (f"AMBIGUOUS_{field_id}_FORMAT",))
            normalized = token.replace(".", "")
        else:
            normalized = token
        return FieldNormalizationResult(field_id, raw_text, f"{sign}{normalized}", True)

    def _normalize_duration(self, raw_text: str) -> FieldNormalizationResult:
        clean = self._clean(raw_text)
        matches = re.findall(
            r"(?<!\d)(\d+)\s*(seg(?:undos?)?\.?|min(?:utos?)?\.?|s|m)(?!\w)",
            clean,
            re.IGNORECASE,
        )
        if len(matches) != 1:
            reason = "DURATION_NOT_FOUND" if not matches else "MULTIPLE_DURATIONS"
            return FieldNormalizationResult("DURATION", raw_text, "", False, (reason,))
        amount, unit = matches[0]
        normalized_unit = "s" if unit.casefold().startswith("s") else "m"
        return FieldNormalizationResult("DURATION", raw_text, f"{int(amount)}{normalized_unit}", True)

    def _normalize_account_type(self, raw_text: str) -> FieldNormalizationResult:
        clean = self._clean(raw_text).upper()
        has_demo = re.search(r"\b(?:CONTA\s+)?DEMO\b", clean) is not None
        has_real = re.search(r"\b(?:CONTA\s+)?REAL\b", clean) is not None
        if has_demo and has_real:
            return FieldNormalizationResult("ACCOUNT_TYPE", raw_text, "", False, ("ACCOUNT_TYPE_AMBIGUOUS",))
        if not has_demo and not has_real:
            return FieldNormalizationResult("ACCOUNT_TYPE", raw_text, "", False, ("ACCOUNT_TYPE_NOT_FOUND",))
        return FieldNormalizationResult("ACCOUNT_TYPE", raw_text, "DEMO" if has_demo else "REAL", True)

    def _normalize_profitability_filter(self, raw_text: str) -> FieldNormalizationResult:
        clean = self._clean(raw_text)
        if clean.casefold() in {"todas", "todos", "all"}:
            return FieldNormalizationResult("PROFITABILITY_FILTER", raw_text, "ALL", True)
        payout = self._normalize_payout(clean)
        if not payout.valid:
            return FieldNormalizationResult("PROFITABILITY_FILTER", raw_text, "", False, payout.reasons)
        return FieldNormalizationResult("PROFITABILITY_FILTER", raw_text, payout.normalized_text, True)
