"""
Structured Logging Configuration

Setup for structured logging with request IDs and JSON formatting.
"""

import json
import logging
import sys
import uuid
from datetime import datetime
from typing import Any, Dict

from pythonjsonlogger import jsonlogger

from .config import get_settings


class RequestIDFilter(logging.Filter):
    """Add request ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, 'request_id'):
            record.request_id = str(uuid.uuid4())[:8]
        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        # Add service info
        log_record['service'] = 'iot-identity-gateway'
        log_record['version'] = get_settings().app_version
        
        # Ensure level is present
        if 'level' not in log_record:
            log_record['level'] = record.levelname


def setup_logging() -> None:
    """Configure application logging."""
    settings = get_settings()
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Add request ID filter
    request_id_filter = RequestIDFilter()
    console_handler.addFilter(request_id_filter)
    
    # Configure formatter
    if settings.log_format.lower() == 'json':
        formatter = CustomJsonFormatter(
            fmt='%(timestamp)s %(level)s %(name)s %(request_id)s %(message)s'
        )
    else:
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(request_id)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('web3').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - level: {settings.log_level}, format: {settings.log_format}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)
