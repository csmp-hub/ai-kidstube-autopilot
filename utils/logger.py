# utils klasöründe yeni dosya: logger.py
# İçeriği yapıştır:

# utils/logger.py
# ====================
"""
Structured logging for AI-KidsTube Autopilot
"""
import structlog
import sys
from pathlib import Path

def setup_logger(log_level: str = "INFO", log_file: Path = None):
    """
    Configure structlog with console and optional file output
    """
    processors = [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.set_exc_info,
    ]
    
    # Add file handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        processors.append(
            structlog.processors.JSONRenderer()
        )
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(structlog, log_level.upper(), structlog.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(
            file=sys.stdout if not log_file else open(log_file, "a", encoding="utf-8")
        ),
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger()

# Create default logger instance
logger = setup_logger()
# ====================
# Dosyayı kaydet ✅