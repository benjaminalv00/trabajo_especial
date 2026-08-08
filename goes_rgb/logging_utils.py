import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


_LOGGING_CONFIGURED = False


def setup_logging(level=None, log_file=None):
    global _LOGGING_CONFIGURED

    if _LOGGING_CONFIGURED:
        return logging.getLogger("goes_rgb")

    log_level_name = (level or os.getenv("GOES_RGB_LOG_LEVEL", "INFO")).upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    log_path = Path(log_file or os.getenv("GOES_RGB_LOG_FILE", "logs/goes_rgb.log"))
    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)

    _LOGGING_CONFIGURED = True
    root_logger.debug("Logging configurado en %s", log_path)
    return logging.getLogger("goes_rgb")


def get_logger(name=None):
    setup_logging()
    return logging.getLogger(name or "goes_rgb")