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


def log_error(logger: logging.Logger, message: str, error: Exception) -> None:
    """Record initialization errors without exposing secrets."""
    logger.exception("%s: %s", message, error)


def _reset_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
