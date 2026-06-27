"""Technical logging for the PredixAI foundation."""

from __future__ import annotations

import logging
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from predixai.core.config import AppConfig

LOGGER_NAME = "predixai"


def configure_logger(config: AppConfig) -> logging.Logger:
    """Configure the technical logger using only standard-library logging."""
    logs_dir = config.resolve_path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_file = logs_dir / str(config.logging["technical_log_file"])
    level_name = str(config.logging.get("level", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    _reset_handlers(logger)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def log_startup(
    logger: logging.Logger,
    config: AppConfig,
    module_names: Iterable[str],
) -> None:
    """Record the startup context required by the foundation."""
    logger.info("PredixAI initialization started.")
    logger.info("Application: %s", config.name)
    logger.info("Version: %s", config.version)
    logger.info("Mode: %s", config.mode)
    logger.info("Environment: %s", config.environment)
    logger.info("Date/time: %s", datetime.now().astimezone().isoformat())
    logger.info("Operating system: %s", platform.platform())
    logger.info("Python: %s", sys.version.replace("\n", " "))
    logger.info("Loaded modules: %s", ", ".join(module_names))
    logger.info("PredixAI initialization finished.")


def log_perception(logger: logging.Logger, snapshot: Any) -> None:
    """Record Perception Engine foundation metadata."""
    environment = snapshot.environment
    windows = snapshot.windows
    active_window = windows.active_window.title if windows.active_window else "none"

    logger.info(
        "Screen resolution: %sx%s",
        environment.resolution.width,
        environment.resolution.height,
    )
    logger.info("Screen scale: %s%%", environment.scale_percent)
    logger.info("Screen operating system: %s", environment.operating_system)
    logger.info("Monitor count: %s", environment.monitor_count)
    logger.info("Primary monitor: %s", environment.primary_monitor)
    logger.info(
        "Screen work area: x=%s y=%s width=%s height=%s",
        environment.work_area.left,
        environment.work_area.top,
        environment.work_area.width,
        environment.work_area.height,
    )
    logger.info("Windows found: %s", len(windows.windows))
    logger.info("Active window: %s", active_window)


def log_capture_engine(logger: logging.Logger, status: Any) -> None:
    """Record Capture Engine bootstrap metadata."""
    logger.info("Capture Engine iniciado.")
    logger.info("Diretório das capturas: %s", status.storage.output_directory)
    logger.info("Formato: %s", status.storage.image_format.upper())
    logger.info("Compressão: %s", status.storage.compression)


def log_manual_snapshot(logger: logging.Logger, metadata: Any) -> None:
    """Record one manual snapshot action."""
    logger.info("Início da sessão de captura: %s", metadata.session_id)
    logger.info("Horário da captura: %s", metadata.captured_at)
    logger.info(
        "Resolução da captura: %sx%s",
        metadata.resolution_width,
        metadata.resolution_height,
    )
    logger.info("Arquivo da captura: %s", metadata.file_path)
    logger.info("Tamanho do arquivo: %s bytes", metadata.file_size_bytes)


def log_vision_frame(logger: logging.Logger, snapshot: Any, frame: Any) -> None:
    """Record one Vision Engine frame metadata action."""
    logger.info("Vision Engine iniciado")
    logger.info("Frame recebido: %s", snapshot.file_path)
    logger.info(
        "Arquivo validado: %s (%sx%s, %s bytes)",
        frame.filename,
        frame.width,
        frame.height,
        frame.file_size,
    )
    logger.info("SHA256 calculado: %s", frame.sha256)
    logger.info("Frame criado: %s", frame.filename)
    logger.info("Metadados registrados: %s", frame.to_dict())


def log_image_buffer(logger: logging.Logger, image_buffer: Any) -> None:
    """Record Image Loader metadata without visual interpretation."""
    logger.info("Image Loader iniciado")
    logger.info("PNG carregado em memória: %s", image_buffer.file_path)
    logger.info("tamanho em bytes: %s", image_buffer.byte_size)
    logger.info("largura: %s", image_buffer.width)
    logger.info("altura: %s", image_buffer.height)
    logger.info("SHA256: %s", image_buffer.sha256)
    logger.info("ImageBuffer criado: %s", image_buffer.to_dict())


def log_roi_registry(logger: logging.Logger, registry: Any) -> None:
    """Record ROI registry metadata without using image regions."""
    logger.info("ROI Manager iniciado")
    logger.info("ROI Registry carregado")
    logger.info("%s ROI registrada", registry.count)
    for roi in registry.rois:
        if roi.id == "FULL_SCREEN":
            logger.info("ROI FULL_SCREEN registrada")
            logger.info("FULL_SCREEN registrada")


def log_region_registry(logger: logging.Logger, registry: Any) -> None:
    """Record logical Region Mapping metadata."""
    logger.info("Region Manager iniciado")
    logger.info("Screen Profile carregado: %s", registry.profile_id)
    logger.info("Region Binding iniciado")
    logger.info("Region Registry carregado")
    logger.info("Region Validation iniciado")
    for region in registry.regions:
        logger.info("Região registrada: %s", region.id)
        logger.info("Região serializada: %s", region.to_dict())
        logger.info("Região validada: %s", region.id)
        if region.id == "FULL_SCREEN":
            logger.info("Região FULL_SCREEN vinculada")
            logger.info("Região FULL_SCREEN registrada")
    logger.info("Total de regiões válidas: %s", registry.count)
    logger.info("Total de regiões registradas: %s", registry.count)


def log_region_mapping_started(logger: logging.Logger) -> None:
    """Record the beginning of Region Mapping."""
    logger.info("Region Mapping iniciado")


def log_region_mapping_finished(logger: logging.Logger) -> None:
    """Record the end of Region Mapping."""
    logger.info("Region Mapping finalizado")


def log_roi_crop(logger: logging.Logger, roi_crop: Any) -> None:
    """Record ROI crop metadata without pixel extraction."""
    logger.info("ROI Crop Engine iniciado")
    logger.info("ROI validada: %s", roi_crop.roi_id)
    logger.info("ROICrop criado: %s", roi_crop.to_dict())


def log_roi_crop_export(logger: logging.Logger, roi_export: Any) -> None:
    """Record ROI crop export metadata without visual interpretation."""
    logger.info("ROI Crop Export iniciado")
    logger.info("ROI exportada: %s", roi_export.roi_id)
    logger.info("caminho do PNG exportado: %s", roi_export.output_path)
    logger.info("tamanho do arquivo: %s bytes", roi_export.file_size)


def log_ocr_pipeline(logger: logging.Logger, ocr_result: Any) -> None:
    """Record OCR foundation metadata without text extraction."""
    logger.info("Pipeline OCR iniciado")
    logger.info("OCR Engine iniciado")
    logger.info("OCR Cache iniciado")
    logger.info("OCR Cache hit: %s", ocr_result.cache_hit)
    logger.info("OCR SHA256: %s", ocr_result.image_sha256)
    benchmark = ocr_result.benchmark
    logger.info("OCR Benchmark iniciado")
    logger.info(
        "OCR tempo de processamento: %s ms",
        benchmark.get("provider_processing_time_ms", 0.0),
    )
    logger.info(
        "OCR pico de memória: %s KB",
        benchmark.get("peak_memory_kb", 0.0),
    )
    logger.info("OCR tamanho do texto: %s", benchmark.get("text_length", 0))
    logger.info("OCR status do benchmark: %s", benchmark.get("status", ""))
    logger.info("OCR Benchmark finalizado")
    logger.info("OCR Provider Registry iniciado")
    logger.info("Provider Registry iniciado")
    for provider_name in ocr_result.registered_providers:
        logger.info("Provider %s registrado", provider_name)
    logger.info("Provider selecionado: %s", ocr_result.selected_provider)
    logger.info("Provider %s selecionado", ocr_result.selected_provider)
    logger.info("Imagem recebida: %s", ocr_result.image_path)
    logger.info("OCR Provider carregado: %s", ocr_result.provider_name)
    logger.info("OCR Validation iniciado")
    if ocr_result.provider == "tesseract":
        logger.info("Imagem enviada ao Tesseract Provider: %s", ocr_result.image_path)
        logger.info("Tesseract Provider iniciado")
        logger.info("Versão detectada: %s", ocr_result.provider_version)
        logger.info("Idioma configurado: %s", ocr_result.provider_language)
        logger.info("Idioma utilizado: %s", ocr_result.language_used)
        logger.info("Provider pronto")
        logger.info("OCR executado (Tesseract)")
    else:
        logger.info("Imagem enviada ao Mock Provider: %s", ocr_result.image_path)
        logger.info("OCR executado (Mock)")
    logger.info("Confiança mínima configurada: %s", ocr_result.min_confidence)
    logger.info("Confiança OCR: %s", ocr_result.confidence)
    logger.info("Idioma válido: %s", ocr_result.language_valid)
    logger.info("Confiança válida: %s", ocr_result.confidence_valid)
    for warning in ocr_result.validation_warnings:
        logger.warning("Aviso de validação OCR: %s", warning)
    for error in ocr_result.validation_errors:
        logger.error("Erro de validação OCR: %s", error)
    logger.info("OCR Validation finalizado")
    logger.info("Resultado criado: %s", ocr_result.to_dict())
    logger.info("OCRResult criado: %s", ocr_result.to_dict())
    if ocr_result.text_extraction_enabled:
        logger.info("Texto extraído pelo OCR: %s", ocr_result.text)
    else:
        logger.info("OCR continua sem extração de texto")
    logger.info("Pipeline OCR pronto: %s", ocr_result.to_dict())
    logger.info("Pipeline finalizado")
    logger.info("Pipeline OCR finalizado")


def log_ocr_parser(logger: logging.Logger, parsed_text: Any) -> None:
    """Record OCR parser foundation metadata."""
    logger.info("OCR Parser iniciado")
    logger.info("Texto OCR recebido: %s caracteres", len(parsed_text.raw_text))
    logger.info("Blocos OCR criados: %s", parsed_text.block_count)
    logger.info("OCR Parser finalizado: %s", parsed_text.to_dict())


def log_region_text_mapping(logger: logging.Logger, mapping: Any) -> None:
    """Record Region Text Mapping metadata."""
    logger.info("Region Text Mapping iniciado")
    for region_text in mapping.texts:
        logger.info("Texto associado à região %s", region_text.region_id)
    logger.info("Total de textos regionais: %s", mapping.count)
    logger.info("Region Text Mapping finalizado: %s", mapping.to_dict())


def log_structured_ocr(logger: logging.Logger, structured_ocr: Any) -> None:
    """Record Structured OCR metadata."""
    logger.info("Structured OCR iniciado")
    logger.info("Regiões estruturadas: %s", structured_ocr.total_regions)
    logger.info("Blocos estruturados: %s", structured_ocr.total_blocks)
    logger.info("Confiança média estruturada: %s", structured_ocr.average_confidence)
    logger.info("Structured OCR Result criado: %s", structured_ocr.to_dict())


def log_visual_snapshot(logger: logging.Logger, visual_snapshot: Any) -> None:
    """Record Visual Snapshot metadata."""
    logger.info("Visual Snapshot iniciado")
    logger.info("Visual Snapshot sessão: %s", visual_snapshot.session_id)
    logger.info("Visual Snapshot frame: %s", visual_snapshot.source_frame)
    logger.info(
        "Visual Snapshot regiões: %s",
        visual_snapshot.structured_ocr.total_regions,
    )
    logger.info(
        "Visual Snapshot blocos: %s",
        visual_snapshot.structured_ocr.total_blocks,
    )
    logger.info("Visual Snapshot criado: %s", visual_snapshot.to_dict())
    logger.info("Visual Snapshot finalizado")


def log_visual_benchmark(logger: logging.Logger, benchmark: Any) -> None:
    """Record Visual Benchmark metadata."""
    logger.info("Visual Benchmark iniciado")
    logger.info("Visual Benchmark status: %s", benchmark.status)
    logger.info(
        "Visual Benchmark tempo de processamento: %s ms",
        benchmark.processing_time_ms,
    )
    logger.info("Visual Benchmark pico de memória: %s KB", benchmark.peak_memory_kb)
    logger.info("Visual Benchmark regiões: %s", benchmark.region_count)
    logger.info("Visual Benchmark blocos: %s", benchmark.block_count)
    logger.info("Visual Benchmark tamanho do texto: %s", benchmark.text_length)
    logger.info("Visual Benchmark finalizado: %s", benchmark.to_dict())


def log_screen_elements(logger: logging.Logger, screen_elements: Any) -> None:
    """Record Screen Elements metadata."""
    logger.info("Screen Elements Foundation iniciado")
    logger.info("Elementos visuais criados: %s", screen_elements.count)
    for element in screen_elements.elements:
        logger.info("Elemento visual registrado: %s", element.id)
    logger.info("Screen Elements Foundation finalizado: %s", screen_elements.to_dict())


def log_screen_layout(logger: logging.Logger, screen_layout: Any) -> None:
    """Record Screen Layout metadata."""
    logger.info("Screen Layout Builder iniciado")
    logger.info("Layout estruturado criado: %s", screen_layout.id)
    logger.info("Nos de layout: %s", screen_layout.node_count)
    logger.info("Hierarquia visual preservada")
    logger.info("Screen Layout Builder finalizado: %s", screen_layout.to_dict())


def log_screen_object_registry(logger: logging.Logger, registry: Any) -> None:
    """Record Screen Object Registry metadata."""
    logger.info("Screen Object Registry iniciado")
    logger.info("Objetos registrados: %s", registry.count)
    for screen_object in registry.objects:
        logger.info("Objeto visual registrado: %s", screen_object.id)
    logger.info("Screen Object Registry finalizado: %s", registry.to_dict())


def log_visual_scene(logger: logging.Logger, visual_scene: Any) -> None:
    """Record Visual Scene metadata."""
    logger.info("Visual Scene Builder iniciado")
    logger.info("Visual Scene criada: %s", visual_scene.id)
    logger.info("Visual Scene objetos: %s", visual_scene.object_count)
    logger.info("Visual Scene elementos: %s", visual_scene.element_count)
    logger.info("Visual Scene regioes: %s", visual_scene.region_count)
    logger.info("Visual Scene finalizado: %s", visual_scene.to_dict())


def log_visual_scene_benchmark(logger: logging.Logger, benchmark: Any) -> None:
    """Record Visual Scene Benchmark metadata."""
    logger.info("Visual Scene Benchmark iniciado")
    logger.info("Visual Scene Benchmark status: %s", benchmark.status)
    logger.info(
        "Visual Scene Benchmark tempo de processamento: %s ms",
        benchmark.processing_time_ms,
    )
    logger.info(
        "Visual Scene Benchmark pico de memoria: %s KB",
        benchmark.peak_memory_kb,
    )
    logger.info("Visual Scene Benchmark objetos: %s", benchmark.object_count)
    logger.info("Visual Scene Benchmark elementos: %s", benchmark.element_count)
    logger.info("Visual Scene Benchmark regioes: %s", benchmark.region_count)
    logger.info("Visual Scene Benchmark finalizado: %s", benchmark.to_dict())


def log_semantic_elements(logger: logging.Logger, semantic_elements: Any) -> None:
    """Record Semantic Element foundation metadata."""
    logger.info("Semantic Element Foundation iniciado")
    logger.info("Entidades semanticas criadas: %s", semantic_elements.count)
    for element in semantic_elements.elements:
        logger.info("Semantic Element registrado: %s", element.id)
    logger.info("Semantic Element Foundation finalizado: %s", semantic_elements.to_dict())


def log_semantic_label_mapping(logger: logging.Logger, mapping: Any) -> None:
    """Record deterministic Semantic Label Mapper metadata."""
    logger.info("Semantic Label Mapper iniciado")
    logger.info("Labels semanticos mapeados: %s", mapping.count)
    for label in mapping.labels:
        logger.info("Semantic Label mapeado: %s", label.label)
    logger.info("Semantic Label Mapper finalizado: %s", mapping.to_dict())


def log_semantic_scene(logger: logging.Logger, semantic_scene: Any) -> None:
    """Record Semantic Scene metadata."""
    logger.info("Semantic Scene Builder iniciado")
    logger.info("Semantic Scene criada: %s", semantic_scene.id)
    logger.info("Semantic Scene entidades: %s", semantic_scene.entity_count)
    logger.info("Semantic Scene labels: %s", semantic_scene.label_count)
    logger.info("Semantic Scene regioes: %s", semantic_scene.region_count)
    logger.info("Semantic Scene Builder finalizado: %s", semantic_scene.to_dict())


def log_semantic_registry(logger: logging.Logger, registry: Any) -> None:
    """Record Semantic Registry metadata."""
    logger.info("Semantic Registry iniciado")
    logger.info("Entidades semanticas registradas: %s", registry.count)
    logger.info("Labels registrados: %s", registry.label_count)
    for entity in registry.entities:
        logger.info("Semantic Entity registrada: %s", entity.id)
    logger.info("Semantic Registry finalizado: %s", registry.to_dict())


def log_semantic_benchmark(logger: logging.Logger, benchmark: Any) -> None:
    """Record Semantic Benchmark metadata."""
    logger.info("Semantic Benchmark iniciado")
    logger.info("Semantic Benchmark status: %s", benchmark.status)
    logger.info(
        "Semantic Benchmark tempo de processamento: %s ms",
        benchmark.processing_time_ms,
    )
    logger.info("Semantic Benchmark pico de memoria: %s KB", benchmark.peak_memory_kb)
    logger.info("Semantic Benchmark entidades: %s", benchmark.entity_count)
    logger.info("Semantic Benchmark labels: %s", benchmark.label_count)
    logger.info("Semantic Benchmark regioes: %s", benchmark.region_count)
    logger.info("Semantic Benchmark finalizado: %s", benchmark.to_dict())


def log_market_elements(logger: logging.Logger, market_elements: Any) -> None:
    """Record Market Element foundation metadata."""
    logger.info("Market Element Foundation iniciado")
    logger.info("Elementos de mercado criados: %s", market_elements.count)
    logger.info("Entidades de mercado criadas: %s", market_elements.entity_count)
    for element in market_elements.elements:
        logger.info("Market Element registrado: %s", element.id)
        logger.info("Market Element tipo: %s", element.market_type)
    logger.info("Market Element Foundation finalizado: %s", market_elements.to_dict())


def log_price_region_mapping(logger: logging.Logger, mapping: Any) -> None:
    """Record structural Price Region Mapper metadata."""
    logger.info("Price Region Mapper iniciado")
    logger.info("Regioes de preco mapeadas: %s", mapping.count)
    for region in mapping.regions:
        logger.info("Price Region registrada: %s", region.id)
    logger.info("Price Region Mapper finalizado: %s", mapping.to_dict())


def log_time_region_mapping(logger: logging.Logger, mapping: Any) -> None:
    """Record structural Time Region Mapper metadata."""
    logger.info("Time Region Mapper iniciado")
    logger.info("Regioes de tempo mapeadas: %s", mapping.count)
    for region in mapping.regions:
        logger.info("Time Region registrada: %s", region.id)
    logger.info("Time Region Mapper finalizado: %s", mapping.to_dict())


def log_market_scene(logger: logging.Logger, market_scene: Any) -> None:
    """Record Market Scene metadata."""
    logger.info("Market Scene Builder iniciado")
    logger.info("Market Scene criada: %s", market_scene.id)
    logger.info("Market Scene elementos: %s", market_scene.element_count)
    logger.info("Market Scene entidades: %s", market_scene.entity_count)
    logger.info("Market Scene regioes: %s", market_scene.region_count)
    logger.info("Market Scene regioes de preco: %s", market_scene.price_region_count)
    logger.info("Market Scene regioes de tempo: %s", market_scene.time_region_count)
    logger.info("Market Scene Builder finalizado: %s", market_scene.to_dict())


def log_market_benchmark(logger: logging.Logger, benchmark: Any) -> None:
    """Record Market Benchmark metadata."""
    logger.info("Market Benchmark iniciado")
    logger.info("Market Benchmark status: %s", benchmark.status)
    logger.info(
        "Market Benchmark tempo de processamento: %s ms",
        benchmark.processing_time_ms,
    )
    logger.info("Market Benchmark pico de memoria: %s KB", benchmark.peak_memory_kb)
    logger.info("Market Benchmark elementos: %s", benchmark.element_count)
    logger.info("Market Benchmark regioes: %s", benchmark.region_count)
    logger.info("Market Benchmark entidades: %s", benchmark.entity_count)
    logger.info(
        "Market Benchmark regioes de preco: %s",
        benchmark.price_region_count,
    )
    logger.info(
        "Market Benchmark regioes de tempo: %s",
        benchmark.time_region_count,
    )
    logger.info("Market Benchmark finalizado: %s", benchmark.to_dict())


def log_market_entities(logger: logging.Logger, market_entities: Any) -> None:
    """Record Market Entity foundation metadata."""
    logger.info("Market Entity Foundation iniciado")
    logger.info("Entidades de mercado criadas: %s", market_entities.count)
    for entity in market_entities.entities:
        logger.info("Market Entity registrada: %s", entity.id)
        logger.info("Market Entity tipo: %s", entity.entity_type)
    logger.info("Market Entity Foundation finalizado: %s", market_entities.to_dict())


def log_market_entity_validation(logger: logging.Logger, validation: Any) -> None:
    """Record Market Entity validation metadata."""
    logger.info("Market Entity Validator iniciado")
    logger.info("Market Entity valida: %s", validation.valid)
    logger.info("Market Entity validadas: %s", validation.entity_count)
    logger.info("Market Entity regioes validadas: %s", validation.region_count)
    for issue in validation.issues:
        logger.warning("Market Entity issue: %s", issue)
    logger.info("Market Entity Validator finalizado: %s", validation.to_dict())


def log_market_entity_registry(logger: logging.Logger, registry: Any) -> None:
    """Record market entity registry metadata."""
    logger.info("Market Entity Registry iniciado")
    logger.info("Market Entity Registry entidades: %s", registry.count)
    logger.info("Market Entity Registry regioes: %s", registry.region_count)
    logger.info("Market Entity Storage definido: %s", getattr(registry, "metadata", {}))
    logger.info("Market Entity Registry finalizado: %s", registry.to_dict())


def log_market_structure(logger: logging.Logger, market_structure: Any) -> None:
    """Record Market Structure metadata."""
    logger.info("Market Structure Builder iniciado")
    logger.info("Market Structure criada: %s", market_structure.id)
    logger.info("Market Structure entidades: %s", market_structure.entity_count)
    logger.info("Market Structure regioes: %s", market_structure.region_count)
    logger.info("Market Structure elementos: %s", market_structure.element_count)
    logger.info("Market Structure Snapshot regioes: %s", market_structure.snapshot_region_count)
    logger.info("Market Structure Builder finalizado: %s", market_structure.to_dict())


def log_market_structure_validation(logger: logging.Logger, validation: Any) -> None:
    """Record Market Structure validation metadata."""
    logger.info("Market Structure Validator iniciado")
    logger.info("Market Structure valida: %s", validation.valid)
    logger.info("Market Structure entidades validadas: %s", validation.entity_count)
    logger.info("Market Structure regioes validadas: %s", validation.region_count)
    logger.info("Market Structure elementos validados: %s", validation.element_count)
    for issue in validation.issues:
        logger.warning("Market Structure issue: %s", issue)
    logger.info("Market Structure Validator finalizado: %s", validation.to_dict())


def log_market_structure_benchmark(logger: logging.Logger, benchmark: Any) -> None:
    """Record Market Structure benchmark metadata."""
    logger.info("Market Structure Benchmark iniciado")
    logger.info("Market Structure Benchmark status: %s", benchmark.status)
    logger.info(
        "Market Structure Benchmark tempo de processamento: %s ms",
        benchmark.processing_time_ms,
    )
    logger.info(
        "Market Structure Benchmark pico de memoria: %s KB",
        benchmark.peak_memory_kb,
    )
    logger.info("Market Structure Benchmark entidades: %s", benchmark.entity_count)
    logger.info("Market Structure Benchmark regioes: %s", benchmark.region_count)
    logger.info("Market Structure Benchmark elementos: %s", benchmark.element_count)
    logger.info("Market Structure Benchmark finalizado: %s", benchmark.to_dict())


def log_pattern_detector(logger: logging.Logger, patterns: Any) -> None:
    """Record structural pattern detection metadata."""
    logger.info("Pattern Detector iniciado")
    logger.info("Patterns detectados: %s", patterns.count)
    logger.info("Pattern Detector finalizado: %s", patterns.to_dict())


def log_pattern_registry(logger: logging.Logger, registry: Any) -> None:
    """Record structural pattern registry metadata."""
    logger.info("Pattern Registry iniciado")
    logger.info("Pattern Registry patterns: %s", registry.count)
    logger.info("Pattern Registry regioes: %s", registry.region_count)
    logger.info("Pattern Registry finalizado: %s", registry.to_dict())


def log_pattern_validation(logger: logging.Logger, validation: Any) -> None:
    """Record structural pattern validation metadata."""
    logger.info("Pattern Validator iniciado")
    logger.info("Pattern valida: %s", validation.valid)
    logger.info("Pattern validadas: %s", validation.pattern_count)
    logger.info("Pattern regioes validadas: %s", validation.region_count)
    for issue in validation.issues:
        logger.warning("Pattern issue: %s", issue)
    logger.info("Pattern Validator finalizado: %s", validation.to_dict())


def log_pattern_scene(logger: logging.Logger, pattern_scene: Any) -> None:
    """Record structural pattern scene metadata."""
    logger.info("Pattern Scene Builder iniciado")
    logger.info("Pattern Scene criada: %s", pattern_scene.id)
    logger.info("Pattern Scene patterns: %s", pattern_scene.pattern_count)
    logger.info("Pattern Scene entidades: %s", pattern_scene.entity_count)
    logger.info("Pattern Scene regioes: %s", pattern_scene.region_count)
    logger.info("Pattern Scene Builder finalizado: %s", pattern_scene.to_dict())


def log_pattern_benchmark(logger: logging.Logger, benchmark: Any) -> None:
    """Record structural pattern benchmark metadata."""
    logger.info("Pattern Benchmark iniciado")
    logger.info("Pattern Benchmark status: %s", benchmark.status)
    logger.info(
        "Pattern Benchmark tempo de processamento: %s ms",
        benchmark.processing_time_ms,
    )
    logger.info("Pattern Benchmark pico de memoria: %s KB", benchmark.peak_memory_kb)
    logger.info("Pattern Benchmark patterns: %s", benchmark.pattern_count)
    logger.info("Pattern Benchmark entidades: %s", benchmark.entity_count)
    logger.info("Pattern Benchmark regioes: %s", benchmark.region_count)
    logger.info("Pattern Benchmark finalizado: %s", benchmark.to_dict())


def log_pattern_classification(logger: logging.Logger, registry: Any) -> None:
    """Record deterministic pattern classification metadata."""
    logger.info("Pattern Classifier iniciado")
    logger.info("Classificacoes de padrao: %s", registry.count)
    logger.info("Pattern Classifier finalizado: %s", registry.to_dict())


def log_pattern_context(logger: logging.Logger, context: Any) -> None:
    """Record structural pattern context metadata."""
    logger.info("Pattern Context Builder iniciado")
    logger.info("Pattern Context criado: %s", context.id)
    logger.info("Pattern Context finalizado: %s", context.to_dict())


def log_pattern_analysis(logger: logging.Logger, analysis: Any) -> None:
    """Record pattern analysis metadata."""
    logger.info("Pattern Analyzer iniciado")
    logger.info("Pattern Analysis criada: %s", analysis.id)
    logger.info("Pattern Analysis padroes: %s", analysis.pattern_count)
    logger.info("Pattern Analysis classificacoes: %s", analysis.classification_count)
    logger.info("Pattern Analysis contextos: %s", analysis.context_count)
    logger.info("Pattern Analysis finalizado: %s", analysis.to_dict())


def log_pattern_analysis_validation(logger: logging.Logger, validation: Any) -> None:
    """Record pattern analysis validation metadata."""
    logger.info("Pattern Analysis Validator iniciado")
    logger.info("Pattern Analysis valida: %s", validation.valid)
    logger.info("Pattern Analysis padroes validados: %s", validation.pattern_count)
    logger.info("Pattern Analysis classificacoes validadas: %s", validation.classification_count)
    logger.info("Pattern Analysis contextos validados: %s", validation.context_count)
    for issue in validation.issues:
        logger.warning("Pattern Analysis issue: %s", issue)
    logger.info("Pattern Analysis Validator finalizado: %s", validation.to_dict())


def log_pattern_analysis_benchmark(logger: logging.Logger, benchmark: Any) -> None:
    """Record pattern analysis benchmark metadata."""
    logger.info("Pattern Analysis Benchmark iniciado")
    logger.info("Pattern Analysis Benchmark status: %s", benchmark.status)
    logger.info(
        "Pattern Analysis Benchmark tempo de processamento: %s ms",
        benchmark.processing_time_ms,
    )
    logger.info(
        "Pattern Analysis Benchmark pico de memoria: %s KB",
        benchmark.peak_memory_kb,
    )
    logger.info(
        "Pattern Analysis Benchmark padroes analisados: %s",
        benchmark.analyzed_pattern_count,
    )
    logger.info(
        "Pattern Analysis Benchmark classificacoes: %s",
        benchmark.classification_count,
    )
    logger.info(
        "Pattern Analysis Benchmark contextos: %s",
        benchmark.context_count,
    )
    logger.info("Pattern Analysis Benchmark finalizado: %s", benchmark.to_dict())


def log_intelligence_context(logger: logging.Logger, context: Any) -> None:
    """Record structural intelligence context metadata."""
    logger.info("Intelligence Context iniciado")
    logger.info("Intelligence Context criado: %s", context.id)
    logger.info("Intelligence Context analises: %s", context.analysis_count)
    logger.info("Intelligence Context entidades: %s", context.entity_count)
    logger.info("Intelligence Context finalizado: %s", context.to_dict())


def log_intelligence_context_validation(
    logger: logging.Logger,
    validation: Any,
) -> None:
    """Record intelligence context validation metadata."""
    logger.info("Intelligence Context Validator iniciado")
    logger.info("Intelligence Context valida: %s", validation.valid)
    logger.info("Intelligence Context analises validadas: %s", validation.analysis_count)
    logger.info("Intelligence Context entidades validadas: %s", validation.entity_count)
    for issue in validation.issues:
        logger.warning("Intelligence Context issue: %s", issue)
    logger.info("Intelligence Context Validator finalizado: %s", validation.to_dict())


def log_market_hypothesis(logger: logging.Logger, hypotheses: Any) -> None:
    """Record market hypothesis metadata."""
    logger.info("Market Hypothesis Builder iniciado")
    logger.info("Market Hypotheses criadas: %s", hypotheses.count)
    logger.info("Market Hypothesis Builder finalizado: %s", hypotheses.to_dict())


def log_market_hypothesis_registry(logger: logging.Logger, registry: Any) -> None:
    """Record market hypothesis registry metadata."""
    logger.info("Market Hypothesis Registry iniciado")
    logger.info("Market Hypothesis Registry hypotheses: %s", registry.hypothesis_count)
    logger.info("Market Hypothesis Registry finalizado: %s", registry.to_dict())


def log_hypothesis_evaluator(logger: logging.Logger, scores: Any) -> None:
    """Record hypothesis evaluation metadata."""
    logger.info("Hypothesis Evaluator iniciado")
    logger.info("Hypothesis Scores criados: %s", len(scores))
    logger.info("Hypothesis Evaluator finalizado")


def log_intelligence_snapshot(logger: logging.Logger, snapshot: Any) -> None:
    """Record intelligence snapshot metadata."""
    logger.info("Intelligence Snapshot Builder iniciado")
    logger.info("Intelligence Snapshot criado: %s", snapshot.id)
    logger.info("Intelligence Snapshot hypotheses: %s", snapshot.hypothesis_count)
    logger.info("Intelligence Snapshot analises: %s", snapshot.analysis_count)
    logger.info("Intelligence Snapshot finalizado: %s", snapshot.to_dict())


def log_intelligence_benchmark(logger: logging.Logger, benchmark: Any) -> None:
    """Record intelligence benchmark metadata."""
    logger.info("Intelligence Benchmark iniciado")
    logger.info("Intelligence Benchmark status: %s", benchmark.status)
    logger.info(
        "Intelligence Benchmark tempo de processamento: %s ms",
        benchmark.processing_time_ms,
    )
    logger.info(
        "Intelligence Benchmark pico de memoria: %s KB",
        benchmark.peak_memory_kb,
    )
    logger.info("Intelligence Benchmark hypotheses: %s", benchmark.hypothesis_count)
    logger.info("Intelligence Benchmark analises: %s", benchmark.analysis_count)
    logger.info("Intelligence Benchmark entidades: %s", benchmark.entity_count)
    logger.info("Intelligence Benchmark finalizado: %s", benchmark.to_dict())


def log_signal(logger: logging.Logger, signals: Any) -> None:
    """Record structural signal metadata."""
    logger.info("Signal Builder iniciado")
    logger.info("Signals criados: %s", signals.count)
    logger.info("Signal Builder finalizado: %s", signals.to_dict())


def log_signal_registry(logger: logging.Logger, registry: Any) -> None:
    """Record signal registry metadata."""
    logger.info("Signal Registry iniciado")
    logger.info("Signal Registry sinais: %s", registry.count)
    logger.info("Signal Registry finalizado: %s", registry.to_dict())


def log_signal_validation(logger: logging.Logger, validation: Any) -> None:
    """Record signal validation metadata."""
    logger.info("Signal Validator iniciado")
    logger.info("Signal valida: %s", validation.valid)
    logger.info("Signal validadas: %s", validation.signal_count)
    for issue in validation.issues:
        logger.warning("Signal issue: %s", issue)
    logger.info("Signal Validator finalizado: %s", validation.to_dict())


def log_signal_score(logger: logging.Logger, score: Any) -> None:
    """Record signal scoring metadata."""
    logger.info("Signal Scorer iniciado")
    logger.info("Signal score criado: %s", score.to_dict())
    logger.info("Signal Scorer finalizado")


def log_strategy_readiness_snapshot(logger: logging.Logger, snapshot: Any) -> None:
    """Record strategy readiness snapshot metadata."""
    logger.info("Strategy Readiness Snapshot iniciado")
    logger.info("Strategy Readiness Snapshot criado: %s", snapshot.id)
    logger.info("Strategy Readiness Snapshot sinais: %s", snapshot.signal_count)
    logger.info("Strategy Readiness Snapshot hipoteses: %s", snapshot.hypothesis_count)
    logger.info("Strategy Readiness Snapshot finalizado: %s", snapshot.to_dict())


def log_strategy_readiness_benchmark(logger: logging.Logger, benchmark: Any) -> None:
    """Record strategy readiness benchmark metadata."""
    logger.info("Strategy Readiness Benchmark iniciado")
    logger.info("Strategy Readiness Benchmark status: %s", benchmark.status)
    logger.info(
        "Strategy Readiness Benchmark tempo de processamento: %s ms",
        benchmark.processing_time_ms,
    )
    logger.info(
        "Strategy Readiness Benchmark pico de memoria: %s KB",
        benchmark.peak_memory_kb,
    )
    logger.info("Strategy Readiness Benchmark sinais: %s", benchmark.signal_count)
    logger.info(
        "Strategy Readiness Benchmark hipoteses: %s",
        benchmark.hypothesis_count,
    )
    logger.info(
        "Strategy Readiness Benchmark analises: %s",
        benchmark.analysis_count,
    )
    logger.info(
        "Strategy Readiness Benchmark finalizado: %s",
        benchmark.to_dict(),
    )


def log_live_session(logger: logging.Logger, session: Any) -> None:
    """Record live session metadata."""
    logger.info("Live Session Foundation iniciado")
    logger.info("Live Session ID: %s", session.session_id)
    logger.info("Live Session timeframe: %s", session.timeframe)
    logger.info("Live Session captura: %s s", session.capture_interval_seconds)
    logger.info("Live Session capturas por vela: %s", session.captures_per_candle)
    logger.info("Live Session estado: %s", session.state.state)
    logger.info("Live Session finalizado: %s", session.to_dict())


def log_broker_window_state(logger: logging.Logger, state: Any) -> None:
    """Record broker/browser window metadata."""
    logger.info("Broker Window Detection iniciado")
    logger.info("Título da janela: %s", state.title)
    logger.info("Resolução da janela: %sx%s", state.resolution_width, state.resolution_height)
    logger.info("Posição da janela: x=%s y=%s", state.left, state.top)
    logger.info("Janela maximizada: %s", state.maximized)
    logger.info("Janela em primeiro plano: %s", state.foreground)
    logger.info("Broker Window Detection finalizado: %s", state.to_dict())


def log_live_capture_tick(logger: logging.Logger, tick: Any) -> None:
    """Record compact live capture tick metadata."""
    logger.info(
        "LIVE_CAPTURE_TICK index=%s captured_at=%s capture_path=%s window_title=%s",
        getattr(tick, "tick_index", "UNKNOWN"),
        getattr(tick, "captured_at", "UNKNOWN"),
        getattr(tick, "capture_path", "UNKNOWN"),
        getattr(tick, "window_title", "UNKNOWN"),
    )

def log_live_market_reading(logger: logging.Logger, reading: Any) -> None:
    """Record compact live market reading metadata."""
    metadata = getattr(reading, "metadata", {}) or {}
    unknown_fields = metadata.get("unknown_fields", [])

    logger.info(
        "LIVE_READING asset=%s price=%s payout=%s balance=%s trade_value=%s duration=%s timeframe=%s confidence=%s unknown_fields=%s",
        getattr(reading, "asset", "UNKNOWN"),
        getattr(reading, "price", "UNKNOWN"),
        getattr(reading, "payout", "UNKNOWN"),
        getattr(reading, "balance", "UNKNOWN"),
        getattr(reading, "trade_value", "UNKNOWN"),
        getattr(reading, "duration", "UNKNOWN"),
        getattr(reading, "timeframe", "UNKNOWN"),
        getattr(reading, "confidence", 0.0),
        unknown_fields,
    )

def log_field_location_map(logger: logging.Logger, location_map: Any) -> None:
    """Record live candle field location metadata."""
    logger.info("Field Locator iniciado")
    logger.info("Campos mapeados: %s", len(location_map.definitions))
    logger.info("Field Locator finalizado: %s", location_map.to_dict())


def log_field_extraction_result(logger: logging.Logger, extraction: Any) -> None:
    """Record live candle field extraction metadata."""
    logger.info("Field Extractor iniciado")
    logger.info("Campos encontrados: %s", len(extraction.fields))
    logger.info("Campos UNKNOWN: %s", len(extraction.unknown_fields))
    logger.info("Field Extractor finalizado: %s", extraction.to_dict())


def log_candle_snapshot(logger: logging.Logger, snapshot: Any) -> None:
    """Record candle snapshot metadata."""
    logger.info("Candle Snapshot iniciado")
    logger.info("Leituras da vela: %s", snapshot.capture_count)
    logger.info("Campos da vela: %s", len(snapshot.field_names))
    logger.info("Candle Snapshot finalizado: %s", snapshot.to_dict())


def log_candle_statistics(logger: logging.Logger, statistics: Any) -> None:
    """Record candle statistics metadata."""
    logger.info("Candle Statistics iniciado")
    logger.info("Média da vela: %s", statistics.average)
    logger.info("Máxima da vela: %s", statistics.maximum)
    logger.info("Mínima da vela: %s", statistics.minimum)
    logger.info("Volatilidade da vela: %s", statistics.volatility)
    logger.info("Candle Statistics finalizado: %s", statistics.to_dict())


def log_live_candle_benchmark(logger: logging.Logger, benchmark: Any) -> None:
    """Record live candle benchmark metadata."""
    logger.info("Live Candle Benchmark iniciado")
    logger.info("Live Candle Benchmark capturas: %s", benchmark.capture_count)
    logger.info("Live Candle Benchmark campos: %s", benchmark.field_count)
    logger.info("Live Candle Benchmark média: %s", benchmark.average)
    logger.info("Live Candle Benchmark máxima: %s", benchmark.maximum)
    logger.info("Live Candle Benchmark mínima: %s", benchmark.minimum)
    logger.info("Live Candle Benchmark volatilidade: %s", benchmark.volatility)
    logger.info("Live Candle Benchmark finalizado: %s", benchmark.to_dict())


def log_live_validation_report(logger: logging.Logger, report: Any) -> None:
    """Record live validation report metadata."""
    logger.info("Live Validation Report iniciado")
    logger.info("Total de capturas: %s", report.total_captures)
    logger.info("Campos detectados: %s", ", ".join(report.fields_detected))
    logger.info("Campos UNKNOWN: %s", ", ".join(report.unknown_fields))
    logger.info("Confiança OCR: %s", report.ocr_confidence)
    logger.info("Tempo total: %s ms", report.total_time_ms)
    logger.info("Status: %s", report.status)
    logger.info("Live Validation Report finalizado: %s", report.to_dict())


def log_live_validation_benchmark(logger: logging.Logger, benchmark: Any) -> None:
    """Record live validation benchmark metadata."""
    logger.info("Live Validation Benchmark iniciado")
    logger.info("Live Validation Benchmark status: %s", benchmark.status)
    logger.info(
        "Live Validation Benchmark tempo de processamento: %s ms",
        benchmark.processing_time_ms,
    )
    logger.info(
        "Live Validation Benchmark pico de memoria: %s KB",
        benchmark.peak_memory_kb,
    )
    logger.info("Live Validation Benchmark capturas: %s", benchmark.total_captures)
    logger.info("Live Validation Benchmark campos detectados: %s", benchmark.detected_fields)
    logger.info("Live Validation Benchmark campos UNKNOWN: %s", benchmark.unknown_fields)
    logger.info("Live Validation Benchmark finalizado: %s", benchmark.to_dict())


def log_error(logger: logging.Logger, message: str, error: Exception) -> None:
    """Record initialization errors without exposing secrets."""
    logger.exception("%s: %s", message, error)


def _reset_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
