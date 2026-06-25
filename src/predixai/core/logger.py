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

    stream_handler = logging.StreamHandler()
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


def log_error(logger: logging.Logger, message: str, error: Exception) -> None:
    """Record initialization errors without exposing secrets."""
    logger.exception("%s: %s", message, error)


def _reset_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
