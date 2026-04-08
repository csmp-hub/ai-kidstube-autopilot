# utils/logger.py
# ====================
"""
Simple logging for AI-KidsTube Autopilot (GitHub Actions compatible)
"""
import logging
import sys
from pathlib import Path

def setup_logger(log_level: str = "INFO", log_file: Path = None):
    """
    Configure standard logging (simple, reliable, GitHub Actions compatible)
    """
    # Use standard Python logging (not structlog - avoids compatibility issues)
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger("ai-kidstube")
    logger.setLevel(level)
    
    # Clear existing handlers (prevent duplicates in re-runs)
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # Optional file handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
        file_handler.setLevel(level)
        file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger

# Create default logger instance
logger = setup_logger()
# ====================
