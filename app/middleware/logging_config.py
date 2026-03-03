"""
Structured logging configuration for production
"""
import logging
import sys
import json
from datetime import datetime
from pythonjsonlogger import jsonlogger
from functools import wraps

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields"""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        
        # Add request ID if available
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
        
        # Add user ID if available
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id

def setup_logging(log_level: str = "INFO", log_file: str = None):
    """Configure structured logging"""
    # Create logger
    logger = logging.getLogger("datachat")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logger.handlers = []
    
    # JSON formatter
    formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(message)s',
        json_ensure_ascii=False
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# Global logger instance
logger = setup_logging()

def log_request(func):
    """Decorator to log API requests"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get('request')
        if request:
            logger.info(
                f"API Request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": str(request.query_params),
                    "request_id": getattr(request.state, 'request_id', None)
                }
            )
        return await func(*args, **kwargs)
    return wrapper

def log_error(error: Exception, context: dict = None):
    """Log errors with context"""
    logger.error(
        f"Error: {str(error)}",
        extra={
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {}
        },
        exc_info=True
    )

def log_user_action(user_id: str, action: str, details: dict = None):
    """Log user actions for analytics"""
    logger.info(
        f"User Action: {action}",
        extra={
            "user_id": user_id,
            "action": action,
            "details": details or {}
        }
    )

# Usage examples:
# logger.info("User logged in", extra={"user_id": "123", "action": "login"})
# logger.error("Database connection failed", extra={"error": "connection_timeout"})
# log_user_action("user_123", "chat_message", {"tokens": 150, "cost": 0.00015})