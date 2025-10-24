"""
Logging utility module
"""

import logging
import sys
from pathlib import Path
from typing import Optional
import colorlog


def setup_logger(
    name: str,
    level: str = 'INFO',
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
    use_color: bool = True
) -> logging.Logger:
    """
    Set up a logger with console and optional file output.
    
    Args:
        name: Logger name
        level: Logging level
        log_file: Optional log file path
        format_string: Custom format string
        use_color: Whether to use colored output
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Default format
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Console handler with color
    if use_color and sys.stdout.isatty():
        console_formatter = colorlog.ColoredFormatter(
            '%(log_color)s' + format_string,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            }
        )
    else:
        console_formatter = logging.Formatter(format_string)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_formatter = logging.Formatter(format_string)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


class LoggerMixin:
    """
    Mixin class to add logging capability to any class.
    
    Usage:
        class MyClass(LoggerMixin):
            def __init__(self):
                self.setup_logger()
    """
    
    def setup_logger(self, name: Optional[str] = None, **kwargs):
        """
        Set up logger for the class.
        
        Args:
            name: Logger name (defaults to class name)
            **kwargs: Additional arguments for setup_logger
        """
        if name is None:
            name = self.__class__.__name__
        
        self.logger = setup_logger(name, **kwargs)
    
    def log_debug(self, message: str, *args, **kwargs):
        """Log debug message."""
        if hasattr(self, 'logger'):
            self.logger.debug(message, *args, **kwargs)
    
    def log_info(self, message: str, *args, **kwargs):
        """Log info message."""
        if hasattr(self, 'logger'):
            self.logger.info(message, *args, **kwargs)
    
    def log_warning(self, message: str, *args, **kwargs):
        """Log warning message."""
        if hasattr(self, 'logger'):
            self.logger.warning(message, *args, **kwargs)
    
    def log_error(self, message: str, *args, **kwargs):
        """Log error message."""
        if hasattr(self, 'logger'):
            self.logger.error(message, *args, **kwargs)
    
    def log_critical(self, message: str, *args, **kwargs):
        """Log critical message."""
        if hasattr(self, 'logger'):
            self.logger.critical(message, *args, **kwargs)


def log_function_call(func):
    """
    Decorator to log function calls.
    
    Usage:
        @log_function_call
        def my_function(arg1, arg2):
            return result
    """
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} returned {result}")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} raised {e.__class__.__name__}: {str(e)}")
            raise
    
    return wrapper


def log_execution_time(func):
    """
    Decorator to log execution time of functions.
    
    Usage:
        @log_execution_time
        def slow_function():
            time.sleep(1)
    """
    import functools
    import time
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            logger.info(f"{func.__name__} completed in {elapsed_time:.3f} seconds")
            return result
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {elapsed_time:.3f} seconds: {str(e)}")
            raise
    
    return wrapper


class ProgressLogger:
    """
    Helper class for logging progress of long-running operations.
    
    Usage:
        progress = ProgressLogger(total=100, logger=my_logger)
        for i in range(100):
            # Do work
            progress.update(1, f"Processing item {i}")
    """
    
    def __init__(
        self,
        total: int,
        logger: Optional[logging.Logger] = None,
        log_interval: int = 10
    ):
        """
        Initialize progress logger.
        
        Args:
            total: Total number of items
            logger: Logger instance
            log_interval: Percentage interval for logging
        """
        self.total = total
        self.current = 0
        self.logger = logger or logging.getLogger(__name__)
        self.log_interval = log_interval
        self.last_logged_percent = -log_interval
    
    def update(self, amount: int = 1, message: Optional[str] = None):
        """
        Update progress.
        
        Args:
            amount: Amount to increment
            message: Optional message to log
        """
        self.current += amount
        percent = (self.current / self.total) * 100 if self.total > 0 else 0
        
        if percent >= self.last_logged_percent + self.log_interval or self.current >= self.total:
            if message:
                self.logger.info(f"Progress: {percent:.1f}% - {message}")
            else:
                self.logger.info(f"Progress: {percent:.1f}% ({self.current}/{self.total})")
            
            self.last_logged_percent = (percent // self.log_interval) * self.log_interval
    
    def reset(self):
        """Reset progress counter."""
        self.current = 0
        self.last_logged_percent = -self.log_interval
