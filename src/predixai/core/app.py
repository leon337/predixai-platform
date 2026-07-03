"""Application bootstrap for the PredixAI foundation."""

from __future__ import annotations

import json
import re
import importlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import perf_counter
from time import sleep

from predixai.capture import CaptureEngine, CaptureEngineStatus, SnapshotMetadata
from predixai.core.config import AppConfig, load_config
from predixai.core.events import EventRegistry
from predixai.core.logger import (
    log_broker_window_state,
    configure_logger,
    log_capture_engine,
    log_candle_snapshot,
    log_candle_statistics,
    log_error,
    log_field_extraction_result,
    log_field_location_map,
    log_image_buffer,
    log_live_capture_tick,
    log_live_candle_benchmark,
    log_live_market_reading,
    log_live_session,
    log_live_validation_benchmark,
    log_live_validation_report,
    log_manual_snapshot,
    log_market_benchmark,
    log_market_elements,
    log_market_entities,
    log_market_entity_validation,
    log_market_entity_registry,
    log_market_scene,
    log_market_structure,
    log_market_structure_benchmark,
    log_market_structure_validation,
    log_pattern_benchmark,
    log_pattern_analysis,
    log_pattern_analysis_benchmark,
    log_pattern_analysis_validation,
    log_pattern_classification,
    log_pattern_context,
    log_hypothesis_evaluator,
    log_intelligence_benchmark,
    log_intelligence_context,
    log_intelligence_context_validation,
    log_intelligence_snapshot,
    log_market_hypothesis,
    log_market_hypothesis_registry,
    log_pattern_detector,
    log_pattern_registry,
    log_pattern_scene,
    log_pattern_validation,
    log_signal,
    log_signal_registry,
    log_signal_score,
    log_signal_validation,
    log_ocr_pipeline,
    log_ocr_parser,
    log_perception,
    log_price_region_mapping,
    log_region_text_mapping,
    log_region_mapping_finished,
    log_region_mapping_started,
    log_region_registry,
    log_roi_crop,
    log_roi_crop_export,
    log_roi_registry,
    log_screen_elements,
    log_screen_layout,
    log_screen_object_registry,
    log_semantic_benchmark,
    log_semantic_elements,
    log_semantic_label_mapping,
    log_semantic_registry,
    log_semantic_scene,
    log_startup,
    log_structured_ocr,
    log_time_region_mapping,
    log_visual_benchmark,
    log_visual_scene,
    log_visual_scene_benchmark,
    log_visual_snapshot,
    log_vision_frame,
    log_strategy_readiness_benchmark,
    log_strategy_readiness_snapshot,
)
from predixai.ocr import OCREngine
from predixai.live import (
    LiveCalibrationEngine,
    CandleSnapshotBuilder,
    CandleStatisticsBuilder,
    BrokerWindowDetector,
    FieldExtractor,
    FieldLocator,
    LiveCandleBenchmarkBuilder,
    LiveCaptureScheduler,
    LiveEvidencePackageWriter,
    LiveMarketReader,
    LiveSessionController,
    LiveValidationBenchmark,
    LiveValidationReport,
)
from predixai.perception import PerceptionEngine
from predixai.vision import (
    MarketBenchmark,
    MarketElementBuilder,
    MarketEntityBuilder,
    MarketEntityRegistryBuilder,
    MarketEntityValidator,
    MarketSceneBuilder,
    MarketStructureBenchmark,
    MarketStructureBuilder,
    MarketStructureValidator,
    PatternBenchmark,
    PatternAnalysisBenchmark,
    PatternAnalysisBuilder,
    PatternAnalysisValidator,
    PatternAnalyzer,
    PatternDetector,
    PatternClassifier,
    PatternClassifierRegistry,
    PatternContextBuilder,
    IntelligenceBenchmark,
    IntelligenceContextBuilder,
    IntelligenceContextValidator,
    IntelligenceSnapshot,
    IntelligenceSnapshotBuilder,
    HypothesisEvaluator,
    HypothesisScore,
    MarketHypothesisBuilder,
    MarketHypothesisRegistry,
    PatternRegistryBuilder,
    PatternSceneBuilder,
    PatternValidator,
    OCRParser,
    EntitySerializer,
    EntityStorage,
    PriceRegionMapper,
    RegionTextMapper,
    ScreenElementBuilder,
    ScreenLayoutBuilder,
    ScreenObjectRegistryBuilder,
    SemanticBenchmark,
    SemanticElementBuilder,
    SemanticLabelMapper,
    SemanticRegistryBuilder,
    SemanticSceneBuilder,
    SignalBuilder,
    SignalRegistry,
    SignalScorer,
    SignalValidator,
    StrategyReadinessBenchmark,
    StrategyReadinessSnapshotBuilder,
    StructuredOCRBuilder,
    TimeRegionMapper,
    VisualBenchmark,
    VisualSceneBenchmark,
    VisualSceneBuilder,
    VisualSnapshotBuilder,
    VisionEngine,
)


@dataclass(frozen=True)
class ModuleInfo:
    """Registered module metadata."""

    name: str
    package: str
    loaded: bool


@dataclass(frozen=True)
class StartupReport:
    """Result of the foundation startup sequence."""

    app_name: str
    version: str
    mode: str
    environment: str
    started_at: str
    modules: tuple[str, ...]
    status: str


class PredixAIApp:
    """Coordinates the foundation startup without business functionality."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        self.config: AppConfig = load_config(config_path)
        self.logger = configure_logger(self.config)
        self.events = EventRegistry()
        self.modules: tuple[ModuleInfo, ...] = ()
        self.capture_engine: CaptureEngine | None = None
        self.capture_status: CaptureEngineStatus | None = None
        self.vision_engine: VisionEngine | None = None
        self.ocr_engine: OCREngine | None = None
        self.ocr_parser = OCRParser()
        self.region_text_mapper = RegionTextMapper()
        self.structured_ocr_builder = StructuredOCRBuilder()
        self.visual_snapshot_builder = VisualSnapshotBuilder()
        self.visual_benchmark = VisualBenchmark(
            enabled=self._visual_benchmark_enabled()
        )
        self.screen_element_builder = ScreenElementBuilder()
        self.screen_layout_builder = ScreenLayoutBuilder()
        self.screen_object_registry_builder = ScreenObjectRegistryBuilder()
        self.visual_scene_builder = VisualSceneBuilder()
        self.visual_scene_benchmark = VisualSceneBenchmark(
            enabled=self._visual_scene_benchmark_enabled()
        )
        self.semantic_element_builder = SemanticElementBuilder()
        self.semantic_label_mapper = SemanticLabelMapper()
        self.semantic_scene_builder = SemanticSceneBuilder()
        self.semantic_registry_builder = SemanticRegistryBuilder()
        self.semantic_benchmark = SemanticBenchmark(
            enabled=self._semantic_benchmark_enabled()
        )
        self.market_element_builder = MarketElementBuilder()
        self.market_entity_builder = MarketEntityBuilder()
        self.market_entity_registry_builder = MarketEntityRegistryBuilder()
        self.market_entity_validator = MarketEntityValidator()
        self.market_entity_serializer = EntitySerializer()
        self.market_entity_storage = EntityStorage()
        self.market_structure_builder = MarketStructureBuilder()
        self.market_structure_validator = MarketStructureValidator()
        self.market_structure_benchmark = MarketStructureBenchmark(
            enabled=self._market_structure_benchmark_enabled()
        )
        self.pattern_detector = PatternDetector()
        self.pattern_registry_builder = PatternRegistryBuilder()
        self.pattern_scene_builder = PatternSceneBuilder()
        self.pattern_validator = PatternValidator()
        self.pattern_benchmark = PatternBenchmark(
            enabled=self._pattern_benchmark_enabled()
        )
        self.pattern_classifier = PatternClassifier()
        self.pattern_context_builder = PatternContextBuilder()
        self.pattern_analysis_builder = PatternAnalysisBuilder()
        self.pattern_analysis_validator = PatternAnalysisValidator()
        self.pattern_analyzer = PatternAnalyzer()
        self.pattern_analysis_benchmark = PatternAnalysisBenchmark(
            enabled=self._pattern_analysis_benchmark_enabled()
        )
        self.intelligence_context_builder = IntelligenceContextBuilder()
        self.intelligence_context_validator = IntelligenceContextValidator()
        self.intelligence_snapshot_builder = IntelligenceSnapshotBuilder()
        self.intelligence_benchmark = IntelligenceBenchmark(
            enabled=self._intelligence_benchmark_enabled()
        )
        self.hypothesis_evaluator = HypothesisEvaluator()
        self.market_hypothesis_builder = MarketHypothesisBuilder()
        self.market_hypothesis_registry = MarketHypothesisRegistry
        self.signal_builder = SignalBuilder()
        self.signal_registry = SignalRegistry
        self.signal_scorer = SignalScorer()
        self.signal_validator = SignalValidator()
        self.strategy_readiness_snapshot_builder = StrategyReadinessSnapshotBuilder()
        self.strategy_readiness_benchmark = StrategyReadinessBenchmark(
            enabled=self._strategy_readiness_benchmark_enabled()
        )
        self.live_session_controller = LiveSessionController()
        self.broker_window_detector = BrokerWindowDetector()
        self.live_capture_scheduler = LiveCaptureScheduler()
        self.live_market_reader = LiveMarketReader()
        self.field_locator = FieldLocator()
        self.field_extractor = FieldExtractor()
        self.candle_snapshot_builder = CandleSnapshotBuilder()
        self.candle_statistics_builder = CandleStatisticsBuilder()
        self.live_candle_benchmark = LiveCandleBenchmarkBuilder()
        self.live_calibration_engine = LiveCalibrationEngine(
            config=self.config,
            capture_engine=self.capture_engine,
            capture_status=self.capture_status,
            vision_engine=self.vision_engine,
            ocr_engine=self.ocr_engine if self.ocr_engine is not None else OCREngine(self.config.ocr),
            logger=self.logger,
        )
        self.live_validation_benchmark = LiveValidationBenchmark(
            enabled=self._live_validation_benchmark_enabled()
        )
        self.live_evidence_package_writer = LiveEvidencePackageWriter(
            self.config.resolve_path("data") / "live_evidence"
        )
        self.price_region_mapper = PriceRegionMapper()
        self.time_region_mapper = TimeRegionMapper()
        self.market_scene_builder = MarketSceneBuilder()
        self.market_benchmark = MarketBenchmark(
            enabled=self._market_benchmark_enabled()
        )
        self.last_capture_context: dict[str, object] = {}

    def bootstrap(self) -> StartupReport:
        """Load foundation services and return a startup report."""
        try:
            self.modules = self._load_modules()
            module_names = tuple(module.name for module in self.modules)
            log_startup(self.logger, self.config, module_names)
            perception_snapshot = self._inspect_perception()
            capture_status = self._initialize_capture()
            self.events.record(
                "application.initialized",
                {
                    "version": self.config.version,
                    "mode": self.config.mode,
                    "modules": module_names,
                },
            )
            if perception_snapshot is not None:
                self.events.record(
                    "perception.environment_detected",
                    {
                        "environment": perception_snapshot.environment.to_dict(),
                        "window_count": len(perception_snapshot.windows.windows),
                    },
                )
            if capture_status is not None:
                self.events.record(
                    "capture.engine_initialized",
                    {
                        "session_id": capture_status.session.session_id,
                        "storage": capture_status.storage.to_dict(),
                    },
                )
            return StartupReport(
                app_name=self.config.name,
                version=self.config.version,
                mode=self.config.mode,
                environment=self.config.environment,
                started_at=datetime.now().astimezone().isoformat(),
                modules=module_names,
                status="initialized",
            )
        except Exception as exc:
            self.events.record("application.error", {"error": str(exc)})
            log_error(self.logger, "PredixAI initialization error", exc)
            raise

    def capture_snapshot(self) -> SnapshotMetadata:
        """Capture one manual snapshot after the foundation bootstrap."""
        if self.capture_engine is None or self.capture_status is None:
            capture_status = self._initialize_capture()
            if capture_status is None:
                raise RuntimeError("Capture Engine is disabled.")

        if self.capture_engine is None or self.capture_status is None:
            raise RuntimeError("Capture Engine is not available.")

        metadata = self.capture_engine.capture_manual_snapshot(
            self.capture_status
        )
        log_manual_snapshot(self.logger, metadata)
        self.events.record("capture.snapshot_created", metadata.to_dict())
        frame = self._process_vision_frame(metadata)
        self.events.record("vision.frame_created", frame.to_dict())
        return metadata

    def live_calibrate(self) -> object:
        """Run an isolated live calibration flow without changing live-once."""
        if self.capture_engine is None or self.capture_status is None:
            capture_status = self._initialize_capture()
            if capture_status is None:
                raise RuntimeError("Capture Engine is disabled.")

        if self.capture_engine is None or self.capture_status is None:
            raise RuntimeError("Capture Engine is not available.")

        if self.vision_engine is None:
            self.vision_engine = VisionEngine(self.config)
        if self.ocr_engine is None:
            self.ocr_engine = OCREngine(self.config.ocr)
        self.live_calibration_engine = LiveCalibrationEngine(
            config=self.config,
            capture_engine=self.capture_engine,
            capture_status=self.capture_status,
            vision_engine=self.vision_engine,
            ocr_engine=self.ocr_engine,
            logger=self.logger,
        )
        broker_state = self.broker_window_detector.detect()
        return self.live_calibration_engine.run(
            countdown_seconds=10,
            window_title=broker_state.title,
        )

    def live_once(
        self,
        *,
        captures_per_candle_override: int | None = None,
        interval_seconds_override: int | None = None,
        countdown_seconds_override: int | None = None,
    ) -> object:
        """Run one live validation candle without trading actions."""
        live_config = self.config.live if isinstance(self.config.live, dict) else {}
        timeframe = str(live_config.get("timeframe", "M1"))
        interval_seconds = int(live_config.get("capture_interval_seconds", 10))
        if interval_seconds_override is not None:
            interval_seconds = max(1, int(interval_seconds_override))

        captures_per_candle = 1
        if captures_per_candle_override is not None:
            captures_per_candle = max(1, int(captures_per_candle_override))

        validation_candles = int(live_config.get("validation_candles", 1))

        session = self.live_session_controller.start(
            timeframe=timeframe,
            capture_interval_seconds=interval_seconds,
            captures_per_candle=captures_per_candle,
            validation_candles=validation_candles,
        )
        log_live_session(self.logger, session)

        countdown_seconds = 10
        if countdown_seconds_override is not None:
            countdown_seconds = max(0, int(countdown_seconds_override))

        if countdown_seconds > 0:
            print("Preparando live-once. Coloque a Olymp Trade maximizada em primeiro plano.")
            for remaining in range(countdown_seconds, 0, -1):
                print(f"Captura em {remaining}...")
                sleep(1)

        broker_state = self.broker_window_detector.detect()
        log_broker_window_state(self.logger, broker_state)

        live_start = perf_counter()
        if not self._is_valid_broker_window(broker_state):
            return self._handle_ignored_broker_window(
                session=session,
                broker_state=broker_state,
                timeframe=timeframe,
                live_start=live_start,
            )

        benchmark_run = self.live_validation_benchmark.start()
        readings: list[object] = []
        field_location_map = self.field_locator.locate(
            window_title=broker_state.title,
            timeframe=timeframe,
        )
        log_field_location_map(self.logger, field_location_map)
        extraction_results = []
        ticks = self.live_capture_scheduler.schedule(
            total_ticks=captures_per_candle,
            interval_seconds=interval_seconds,
        )
        for tick in ticks:
            tick_start = perf_counter()

            capture_start = perf_counter()
            metadata = self.capture_snapshot()
            capture_ms = round((perf_counter() - capture_start) * 1000, 3)
            tick = type(tick)(
                tick_index=tick.tick_index,
                captured_at=tick.captured_at,
                capture_path=metadata.file_path,
                window_title=broker_state.title,
                metadata={
                    **tick.metadata,
                    "session_id": session.session_id,
                    "window_title": broker_state.title,
                },
            )
            log_live_capture_tick(self.logger, tick)
            calibration_start = perf_counter()
            calibration_result = self.live_calibration_engine.read_snapshot_fields(
                metadata=metadata,
                window_title=broker_state.title,
                output_directory_name="live_once_fields",
                open_artifacts=False,
            )
            calibration_ms = round((perf_counter() - calibration_start) * 1000, 3)

            reading_start = perf_counter()
            confidence_values = [
                result.confidence
                for result in calibration_result.field_results
                if result.confidence > 0
            ]
            ocr_confidence = (
                round(sum(confidence_values) / len(confidence_values), 3)
                if confidence_values
                else 0.0
            )
            ocr_text = calibration_result.to_text()
            reading = self.live_market_reader.read(
                ocr_text=ocr_text,
                ocr_confidence=ocr_confidence,
                timeframe=timeframe,
            )
            reading_ms = round((perf_counter() - reading_start) * 1000, 3)
            log_live_market_reading(self.logger, reading)
            readings.append(reading)

            calibration_text = calibration_result.to_text()
            normalized_asset = self._normalize_runtime_asset(
                reading.asset,
                broker_state.title,
                calibration_text,
            )
            normalized_balance = self._normalize_runtime_balance(
                reading.balance,
                reading.trade_value,
                calibration_text,
            )
            normalized_price = self._normalize_runtime_price(
                broker_state.title,
                reading.price,
                calibration_text,
                normalized_asset,
            )
            remaining_time = self._extract_remaining_time(calibration_text)
            expiration_suggestion = self._build_expiration_suggestion(
                remaining_time,
                reading.duration,
                timeframe,
            )

            runtime_persistence_start = perf_counter()
            runtime_dir = self.config.resolve_path("data") / "runtime"
            runtime_dir.mkdir(parents=True, exist_ok=True)
            runtime_path = runtime_dir / "last_live_reading.json"
            runtime_payload = {
                "status": "READY",
                "source": "live_once",
                "session_id": session.session_id,
                "timestamp": calibration_result.timestamp,
                "window_title": broker_state.title,
                "asset": reading.asset,
                "price": normalized_price,
                "time": reading.time,
                "balance": reading.balance,
                "payout": reading.payout,
                "trade_value": reading.trade_value,
                "duration": reading.duration,
                "timeframe": reading.timeframe,
                "confidence": reading.confidence,
                "source_ocr_text": reading.source_ocr_text,
                "unknown_fields": reading.metadata.get("unknown_fields", []),
                "capture_path": str(metadata.file_path),
                "calibration_output_directory": str(calibration_result.output_directory),
            }
            price_value = self._parse_runtime_number(normalized_price)

            history_path = runtime_dir / "live_price_history.json"
            if history_path.exists():
                try:
                    history_payload = json.loads(history_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    history_payload = []
            else:
                history_payload = []

            if not isinstance(history_payload, list):
                history_payload = []

            history_entry = {
                "status": "READY",
                "source": "live_once",
                "session_id": session.session_id,
                "timestamp": calibration_result.timestamp,
                "window_title": broker_state.title,
                "asset": reading.asset,
                "price": normalized_price,
                "price_value": price_value,
                "payout": reading.payout,
                "balance": reading.balance,
                "trade_value": reading.trade_value,
                "duration": reading.duration,
                "timeframe": reading.timeframe,
                "confidence": reading.confidence,
                "source_ocr_text": reading.source_ocr_text,
                "unknown_fields": reading.metadata.get("unknown_fields", []),
            }

            runtime_payload["asset"] = normalized_asset
            runtime_payload["balance"] = normalized_balance
            runtime_payload["balance_raw_ocr"] = reading.balance
            runtime_payload["remaining_time"] = remaining_time
            runtime_payload["expiration_suggestion"] = expiration_suggestion
            runtime_payload["balance_quality"] = "OCR_ESTIMATED"

            history_entry["asset"] = normalized_asset
            history_entry["balance"] = normalized_balance
            history_entry["balance_raw_ocr"] = reading.balance
            history_entry["remaining_time"] = remaining_time
            history_entry["expiration_suggestion"] = expiration_suggestion
            history_entry["balance_quality"] = "OCR_ESTIMATED"

            is_valid_runtime_reading, rejection_reasons = (
                self._validate_runtime_live_reading(
                    asset=normalized_asset,
                    payout=reading.payout,
                    price_value=price_value,
                    window_title=broker_state.title,
                )
            )

            if is_valid_runtime_reading:
                price_tick_id = self._persist_runtime_price_tick_sqlite(
                    runtime_dir=runtime_dir,
                    created_at=calibration_result.timestamp,
                    asset=normalized_asset,
                    price=price_value,
                    source="live_once",
                    metadata={
                        "window_title": broker_state.title,
                        "session_id": session.session_id,
                        "timeframe": reading.timeframe,
                        "capture_path": str(metadata.file_path),
                        "price_source_priority": (
                            "window_title_then_labeled_text_then_reader"
                        ),
                    },
                )
                if price_tick_id is not None:
                    runtime_payload["price_tick_id"] = price_tick_id
                    history_entry["price_tick_id"] = price_tick_id
                runtime_path.write_text(
                    json.dumps(runtime_payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                history_payload.append(history_entry)
                history_payload = history_payload[-3000:]
                history_path.write_text(
                    json.dumps(history_payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            else:
                self._append_rejected_runtime_live_reading(
                    runtime_dir=runtime_dir,
                    payload=history_entry,
                    rejection_reasons=rejection_reasons,
                )

            runtime_persistence_ms = round(
                (perf_counter() - runtime_persistence_start) * 1000,
                3,
            )

            field_extraction_start = perf_counter()
            extraction = self.field_extractor.extract(reading, field_location_map)
            extraction_results.append(extraction)
            log_field_extraction_result(self.logger, extraction)
            field_extraction_ms = round(
                (perf_counter() - field_extraction_start) * 1000,
                3,
            )

            tick_total_ms = round((perf_counter() - tick_start) * 1000, 3)
            timing_path = runtime_dir / "live_timing_profile.json"
            if timing_path.exists():
                try:
                    timing_payload = json.loads(timing_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    timing_payload = []
            else:
                timing_payload = []

            if not isinstance(timing_payload, list):
                timing_payload = []

            timing_payload.append(
                {
                    "session_id": session.session_id,
                    "timestamp": calibration_result.timestamp,
                    "tick_index": tick.tick_index,
                    "asset": reading.asset,
                    "price": normalized_price,
                    "payout": reading.payout,
                    "valid_runtime_reading": is_valid_runtime_reading,
                    "rejection_reasons": rejection_reasons,
                    "capture_ms": capture_ms,
                    "calibration_ms": calibration_ms,
                    "reading_ms": reading_ms,
                    "runtime_persistence_ms": runtime_persistence_ms,
                    "field_extraction_ms": field_extraction_ms,
                    "tick_total_ms": tick_total_ms,
                }
            )
            timing_payload = timing_payload[-3000:]
            timing_path.write_text(
                json.dumps(timing_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            if tick.tick_index < captures_per_candle:
                sleep(interval_seconds)

        candle_snapshot_result = self.candle_snapshot_builder.build(
            session_id=session.session_id,
            timeframe=timeframe,
            readings=tuple(readings),
            extraction_results=tuple(extraction_results),
            locator=field_location_map,
        )
        candle_snapshot = candle_snapshot_result.snapshot
        log_candle_snapshot(self.logger, candle_snapshot)
        candle_statistics_result = self.candle_statistics_builder.build(candle_snapshot)
        candle_statistics = candle_statistics_result.statistics
        log_candle_statistics(self.logger, candle_statistics)
        live_candle_run = self.live_candle_benchmark.start(
            enabled=bool(self.config.live.get("benchmark_enabled", True))
        )
        live_candle_benchmark = self.live_candle_benchmark.finish(
            live_candle_run,
            candle_snapshot,
            candle_statistics,
        )
        log_live_candle_benchmark(self.logger, live_candle_benchmark.benchmark)

        report = self._build_live_validation_report(
            session=session,
            readings=tuple(readings),
            broker_state=broker_state,
            total_time_ms=round((perf_counter() - live_start) * 1000, 3),
        )
        log_live_validation_report(self.logger, report)
        benchmark = self.live_validation_benchmark.finish(benchmark_run, report)
        log_live_validation_benchmark(self.logger, benchmark)
        live_evidence_package = self.live_evidence_package_writer.build(
            source="live_once",
            session_id=session.session_id,
            capture_count=candle_snapshot.capture_count,
            field_count=len(candle_snapshot.field_names),
            unknown_fields=tuple(candle_snapshot.unknown_fields),
            candle_snapshot=candle_snapshot,
            candle_statistics=candle_statistics,
            live_candle_benchmark=live_candle_benchmark.benchmark,
            live_validation_benchmark=benchmark,
        )
        live_evidence_path = self.live_evidence_package_writer.write(
            live_evidence_package
        )
        self.events.record(
            "live.validation_completed",
            {
                **report.to_dict(),
                "candle_snapshot": candle_snapshot.to_dict(),
                "candle_statistics": candle_statistics.to_dict(),
                "live_candle_benchmark": live_candle_benchmark.benchmark.to_dict(),
                "live_validation_benchmark": benchmark.to_dict(),
                "live_evidence_path": str(live_evidence_path),
            },
        )
        return {
            "report": report,
            "candle_snapshot": candle_snapshot,
            "candle_statistics": candle_statistics,
            "live_candle_benchmark": live_candle_benchmark.benchmark,
            "live_validation_benchmark": benchmark,
            "live_evidence_path": live_evidence_path,
        }

    def live_price_tick(self) -> dict[str, object]:
        """Persist one lightweight observer price tick without full-screen OCR."""
        live_config = self.config.live if isinstance(self.config.live, dict) else {}
        timeframe = str(live_config.get("timeframe", "M1"))
        runtime_dir = self.config.resolve_path("data") / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)

        started_at = perf_counter()
        timestamp = datetime.now().astimezone().isoformat()
        tick_session_id = f"price_tick:{timestamp}"
        mobile_session = self._read_runtime_mobile_session(runtime_dir)
        observer_session_id = str(mobile_session.get("session_id") or tick_session_id)
        broker_state = self.broker_window_detector.detect()
        log_broker_window_state(self.logger, broker_state)

        if not self._is_valid_broker_window(broker_state):
            metadata = getattr(broker_state, "metadata", {}) or {}
            reason = str(
                metadata.get("ignore_reason")
                or "Janela ignorada: janela ativa nao e corretora"
            )
            payload = {
                "status": "IGNORED_WINDOW",
                "source": "live_price_tick",
                "session_id": observer_session_id,
                "tick_session_id": tick_session_id,
                "timestamp": timestamp,
                "window_title": getattr(broker_state, "title", "UNKNOWN"),
                "asset": "UNKNOWN",
                "price": "UNKNOWN",
                "price_value": None,
                "time": "UNKNOWN",
                "balance": "UNKNOWN",
                "payout": "UNKNOWN",
                "trade_value": "UNKNOWN",
                "duration": "UNKNOWN",
                "timeframe": timeframe,
                "confidence": 0.0,
                "unknown_fields": ["window", "asset", "price"],
                "message": reason,
                "reason": reason,
                "capture_skipped": True,
                "broker_window": broker_state.to_dict(),
                "mobile_session": mobile_session,
            }
            runtime_path = runtime_dir / "last_live_reading.json"
            runtime_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self._append_rejected_runtime_live_reading(
                runtime_dir=runtime_dir,
                payload=payload,
                rejection_reasons=["invalid_broker_window"],
            )
            return {
                "status": "IGNORED_WINDOW",
                "source": "live_price_tick",
                "reason": reason,
                "total_time_ms": round((perf_counter() - started_at) * 1000, 3),
            }

        title = getattr(broker_state, "title", "") or ""
        asset = self._normalize_runtime_asset("UNKNOWN", title, "")
        price_value = self._extract_runtime_price_from_title(title, asset)
        price_source = "window_title"
        if not self._is_runtime_price_allowed(price_value, asset):
            detected_price = self._read_recent_runtime_price(runtime_dir, asset)
            if detected_price is not None:
                price_value, detected_asset = detected_price
                asset = detected_asset or asset
                price_source = "last_detected_price_field"

        if not self._is_runtime_price_allowed(price_value, asset):
            reason = "Preco nao encontrado no titulo da janela"
            payload = {
                "status": "PRICE_NOT_FOUND",
                "source": "live_price_tick",
                "session_id": observer_session_id,
                "tick_session_id": tick_session_id,
                "timestamp": timestamp,
                "window_title": title or "UNKNOWN",
                "asset": asset,
                "price": "UNKNOWN",
                "price_value": None,
                "time": "UNKNOWN",
                "balance": "UNKNOWN",
                "payout": "UNKNOWN",
                "trade_value": "UNKNOWN",
                "duration": "UNKNOWN",
                "timeframe": timeframe,
                "confidence": 0.0,
                "unknown_fields": ["price"],
                "message": reason,
                "reason": reason,
                "capture_skipped": True,
                "broker_window": broker_state.to_dict(),
                "mobile_session": mobile_session,
            }
            runtime_path = runtime_dir / "last_live_reading.json"
            runtime_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self._append_rejected_runtime_live_reading(
                runtime_dir=runtime_dir,
                payload=payload,
                rejection_reasons=["price_not_found_in_window_title"],
            )
            return {
                "status": "PRICE_NOT_FOUND",
                "source": "live_price_tick",
                "reason": reason,
                "asset": asset,
                "total_time_ms": round((perf_counter() - started_at) * 1000, 3),
            }

        price_text = self._format_runtime_price_value(price_value)
        payload = {
            "status": "READY",
            "source": "live_price_tick",
            "session_id": observer_session_id,
            "tick_session_id": tick_session_id,
            "timestamp": timestamp,
            "asset": asset,
            "price": price_text,
            "price_value": price_value,
            "window_title": title,
            "time": "UNKNOWN",
            "balance": "UNKNOWN",
            "payout": "UNKNOWN",
            "trade_value": "UNKNOWN",
            "duration": "UNKNOWN",
            "timeframe": timeframe,
            "confidence": 100.0,
            "source_ocr_text": (
                f"Janela detectada: {title}\n"
                f"Price: {price_text}\n"
                f"Asset: {asset}\n"
            ),
            "unknown_fields": [],
            "price_source": price_source,
            "capture_skipped": True,
            "broker_window": broker_state.to_dict(),
            "balance_quality": "NOT_READ",
            "mobile_session": mobile_session,
        }
        tick_id = self._persist_runtime_price_tick_sqlite(
            runtime_dir=runtime_dir,
            created_at=timestamp,
            asset=asset,
            price=price_value,
            source=price_source,
            metadata={
                "window_title": title,
                "timeframe": timeframe,
                "reader": "live_price_tick",
                "session_id": observer_session_id,
                "tick_session_id": tick_session_id,
                "capture_skipped": True,
                "broker_window": broker_state.to_dict(),
                "mobile_session": mobile_session,
            },
        )
        if tick_id is not None:
            payload["price_tick_id"] = tick_id

        runtime_path = runtime_dir / "last_live_reading.json"
        runtime_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._append_runtime_price_history(runtime_dir, payload)
        return {
            "status": "READY",
            "source": price_source,
            "asset": asset,
            "price": price_value,
            "session_id": observer_session_id,
            "price_tick_id": tick_id,
            "total_time_ms": round((perf_counter() - started_at) * 1000, 3),
        }

    def _read_runtime_mobile_session(self, runtime_dir: Path) -> dict[str, object]:
        session_path = runtime_dir / "mobile_current_session.json"
        if not session_path.exists():
            return {}
        try:
            payload = json.loads(session_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _read_recent_runtime_price(
        self,
        runtime_dir: Path,
        fallback_asset: str,
        *,
        max_age_seconds: int = 2,
    ) -> tuple[float, str] | None:
        runtime_path = runtime_dir / "last_live_reading.json"
        if not runtime_path.exists():
            return None

        age_seconds = max(0.0, datetime.now().timestamp() - runtime_path.stat().st_mtime)
        if age_seconds > max_age_seconds:
            return None

        try:
            payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None

        asset = self._normalize_runtime_asset(
            str(payload.get("asset") or fallback_asset or "UNKNOWN"),
            str(payload.get("window_title") or ""),
            str(payload.get("source_ocr_text") or ""),
        )
        price = self._parse_runtime_number(
            payload.get("price_value")
            if payload.get("price_value") is not None
            else payload.get("price")
        )
        if not self._is_runtime_price_allowed(price, asset):
            return None
        return float(price), asset

    def _append_runtime_price_history(
        self,
        runtime_dir: Path,
        payload: dict[str, object],
    ) -> None:
        history_path = runtime_dir / "live_price_history.json"
        if history_path.exists():
            try:
                history_payload = json.loads(history_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                history_payload = []
        else:
            history_payload = []

        if not isinstance(history_payload, list):
            history_payload = []

        history_entry = dict(payload)
        price_value = self._parse_runtime_number(
            history_entry.get("price_value")
            if history_entry.get("price_value") is not None
            else history_entry.get("price")
        )
        is_valid, _ = self._validate_runtime_live_reading(
            asset=str(history_entry.get("asset") or "UNKNOWN"),
            payout=str(history_entry.get("payout") or "UNKNOWN"),
            price_value=price_value,
            window_title=str(history_entry.get("window_title") or ""),
        )
        if not is_valid:
            return
        history_payload.append(history_entry)
        history_payload = history_payload[-3000:]
        history_path.write_text(
            json.dumps(history_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _persist_runtime_price_tick_sqlite(
        self,
        *,
        runtime_dir: Path,
        created_at: str,
        asset: str,
        price: float | None,
        source: str,
        metadata: dict[str, object],
    ) -> int | None:
        if price is None:
            return None
        is_valid, _ = self._validate_runtime_live_reading(
            asset=asset,
            payout=str(metadata.get("payout") or "UNKNOWN"),
            price_value=price,
            window_title=str(metadata.get("window_title") or ""),
        )
        if not is_valid:
            return None

        db_path = runtime_dir / "predixai_trader_signals.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS price_ticks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    asset TEXT,
                    price REAL NOT NULL,
                    source TEXT,
                    metadata_json TEXT
                )
                """
            )
            cursor = conn.execute(
                """
                INSERT INTO price_ticks (
                    created_at, asset, price, source, metadata_json
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    asset,
                    price,
                    source,
                    json.dumps(metadata, ensure_ascii=False),
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def _load_modules(self) -> tuple[ModuleInfo, ...]:
        loaded_modules: list[ModuleInfo] = []
        for module in self.config.v1_modules:
            importlib.import_module(module["package"])
            loaded_modules.append(
                ModuleInfo(
                    name=module["name"],
                    package=module["package"],
                    loaded=True,
                )
            )
        return tuple(loaded_modules)

    def _inspect_perception(self) -> object | None:
        if not bool(self.config.perception.get("enabled", False)):
            return None

        snapshot = PerceptionEngine(self.config).inspect()
        if bool(self.config.perception.get("log_on_startup", True)):
            log_perception(self.logger, snapshot)
        return snapshot

    def _initialize_capture(self) -> object | None:
        if not bool(self.config.capture.get("enabled", False)):
            return None

        self.capture_engine = CaptureEngine(self.config)
        status = self.capture_engine.bootstrap()
        self.capture_status = status
        log_capture_engine(self.logger, status)
        return status

    def _process_vision_frame(self, metadata: SnapshotMetadata) -> object:
        if not bool(self.config.vision.get("enabled", False)):
            raise RuntimeError("Vision Engine is required for --capture.")

        if self.vision_engine is None:
            self.vision_engine = VisionEngine(self.config)

        frame = self.vision_engine.process_capture(metadata)
        log_vision_frame(self.logger, metadata, frame)
        log_region_mapping_started(self.logger)
        region_registry = self.vision_engine.register_regions(frame)
        log_region_registry(self.logger, region_registry)
        self.events.record(
            "vision.region_registry_loaded",
            region_registry.to_dict(),
        )
        log_region_mapping_finished(self.logger)
        image_buffer = self._load_vision_image_buffer(metadata)
        if image_buffer is not None:
            self.events.record("vision.image_buffer_created", image_buffer.to_dict())
        roi_registry = self._register_vision_rois(frame)
        self.events.record("vision.roi_registry_loaded", roi_registry.to_dict())
        roi_crops = self._create_roi_crops(roi_registry, image_buffer)
        self.events.record(
            "vision.roi_crops_created",
            {"crops": [roi_crop.to_dict() for roi_crop in roi_crops]},
        )
        roi_exports = self._export_roi_crops(roi_crops, image_buffer)
        self.events.record(
            "vision.roi_crops_exported",
            {"exports": [roi_export.to_dict() for roi_export in roi_exports]},
        )
        ocr_results = self._prepare_ocr_pipeline(roi_exports)
        self.events.record(
            "ocr.pipeline_ready",
            {"results": [ocr_result.to_dict() for ocr_result in ocr_results]},
        )
        visual_benchmark_run = self.visual_benchmark.start()
        parsed_ocr = self._parse_ocr_results(ocr_results)
        self.events.record(
            "visual.ocr_parsed",
            {"results": [parsed_text.to_dict() for parsed_text in parsed_ocr]},
        )
        region_text_mapping = self._map_region_texts(
            parsed_ocr,
            region_registry,
            roi_exports,
        )
        self.events.record(
            "visual.region_texts_mapped",
            region_text_mapping.to_dict(),
        )
        structured_ocr = self._build_structured_ocr(
            frame,
            region_text_mapping,
            ocr_results,
        )
        self.events.record("visual.structured_ocr_created", structured_ocr.to_dict())
        visual_snapshot = self._build_visual_snapshot(
            frame,
            image_buffer,
            region_registry,
            roi_exports,
            structured_ocr,
        )
        self.events.record("visual.snapshot_created", visual_snapshot.to_dict())
        visual_benchmark = self.visual_benchmark.finish(
            visual_benchmark_run,
            visual_snapshot,
            ocr_results,
        )
        log_visual_benchmark(self.logger, visual_benchmark)
        self.events.record(
            "visual.benchmark_completed",
            visual_benchmark.to_dict(),
        )
        visual_scene_benchmark_run = self.visual_scene_benchmark.start()
        screen_elements = self._build_screen_elements(visual_snapshot)
        self.events.record("scene.screen_elements_created", screen_elements.to_dict())
        screen_layout = self._build_screen_layout(visual_snapshot, screen_elements)
        self.events.record("scene.screen_layout_created", screen_layout.to_dict())
        screen_object_registry = self._build_screen_object_registry(
            visual_snapshot,
            screen_elements,
        )
        self.events.record(
            "scene.object_registry_created",
            screen_object_registry.to_dict(),
        )
        visual_scene = self._build_visual_scene(
            visual_snapshot,
            screen_elements,
            screen_layout,
            screen_object_registry,
        )
        self.events.record("scene.visual_scene_created", visual_scene.to_dict())
        scene_benchmark = self.visual_scene_benchmark.finish(
            visual_scene_benchmark_run,
            visual_scene,
        )
        log_visual_scene_benchmark(self.logger, scene_benchmark)
        self.events.record("scene.benchmark_completed", scene_benchmark.to_dict())
        semantic_benchmark_run = self.semantic_benchmark.start()
        semantic_elements = self._build_semantic_elements(visual_scene)
        self.events.record(
            "semantic.elements_created",
            semantic_elements.to_dict(),
        )
        semantic_label_mapping = self._map_semantic_labels(semantic_elements)
        self.events.record(
            "semantic.labels_mapped",
            semantic_label_mapping.to_dict(),
        )
        semantic_scene = self._build_semantic_scene(
            visual_scene,
            semantic_elements,
            semantic_label_mapping,
        )
        self.events.record("semantic.scene_created", semantic_scene.to_dict())
        semantic_registry = self._build_semantic_registry(semantic_scene)
        self.events.record("semantic.registry_created", semantic_registry.to_dict())
        semantic_benchmark = self.semantic_benchmark.finish(
            semantic_benchmark_run,
            semantic_scene,
            semantic_registry,
        )
        log_semantic_benchmark(self.logger, semantic_benchmark)
        self.events.record("semantic.benchmark_completed", semantic_benchmark.to_dict())
        market_benchmark_run = self.market_benchmark.start()
        market_elements = self._build_market_elements(semantic_scene)
        self.events.record("market.elements_created", market_elements.to_dict())
        price_regions = self._map_price_regions(market_elements)
        self.events.record("market.price_regions_mapped", price_regions.to_dict())
        time_regions = self._map_time_regions(market_elements)
        self.events.record("market.time_regions_mapped", time_regions.to_dict())
        market_scene = self._build_market_scene(
            visual_scene,
            semantic_scene,
            market_elements,
            price_regions,
            time_regions,
        )
        self.events.record("market.scene_created", market_scene.to_dict())
        market_benchmark = self.market_benchmark.finish(
            market_benchmark_run,
            market_scene,
        )
        log_market_benchmark(self.logger, market_benchmark)
        self.events.record("market.benchmark_completed", market_benchmark.to_dict())
        market_structure_benchmark_run = self.market_structure_benchmark.start()
        market_entities = self._build_market_entities(market_scene)
        self.events.record("market.entities_created", market_entities.to_dict())
        market_entity_validation = self._validate_market_entities(market_entities)
        self.events.record(
            "market.entities_validated",
            market_entity_validation.to_dict(),
        )
        market_entity_registry = self._build_market_entity_registry(market_entities)
        self.events.record(
            "market.entity_registry_created",
            market_entity_registry.to_dict(),
        )
        market_structure = self._build_market_structure(
            visual_snapshot,
            market_scene,
            market_entities,
            market_entity_registry,
            ocr_results[0],
        )
        self.events.record("market.structure_created", market_structure.to_dict())
        market_structure_validation = self._validate_market_structure(
            market_structure
        )
        self.events.record(
            "market.structure_validated",
            market_structure_validation.to_dict(),
        )
        market_structure_benchmark = self.market_structure_benchmark.finish(
            market_structure_benchmark_run,
            market_structure,
        )
        log_market_structure_benchmark(self.logger, market_structure_benchmark)
        self.events.record(
            "market.structure_benchmark_completed",
            market_structure_benchmark.to_dict(),
        )
        pattern_benchmark_run = self.pattern_benchmark.start()
        detected_patterns = self._detect_patterns(market_structure)
        self.events.record("pattern.detected", detected_patterns.to_dict())
        pattern_registry = self._build_pattern_registry(detected_patterns)
        self.events.record(
            "pattern.registry_created",
            pattern_registry.to_dict(),
        )
        pattern_validation = self._validate_patterns(detected_patterns)
        self.events.record(
            "pattern.validated",
            pattern_validation.to_dict(),
        )
        pattern_scene = self._build_pattern_scene(
            market_structure,
            pattern_registry,
            detected_patterns,
        )
        self.events.record("pattern.scene_created", pattern_scene.to_dict())
        pattern_benchmark = self.pattern_benchmark.finish(
            pattern_benchmark_run,
            pattern_scene,
        )
        log_pattern_benchmark(self.logger, pattern_benchmark)
        self.events.record(
            "pattern.benchmark_completed",
            pattern_benchmark.to_dict(),
        )
        pattern_analysis_benchmark_run = self.pattern_analysis_benchmark.start()
        pattern_classifications = self._classify_patterns(pattern_scene)
        self.events.record(
            "pattern.classified",
            {"classifications": [item.to_dict() for item in pattern_classifications]},
        )
        pattern_classification_registry = self._build_pattern_classification_registry(
            pattern_classifications
        )
        self.events.record(
            "pattern.classification_registry_created",
            pattern_classification_registry.to_dict(),
        )
        pattern_context = self._build_pattern_context(
            pattern_scene,
            market_structure,
            visual_snapshot,
        )
        self.events.record("pattern.context_created", pattern_context.to_dict())
        pattern_analysis = self._build_pattern_analysis(
            pattern_scene,
            pattern_context,
            pattern_classification_registry,
        )
        self.events.record("pattern.analysis_created", pattern_analysis.to_dict())
        pattern_analysis_validation = self._validate_pattern_analysis(
            pattern_analysis
        )
        self.events.record(
            "pattern.analysis_validated",
            pattern_analysis_validation.to_dict(),
        )
        pattern_analysis = self.pattern_analyzer.analyze(pattern_analysis)
        pattern_analysis_benchmark = self.pattern_analysis_benchmark.finish(
            pattern_analysis_benchmark_run,
            pattern_analysis,
        )
        log_pattern_analysis_benchmark(self.logger, pattern_analysis_benchmark)
        self.events.record(
            "pattern.analysis_benchmark_completed",
            pattern_analysis_benchmark.to_dict(),
        )
        intelligence_context = self._build_intelligence_context(
            pattern_analysis,
            market_structure,
            visual_snapshot,
        )
        intelligence_context_validation = self._validate_intelligence_context(
            intelligence_context
        )
        self.events.record(
            "intelligence.context_validated",
            intelligence_context_validation.to_dict(),
        )
        market_hypotheses = self._build_market_hypotheses(intelligence_context)
        self.events.record(
            "intelligence.hypotheses_created",
            market_hypotheses.to_dict(),
        )
        hypothesis_scores = self._evaluate_hypotheses(market_hypotheses)
        self.events.record(
            "intelligence.hypotheses_scored",
            {"scores": [score.to_dict() for score in hypothesis_scores]},
        )
        intelligence_benchmark_run = self.intelligence_benchmark.start()
        intelligence_snapshot = self._build_intelligence_snapshot(
            market_structure,
            pattern_analysis,
            intelligence_context,
            market_hypotheses,
        )
        self.events.record(
            "intelligence.snapshot_created",
            intelligence_snapshot.to_dict(),
        )
        log_intelligence_snapshot(self.logger, intelligence_snapshot)
        intelligence_benchmark = self.intelligence_benchmark.finish(
            intelligence_benchmark_run,
            intelligence_snapshot,
        )
        log_intelligence_benchmark(self.logger, intelligence_benchmark)
        self.events.record(
            "intelligence.benchmark_completed",
            intelligence_benchmark.to_dict(),
        )
        signals = self._build_signals(intelligence_snapshot)
        self.events.record("signal.created", signals.to_dict())
        log_signal(self.logger, signals)
        signal_registry = self._build_signal_registry(signals)
        self.events.record("signal.registry_created", signal_registry.to_dict())
        log_signal_registry(self.logger, signal_registry)
        signal_validation = self._validate_signals(signals)
        self.events.record("signal.validated", signal_validation.to_dict())
        log_signal_validation(self.logger, signal_validation)
        signal_scores = self._score_signals(signals)
        self.events.record(
            "signal.scored",
            {"scores": [score.to_dict() for score in signal_scores]},
        )
        for signal_score in signal_scores:
            log_signal_score(self.logger, signal_score)
        strategy_readiness_benchmark_run = (
            self.strategy_readiness_benchmark.start()
        )
        strategy_readiness_snapshot = self._build_strategy_readiness_snapshot(
            pattern_analysis,
            intelligence_snapshot,
            market_hypotheses,
            signals,
            signal_scores,
        )
        self.events.record(
            "strategy_readiness.snapshot_created",
            strategy_readiness_snapshot.to_dict(),
        )
        strategy_readiness_benchmark = self.strategy_readiness_benchmark.finish(
            strategy_readiness_benchmark_run,
            strategy_readiness_snapshot,
        )
        log_strategy_readiness_snapshot(self.logger, strategy_readiness_snapshot)
        log_strategy_readiness_benchmark(
            self.logger,
            strategy_readiness_benchmark,
        )
        self.events.record(
            "strategy_readiness.benchmark_completed",
            strategy_readiness_benchmark.to_dict(),
        )
        self.last_capture_context = {
            "metadata": metadata,
            "frame": frame,
            "image_buffer": image_buffer,
            "roi_registry": roi_registry,
            "roi_crops": roi_crops,
            "roi_exports": roi_exports,
            "ocr_results": ocr_results,
            "parsed_ocr": parsed_ocr,
            "region_text_mapping": region_text_mapping,
            "structured_ocr": structured_ocr,
            "visual_snapshot": visual_snapshot,
            "visual_scene": visual_scene,
            "semantic_scene": semantic_scene,
            "market_scene": market_scene,
            "market_structure": market_structure,
            "pattern_scene": pattern_scene,
            "pattern_analysis": pattern_analysis,
            "intelligence_context": intelligence_context,
            "market_hypotheses": market_hypotheses,
            "signals": signals,
            "signal_scores": signal_scores,
            "strategy_readiness_snapshot": strategy_readiness_snapshot,
        }
        return frame

    def _visual_benchmark_enabled(self) -> bool:
        visual_config = self.config.vision.get("visual", {})
        if not isinstance(visual_config, dict):
            return True
        return bool(visual_config.get("benchmark_enabled", True))

    def _visual_scene_benchmark_enabled(self) -> bool:
        visual_config = self.config.vision.get("visual", {})
        if not isinstance(visual_config, dict):
            return True
        return bool(visual_config.get("scene_benchmark_enabled", True))

    def _semantic_benchmark_enabled(self) -> bool:
        visual_config = self.config.vision.get("visual", {})
        if not isinstance(visual_config, dict):
            return True
        return bool(visual_config.get("semantic_benchmark_enabled", True))

    def _market_benchmark_enabled(self) -> bool:
        visual_config = self.config.vision.get("visual", {})
        if not isinstance(visual_config, dict):
            return True
        return bool(visual_config.get("market_benchmark_enabled", True))

    def _market_structure_benchmark_enabled(self) -> bool:
        visual_config = self.config.vision.get("visual", {})
        if not isinstance(visual_config, dict):
            return True
        return bool(visual_config.get("market_structure_benchmark_enabled", True))

    def _pattern_benchmark_enabled(self) -> bool:
        visual_config = self.config.vision.get("visual", {})
        if not isinstance(visual_config, dict):
            return True
        return bool(visual_config.get("pattern_benchmark_enabled", True))

    def _pattern_analysis_benchmark_enabled(self) -> bool:
        visual_config = self.config.vision.get("visual", {})
        if not isinstance(visual_config, dict):
            return True
        return bool(visual_config.get("pattern_analysis_benchmark_enabled", True))

    def _intelligence_benchmark_enabled(self) -> bool:
        visual_config = self.config.vision.get("visual", {})
        if not isinstance(visual_config, dict):
            return True
        return bool(visual_config.get("intelligence_benchmark_enabled", True))

    def _strategy_readiness_benchmark_enabled(self) -> bool:
        visual_config = self.config.vision.get("visual", {})
        if not isinstance(visual_config, dict):
            return True
        return bool(
            visual_config.get("strategy_readiness_benchmark_enabled", True)
        )

    def _live_validation_benchmark_enabled(self) -> bool:
        live_config = self.config.live if isinstance(self.config.live, dict) else {}
        return bool(live_config.get("benchmark_enabled", True))

    def _load_vision_image_buffer(self, metadata: SnapshotMetadata) -> object:
        image_loader_config = self.config.vision.get("image_loader", {})
        if not isinstance(image_loader_config, dict):
            raise RuntimeError("Image Loader config is required for --capture.")
        if not bool(image_loader_config.get("enabled", False)):
            raise RuntimeError("Image Loader is required for --capture.")
        if self.vision_engine is None:
            raise RuntimeError("Vision Engine is not available for --capture.")

        image_buffer = self.vision_engine.load_image_buffer(metadata)
        log_image_buffer(self.logger, image_buffer)
        return image_buffer

    def _register_vision_rois(self, frame: object) -> object:
        roi_config = self.config.vision.get("roi", {})
        if not isinstance(roi_config, dict):
            raise RuntimeError("ROI config is required for --capture.")
        if not bool(roi_config.get("enabled", False)):
            raise RuntimeError("ROI registry is required for --capture.")
        if self.vision_engine is None:
            raise RuntimeError("Vision Engine is not available for --capture.")

        registry = self.vision_engine.register_rois(frame)
        log_roi_registry(self.logger, registry)
        return registry

    def _create_roi_crops(
        self,
        roi_registry: object,
        image_buffer: object,
    ) -> tuple[object, ...]:
        if self.vision_engine is None:
            return ()

        roi_crops = self.vision_engine.create_roi_crops(
            roi_registry,
            image_buffer,
        )
        for roi_crop in roi_crops:
            log_roi_crop(self.logger, roi_crop)
        return roi_crops

    def _export_roi_crops(
        self,
        roi_crops: tuple[object, ...],
        image_buffer: object,
    ) -> tuple[object, ...]:
        if self.vision_engine is None:
            return ()

        roi_exports = self.vision_engine.export_roi_crops(
            roi_crops,
            image_buffer,
        )
        for roi_export in roi_exports:
            log_roi_crop_export(self.logger, roi_export)
        return roi_exports

    def _prepare_ocr_pipeline(
        self,
        roi_exports: tuple[object, ...],
    ) -> tuple[object, ...]:
        if not bool(self.config.ocr.get("enabled", False)):
            raise RuntimeError("OCR pipeline is required for --capture.")
        if not roi_exports:
            raise RuntimeError("ROI export is required for OCR pipeline.")
        if self.ocr_engine is None:
            self.ocr_engine = OCREngine(self.config.ocr)

        ocr_results = tuple(
            self.ocr_engine.prepare_pipeline(roi_export.output_path)
            for roi_export in roi_exports
        )
        for ocr_result in ocr_results:
            log_ocr_pipeline(self.logger, ocr_result)
        return ocr_results

    def _parse_ocr_results(self, ocr_results: tuple[object, ...]) -> tuple[object, ...]:
        parsed_results = tuple(
            self.ocr_parser.parse(ocr_result)
            for ocr_result in ocr_results
        )
        for parsed_text in parsed_results:
            log_ocr_parser(self.logger, parsed_text)
        return parsed_results

    def _map_region_texts(
        self,
        parsed_ocr: tuple[object, ...],
        region_registry: object,
        roi_exports: tuple[object, ...],
    ) -> object:
        mapping = self.region_text_mapper.map_texts(
            parsed_ocr,
            region_registry,
            roi_exports,
        )
        log_region_text_mapping(self.logger, mapping)
        return mapping

    def _build_structured_ocr(
        self,
        frame: object,
        region_text_mapping: object,
        ocr_results: tuple[object, ...],
    ) -> object:
        structured_ocr = self.structured_ocr_builder.build(
            frame,
            region_text_mapping,
            ocr_results,
        )
        log_structured_ocr(self.logger, structured_ocr)
        return structured_ocr

    def _build_visual_snapshot(
        self,
        frame: object,
        image_buffer: object,
        region_registry: object,
        roi_exports: tuple[object, ...],
        structured_ocr: object,
    ) -> object:
        visual_snapshot = self.visual_snapshot_builder.build(
            frame,
            image_buffer,
            region_registry,
            roi_exports,
            structured_ocr,
        )
        log_visual_snapshot(self.logger, visual_snapshot)
        return visual_snapshot

    def _build_screen_elements(self, visual_snapshot: object) -> object:
        screen_elements = self.screen_element_builder.build(visual_snapshot)
        log_screen_elements(self.logger, screen_elements)
        return screen_elements

    def _build_screen_layout(
        self,
        visual_snapshot: object,
        screen_elements: object,
    ) -> object:
        screen_layout = self.screen_layout_builder.build(
            visual_snapshot,
            screen_elements,
        )
        log_screen_layout(self.logger, screen_layout)
        return screen_layout

    def _build_screen_object_registry(
        self,
        visual_snapshot: object,
        screen_elements: object,
    ) -> object:
        registry = self.screen_object_registry_builder.build(
            visual_snapshot,
            screen_elements,
        )
        log_screen_object_registry(self.logger, registry)
        return registry

    def _build_visual_scene(
        self,
        visual_snapshot: object,
        screen_elements: object,
        screen_layout: object,
        screen_object_registry: object,
    ) -> object:
        visual_scene = self.visual_scene_builder.build(
            visual_snapshot,
            screen_elements,
            screen_layout,
            screen_object_registry,
        )
        log_visual_scene(self.logger, visual_scene)
        return visual_scene

    def _build_semantic_elements(self, visual_scene: object) -> object:
        semantic_elements = self.semantic_element_builder.build(visual_scene)
        log_semantic_elements(self.logger, semantic_elements)
        return semantic_elements

    def _map_semantic_labels(self, semantic_elements: object) -> object:
        mapping = self.semantic_label_mapper.map_labels(semantic_elements)
        log_semantic_label_mapping(self.logger, mapping)
        return mapping

    def _build_semantic_scene(
        self,
        visual_scene: object,
        semantic_elements: object,
        semantic_label_mapping: object,
    ) -> object:
        semantic_scene = self.semantic_scene_builder.build(
            visual_scene,
            semantic_elements,
            semantic_label_mapping,
        )
        log_semantic_scene(self.logger, semantic_scene)
        return semantic_scene

    def _build_semantic_registry(self, semantic_scene: object) -> object:
        registry = self.semantic_registry_builder.build(semantic_scene)
        log_semantic_registry(self.logger, registry)
        return registry

    def _build_market_elements(self, semantic_scene: object) -> object:
        market_elements = self.market_element_builder.build(semantic_scene)
        log_market_elements(self.logger, market_elements)
        return market_elements

    def _map_price_regions(self, market_elements: object) -> object:
        mapping = self.price_region_mapper.map_regions(market_elements)
        log_price_region_mapping(self.logger, mapping)
        return mapping

    def _map_time_regions(self, market_elements: object) -> object:
        mapping = self.time_region_mapper.map_regions(market_elements)
        log_time_region_mapping(self.logger, mapping)
        return mapping

    def _build_market_scene(
        self,
        visual_scene: object,
        semantic_scene: object,
        market_elements: object,
        price_regions: object,
        time_regions: object,
    ) -> object:
        market_scene = self.market_scene_builder.build(
            visual_scene,
            semantic_scene,
            market_elements,
            price_regions,
            time_regions,
        )
        log_market_scene(self.logger, market_scene)
        return market_scene

    def _build_market_entities(self, market_scene: object) -> object:
        market_entities = self.market_entity_builder.build(market_scene)
        log_market_entities(self.logger, market_entities)
        return market_entities

    def _build_market_entity_registry(self, market_entities: object) -> object:
        registry = self.market_entity_registry_builder.build(market_entities)
        log_market_entity_registry(self.logger, registry)
        storage_path = self.market_entity_storage.resolve(registry.id)
        self.logger.info("Market Entity Storage caminho: %s", storage_path)
        return registry

    def _validate_market_entities(self, market_entities: object) -> object:
        validation = self.market_entity_validator.validate(market_entities)
        log_market_entity_validation(self.logger, validation)
        return validation

    def _build_market_structure(
        self,
        visual_snapshot: object,
        market_scene: object,
        market_entities: object,
        market_entity_registry: object,
        ocr_result: object,
    ) -> object:
        market_structure = self.market_structure_builder.build(
            visual_snapshot,
            market_scene,
            market_entities,
            market_entity_registry,
            ocr_result,
        )
        log_market_structure(self.logger, market_structure)
        return market_structure

    def _validate_market_structure(self, market_structure: object) -> object:
        validation = self.market_structure_validator.validate(market_structure)
        log_market_structure_validation(self.logger, validation)
        return validation

    def _detect_patterns(self, market_structure: object) -> object:
        patterns = self.pattern_detector.detect(market_structure)
        log_pattern_detector(self.logger, patterns)
        return patterns

    def _build_pattern_registry(self, patterns: object) -> object:
        registry = self.pattern_registry_builder.build(patterns)
        log_pattern_registry(self.logger, registry)
        return registry

    def _validate_patterns(self, patterns: object) -> object:
        validation = self.pattern_validator.validate(patterns)
        log_pattern_validation(self.logger, validation)
        return validation

    def _build_pattern_scene(
        self,
        market_structure: object,
        pattern_registry: object,
        patterns: object,
    ) -> object:
        pattern_scene = self.pattern_scene_builder.build(
            market_structure,
            pattern_registry,
            patterns,
        )
        log_pattern_scene(self.logger, pattern_scene)
        return pattern_scene

    def _classify_patterns(self, pattern_scene: object) -> object:
        classifications = self.pattern_classifier.classify(pattern_scene)
        log_pattern_classification(
            self.logger,
            PatternClassifierRegistry(classifications),
        )
        return classifications

    def _build_pattern_classification_registry(self, classifications: object) -> object:
        return PatternClassifierRegistry(tuple(classifications))

    def _build_pattern_context(
        self,
        pattern_scene: object,
        market_structure: object,
        visual_snapshot: object,
    ) -> object:
        context = self.pattern_context_builder.build(
            pattern_scene,
            market_structure,
            visual_snapshot,
        )
        log_pattern_context(self.logger, context)
        return context

    def _build_pattern_analysis(
        self,
        pattern_scene: object,
        pattern_context: object,
        classification_registry: object,
    ) -> object:
        analysis = self.pattern_analysis_builder.build(
            pattern_scene,
            pattern_context,
            classification_registry,
        )
        log_pattern_analysis(self.logger, analysis)
        return analysis

    def _validate_pattern_analysis(self, analysis: object) -> object:
        validation = self.pattern_analysis_validator.validate(analysis)
        log_pattern_analysis_validation(self.logger, validation)
        return validation

    def _build_intelligence_context(
        self,
        pattern_analysis: object,
        market_structure: object,
        visual_snapshot: object,
    ) -> object:
        context = self.intelligence_context_builder.build(
            pattern_analysis,
            market_structure,
            visual_snapshot,
        )
        log_intelligence_context(self.logger, context)
        return context

    def _validate_intelligence_context(self, context: object) -> object:
        validation = self.intelligence_context_validator.validate(context)
        log_intelligence_context_validation(self.logger, validation)
        return validation

    def _build_market_hypotheses(self, intelligence_context: object) -> object:
        hypothesis_score = self._default_hypothesis_score()
        hypotheses = self.market_hypothesis_builder.build(
            intelligence_context,
            hypothesis_score,
        )
        evaluated_scores = self.hypothesis_evaluator.evaluate(hypotheses)
        log_hypothesis_evaluator(self.logger, evaluated_scores)
        registry = self.market_hypothesis_registry(
            id=f"market_hypothesis_registry:{intelligence_context.id}",
            source_intelligence_context_id=intelligence_context.id,
            source_pattern_analysis_id=intelligence_context.source_pattern_analysis_id,
            source_market_structure_id=intelligence_context.source_market_structure_id,
            source_market_scene_id=intelligence_context.source_market_scene_id,
            source_visual_scene_id=intelligence_context.source_visual_scene_id,
            source_frame=intelligence_context.source_frame,
            created_at=hypotheses.created_at,
            hypotheses=hypotheses.hypotheses,
            metadata={"score_count": len(evaluated_scores)},
        )
        log_market_hypothesis(self.logger, hypotheses)
        log_market_hypothesis_registry(self.logger, registry)
        return hypotheses

    def _default_hypothesis_score(self) -> object:
        return HypothesisScore(
            value=1.0,
            rule="structural_hypothesis_rule",
            confidence=1.0,
            status="STRUCTURAL_READY",
        )

    def _evaluate_hypotheses(self, hypotheses: object) -> tuple[object, ...]:
        return self.hypothesis_evaluator.evaluate(hypotheses)

    def _build_intelligence_snapshot(
        self,
        market_structure: object,
        pattern_analysis: object,
        intelligence_context: object,
        market_hypotheses: object,
    ) -> object:
        return self.intelligence_snapshot_builder.build(
            market_structure,
            pattern_analysis,
            intelligence_context,
            market_hypotheses,
        )

    def _build_signals(self, intelligence_snapshot: object) -> object:
        return self.signal_builder.build(intelligence_snapshot)

    def _build_signal_registry(self, signals: object) -> object:
        registry = self.signal_registry(
            id=f"signal_registry:{signals.source_intelligence_snapshot_id}",
            source_intelligence_snapshot_id=signals.source_intelligence_snapshot_id,
            source_market_structure_id=signals.source_market_structure_id,
            source_pattern_analysis_id=signals.source_pattern_analysis_id,
            source_market_scene_id=signals.source_market_scene_id,
            source_visual_scene_id=signals.source_visual_scene_id,
            source_frame=signals.source_frame,
            created_at=signals.created_at,
            signals=signals.signals,
            metadata={"ai": False, "llm": False, "decision_making": False},
        )
        return registry

    def _validate_signals(self, signals: object) -> object:
        return self.signal_validator.validate(signals)

    def _score_signals(self, signals: object) -> tuple[object, ...]:
        return self.signal_scorer.score(signals)

    def _build_strategy_readiness_snapshot(
        self,
        pattern_analysis: object,
        intelligence_snapshot: object,
        market_hypotheses: object,
        signals: object,
        signal_scores: tuple[object, ...],
    ) -> object:
        return self.strategy_readiness_snapshot_builder.build(
            pattern_analysis,
            intelligence_snapshot,
            market_hypotheses,
            signals,
            signal_scores,
        )


    def _is_valid_broker_window(self, broker_state: object) -> bool:
        metadata = getattr(broker_state, "metadata", {}) or {}
        if bool(metadata.get("broker_window_valid")):
            return True

        title = str(getattr(broker_state, "title", "") or "")
        if not title or self._is_runtime_window_blocked(title):
            return False

        asset = self._normalize_runtime_asset("UNKNOWN", title, "")
        price = self._extract_runtime_price_from_title(title, asset)
        return self._is_runtime_asset_allowed(asset) and self._is_runtime_price_allowed(price, asset)

    def _handle_ignored_broker_window(
        self,
        *,
        session: object,
        broker_state: object,
        timeframe: str,
        live_start: float,
    ) -> dict[str, object]:
        """Skip capture when the active window is not a broker surface."""
        metadata = getattr(broker_state, "metadata", {}) or {}
        reason = str(
            metadata.get("ignore_reason")
            or "Janela ignorada: janela ativa não é corretora"
        )
        self.logger.warning(reason)

        runtime_dir = self.config.resolve_path("data") / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().astimezone().isoformat()
        payload = {
            "status": "IGNORED_WINDOW",
            "source": "live_once",
            "session_id": session.session_id,
            "timestamp": timestamp,
            "window_title": getattr(broker_state, "title", "UNKNOWN"),
            "asset": "UNKNOWN",
            "price": "UNKNOWN",
            "price_value": None,
            "time": "UNKNOWN",
            "balance": "UNKNOWN",
            "payout": "UNKNOWN",
            "trade_value": "UNKNOWN",
            "duration": "UNKNOWN",
            "timeframe": timeframe,
            "confidence": 0.0,
            "unknown_fields": ["window", "asset", "price"],
            "message": reason,
            "reason": reason,
            "capture_skipped": True,
            "broker_window": broker_state.to_dict(),
        }

        runtime_path = runtime_dir / "last_live_reading.json"
        runtime_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._append_rejected_runtime_live_reading(
            runtime_dir=runtime_dir,
            payload=payload,
            rejection_reasons=["invalid_broker_window"],
        )

        report = LiveValidationReport(
            session_id=session.session_id,
            total_captures=0,
            fields_detected=(),
            unknown_fields=("window", "asset", "price"),
            ocr_confidence=0.0,
            total_time_ms=round((perf_counter() - live_start) * 1000, 3),
            status="BROKER_WINDOW_IGNORED",
            readings=(),
            metadata={
                "window_title": getattr(broker_state, "title", "UNKNOWN"),
                "reason": reason,
                "capture_skipped": True,
                "observer_only": True,
            },
        )
        log_live_validation_report(self.logger, report)
        return {
            "report": report,
            "broker_state": broker_state,
            "runtime_payload": payload,
        }

    def _normalize_runtime_asset(
        self,
        asset: str,
        window_title: str,
        calibration_text: str = "",
    ) -> str:
        """Normalize runtime asset using OCR plus browser title."""
        text = f"{asset or ''} {window_title or ''} {calibration_text or ''}"

        known_assets = (
            ("Cafeina Index", r"Cafe[ií]na\s+Index"),
            ("Asia Composite Index", r"Asia\s+Composite\s+Index"),
            ("LATAM Index", r"LATAM\s+Index"),
        )

        for normalized, pattern in known_assets:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return normalized

        raw = str(asset or "").strip()
        if raw.upper() in ("", "UNKNOWN", "DATA", "NONE", "N/A", "-"):
            match = re.search(
                r"\b([A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+){0,3}\s+Index)\b",
                text,
                flags=re.IGNORECASE,
            )
            if match:
                return " ".join(match.group(1).split())

        return raw or "UNKNOWN"

    def _normalize_runtime_balance(
        self,
        balance: str,
        trade_value: str,
        calibration_text: str = "",
    ) -> str:
        """Keep OCR balance separated from trade value. Balance is still estimated."""
        raw = str(balance or "").strip()
        trade = str(trade_value or "").strip()

        if raw.upper() in ("", "UNKNOWN", "NONE", "N/A", "-"):
            return "UNKNOWN"

        if trade and trade != "UNKNOWN" and raw == trade:
            return "UNKNOWN"

        raw = raw.replace("RS", "R$")
        return raw

    def _extract_remaining_time(self, calibration_text: str) -> str:
        """Extract visible remaining time when OCR captures it."""
        text = calibration_text or ""

        match = re.search(r"\b\d{1,2}:\d{2}\b", text)
        if match:
            return match.group(0)

        match = re.search(r"\b\d+\s*seg\.?\b", text, flags=re.IGNORECASE)
        if match:
            return match.group(0).replace("seg", "seg.")

        return "UNKNOWN"

    def _build_expiration_suggestion(
        self,
        remaining_time: str,
        duration: str,
        timeframe: str,
    ) -> str:
        """Build simulated expiration guidance without trading execution."""
        if remaining_time and remaining_time != "UNKNOWN":
            return f"Aguardar confirmação; tempo restante visível: {remaining_time}"

        if duration and duration != "UNKNOWN":
            return f"Usar duração observada: {duration}"

        return f"Usar timeframe observado: {timeframe or 'M1'}"


    def _normalize_runtime_price(
        self,
        window_title: str,
        reading_price: str,
        calibration_text: str = "",
        asset: str = "",
    ) -> str:
        """Prefer broker-title price and reject noisy OCR numbers."""
        for value in (
            self._extract_runtime_price_from_title(window_title, asset),
            self._extract_runtime_price_from_labeled_text(calibration_text, asset),
            self._parse_runtime_number(reading_price),
        ):
            if self._is_runtime_price_allowed(value, asset):
                return self._format_runtime_price_value(value)

        return "UNKNOWN"

    def _extract_runtime_price_from_title(
        self,
        window_title: str,
        asset: str = "",
    ) -> float | None:
        title = window_title or ""
        title_asset = self._normalize_runtime_asset(asset or "UNKNOWN", title, "")
        effective_asset = title_asset if self._is_runtime_asset_allowed(title_asset) else asset
        patterns = (
            r"([0-9]{3,6}(?:[.,][0-9]{1,6})?)\s+(?:Cafe[ií]na|Asia\s+Composite|LATAM)\s+Index",
            r"(?:Cafe[ií]na|Asia\s+Composite|LATAM)\s+Index\s+([0-9]{3,6}(?:[.,][0-9]{1,6})?)",
            r"([0-9]{3,6}(?:[.,][0-9]{1,6})?)\s+[A-Za-zÀ-ÿ ]{2,40}\s+Index",
        )
        for pattern in patterns:
            match = re.search(pattern, title, flags=re.IGNORECASE)
            if not match:
                continue
            value = self._parse_runtime_number(match.group(1))
            if self._is_runtime_price_allowed(value, effective_asset):
                return value

        has_broker_or_asset = re.search(
            r"olymp\s*trade|olymptrade|cafe[ií]na\s+index|asia\s+composite\s+index|latam\s+index",
            title,
            flags=re.IGNORECASE,
        )
        if not has_broker_or_asset:
            return None

        for number in re.findall(r"\b[0-9]{3,6}(?:[.,][0-9]{1,6})?\b", title):
            value = self._parse_runtime_number(number)
            if self._is_runtime_price_allowed(value, effective_asset):
                return value

        return None

    def _extract_runtime_price_from_labeled_text(
        self,
        calibration_text: str,
        asset: str = "",
    ) -> float | None:
        for line in (calibration_text or "").splitlines():
            if not re.search(r"\b(price|preço|preco)\b", line, flags=re.IGNORECASE):
                continue
            value = self._parse_runtime_number(line)
            if self._is_runtime_price_allowed(value, asset):
                return value
        return None

    def _parse_runtime_number(self, value: object) -> float | None:
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip()
        if not text or text.upper() in ("UNKNOWN", "NONE", "N/A", "-"):
            return None

        match = re.search(r"-?\d+(?:[.,]\d+)?", text)
        if not match:
            return None

        number = match.group(0)
        if "," in number and "." in number:
            if number.rfind(",") > number.rfind("."):
                number = number.replace(".", "").replace(",", ".")
            else:
                number = number.replace(",", "")
        elif "," in number:
            number = number.replace(",", ".")

        try:
            return float(number)
        except ValueError:
            return None

    def _is_runtime_price_allowed(self, value: float | None, asset: str = "") -> bool:
        if value is None or value <= 0:
            return False

        if asset and not self._is_runtime_asset_allowed(asset):
            return False

        rounded = int(round(value))
        if rounded in {1, 3, 24, 25, 52, 85, 2026}:
            return False

        asset_text = (asset or "").lower()
        min_price = 100.0 if "latam" in asset_text else 1000.0
        if value < min_price:
            return False

        known_index = (
            "cafe" in asset_text
            or "asia composite" in asset_text
            or "latam" in asset_text
            or "index" in asset_text
        )
        if known_index and value < min_price:
            return False

        if ("cafe" in asset_text or "asia composite" in asset_text) and 1900 <= value <= 2100:
            return False

        return True

    def _is_runtime_asset_allowed(self, asset: str) -> bool:
        text = str(asset or "").strip()
        if text.upper() in ("", "UNKNOWN", "DATA", "NONE", "N/A", "-"):
            return False

        lowered = text.lower()
        if any(token in lowered for token in ("core/", "core\\", "codex", "powershell", "visual studio code")):
            return False
        return "index" in lowered

    def _is_runtime_window_blocked(self, window_title: str) -> bool:
        lowered = str(window_title or "").lower()
        if not lowered:
            return False
        blocked_markers = (
            "codex",
            "powershell",
            "pwsh",
            "visual studio code",
            "cmd.exe",
            "command prompt",
            "terminal",
            "predixai compact",
            "predixai trader mobile",
            "localhost:8766",
            "127.0.0.1:8766",
            "localhost:8765",
            "127.0.0.1:8765",
            "dashboard",
        )
        return any(marker in lowered for marker in blocked_markers)

    def _format_runtime_price_value(self, value: float | None) -> str:
        if value is None:
            return "UNKNOWN"
        return f"{value:.6f}".rstrip("0").rstrip(".")


    def _validate_runtime_live_reading(
        self,
        *,
        asset: str,
        payout: str,
        price_value: float | None,
        window_title: str = "",
    ) -> tuple[bool, list[str]]:
        """Validate whether a live reading can enter runtime history."""
        reasons: list[str] = []

        asset_text = str(asset or "").strip()
        if asset_text.upper() in ("", "UNKNOWN", "DATA", "NONE", "N/A", "-"):
            reasons.append("asset_unknown")
        elif not self._is_runtime_asset_allowed(asset_text):
            reasons.append("asset_invalid")

        if self._is_runtime_window_blocked(window_title):
            reasons.append("invalid_window")

        if price_value is None:
            reasons.append("price_value_missing")
        elif not self._is_runtime_price_allowed(price_value, asset):
            reasons.append("price_value_suspicious")

        # Payout ausente vira aviso indireto, mas não bloqueia preço + ativo válidos.
        return len(reasons) == 0, reasons

    def _append_rejected_runtime_live_reading(
        self,
        *,
        runtime_dir: Path,
        payload: dict,
        rejection_reasons: list[str],
    ) -> None:
        """Persist rejected runtime readings for audit without polluting the chart."""
        rejected_path = runtime_dir / "rejected_live_readings.json"
        if rejected_path.exists():
            try:
                rejected_payload = json.loads(rejected_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                rejected_payload = []
        else:
            rejected_payload = []

        if not isinstance(rejected_payload, list):
            rejected_payload = []

        rejected_entry = dict(payload)
        rejected_entry["status"] = "REJECTED"
        rejected_entry["rejection_reasons"] = rejection_reasons

        rejected_payload.append(rejected_entry)
        rejected_payload = rejected_payload[-3000:]
        rejected_path.write_text(
            json.dumps(rejected_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _build_live_validation_report(
        self,
        session: object,
        readings: tuple[object, ...],
        broker_state: object,
        total_time_ms: float,
    ) -> LiveValidationReport:
        fields_detected = tuple(
            field
            for field, value in {
                "asset": readings[-1].asset if readings else "UNKNOWN",
                "price": readings[-1].price if readings else "UNKNOWN",
                "time": readings[-1].time if readings else "UNKNOWN",
                "balance": readings[-1].balance if readings else "UNKNOWN",
                "payout": readings[-1].payout if readings else "UNKNOWN",
                "timeframe": readings[-1].timeframe if readings else "UNKNOWN",
            }.items()
            if value != "UNKNOWN"
        )
        unknown_fields = tuple(
            field
            for field, value in {
                "asset": readings[-1].asset if readings else "UNKNOWN",
                "price": readings[-1].price if readings else "UNKNOWN",
                "time": readings[-1].time if readings else "UNKNOWN",
                "balance": readings[-1].balance if readings else "UNKNOWN",
                "payout": readings[-1].payout if readings else "UNKNOWN",
                "timeframe": readings[-1].timeframe if readings else "UNKNOWN",
            }.items()
            if value == "UNKNOWN"
        )
        ocr_confidence = 0.0
        if readings:
            ocr_confidence = max(float(reading.confidence) for reading in readings)
        return LiveValidationReport(
            session_id=session.session_id,
            total_captures=len(readings),
            fields_detected=fields_detected,
            unknown_fields=unknown_fields,
            ocr_confidence=ocr_confidence,
            total_time_ms=total_time_ms,
            status="LIVE_VALIDATION_COMPLETED",
            readings=readings,
            metadata={
                "window_title": broker_state.title,
                "timeframe": session.timeframe,
                "captures_per_candle": session.captures_per_candle,
                "validation_candles": session.validation_candles,
            },
        )
