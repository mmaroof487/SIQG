"""Structured logging with JSON format."""
import logging
import sys
from pythonjsonlogger import jsonlogger
from opentelemetry import trace


class OTelJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        
        # Add OpenTelemetry context
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            log_record['trace_id'] = format(current_span.get_span_context().trace_id, '032x')
            log_record['span_id'] = format(current_span.get_span_context().span_id, '016x')
            
        # Add timestamp and level
        log_record['level'] = record.levelname
        log_record['module'] = record.module
        
        # Attach any extra fields passed in the log record
        for field in ["user_id", "latency_ms", "query_fingerprint", "connection_id", "event"]:
            if hasattr(record, field):
                log_record[field] = getattr(record, field)


def get_logger(name: str) -> logging.Logger:
    """Get a structured logger instance."""
    logger = logging.getLogger(name)
    
    # Only add handler if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        # Configure format string for pythonjsonlogger
        formatter = OTelJsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s', rename_fields={"asctime": "timestamp"})
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger

