"""Structured logging with JSON format."""
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_dict: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }
        
        # Attach extra fields if present
        for field in ["trace_id", "user_id", "latency_ms", "query_fingerprint"]:
            if hasattr(record, field):
                log_dict[field] = getattr(record, field)
        
        # Add exception info if present
        if record.exc_info:
            log_dict["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_dict)


def get_logger(name: str) -> logging.Logger:
    """Get a structured logger instance."""
    logger = logging.getLogger(name)
    
    # Only add handler if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger
