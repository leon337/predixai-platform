"""Application bootstrap for the PredixAI foundation."""

from __future__ import annotations

import importlib
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
    CandleSnapshotBuilder,
    CandleStatisticsBuilder,
    BrokerWindowDetector,
    FieldExtractor,
    FieldLocator,
    LiveCandleBenchmarkBuilder,
    LiveCaptureScheduler,
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
        self.live_validation_benchmark = LiveValidationBenchmark(
            enabled=self._live_validation_benchmark_enabled()
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

    def live_once(self) -> object:
        """Run one live validation candle without trading actions."""
        live_config = self.config.live if isinstance(self.config.live, dict) else {}
        timeframe = str(live_config.get("timeframe", "M1"))
        interval_seconds = int(live_config.get("capture_interval_seconds", 10))
        captures_per_candle = int(live_config.get("captures_per_candle", 6))
        validation_candles = int(live_config.get("validation_candles", 1))

        session = self.live_session_controller.start(
            timeframe=timeframe,
            capture_interval_seconds=interval_seconds,
            captures_per_candle=captures_per_candle,
            validation_candles=validation_candles,
        )
        log_live_session(self.logger, session)
        broker_state = self.broker_window_detector.detect()
        log_broker_window_state(self.logger, broker_state)

        live_start = perf_counter()
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
            metadata = self.capture_snapshot()
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
            capture_context = self.last_capture_context
            structured_ocr = capture_context.get("structured_ocr")
            ocr_confidence = float(getattr(structured_ocr, "average_confidence", 0.0))
            ocr_text = str(getattr(structured_ocr, "combined_text", ""))
            reading = self.live_market_reader.read(
                ocr_text=ocr_text,
                ocr_confidence=ocr_confidence,
                timeframe=timeframe,
            )
            log_live_market_reading(self.logger, reading)
            readings.append(reading)
            extraction = self.field_extractor.extract(reading, field_location_map)
            extraction_results.append(extraction)
            log_field_extraction_result(self.logger, extraction)
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
        self.events.record(
            "live.validation_completed",
            {
                **report.to_dict(),
                "candle_snapshot": candle_snapshot.to_dict(),
                "candle_statistics": candle_statistics.to_dict(),
                "live_candle_benchmark": live_candle_benchmark.benchmark.to_dict(),
            },
        )
        return {
            "report": report,
            "candle_snapshot": candle_snapshot,
            "candle_statistics": candle_statistics,
            "live_candle_benchmark": live_candle_benchmark.benchmark,
        }

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
