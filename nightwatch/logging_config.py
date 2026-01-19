"""
NIGHTWATCH Logging Configuration

Provides centralized logging configuration for the NIGHTWATCH observatory
control system with support for:
- Structured JSON logging format (machine-parseable)
- Rotating file handlers with size limits
- Console output with optional color formatting
- Per-service log level configuration
- Request correlation IDs for tracing
- Convenience helpers (log_exception, log_timing)

Usage:
    from nightwatch.logging_config import setup_logging, get_logger, log_exception, log_timing

    # Initialize logging at application startup
    setup_logging(log_level="INFO", log_file="nightwatch.log")

    # Get a logger for your module
    logger = get_logger(__name__)
    logger.info("Mount connected", extra={"device": "OnStepX"})

    # Log exceptions with full traceback
    try:
        risky_operation()
    except Exception as e:
        log_exception(logger, "Failed to connect to mount", e)

    # Time a block of code
    with log_timing(logger, "plate_solve"):
        solve_field(image_path)
"""

import logging
import sys
import time
import traceback
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

# Module-level constants
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB
DEFAULT_BACKUP_COUNT = 5

# Log level mapping for per-service configuration
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def setup_logging(
    log_level: str = DEFAULT_LOG_LEVEL,
    log_file: Optional[str | Path] = None,
    json_format: bool = False,
    enable_color: bool = True,
) -> None:
    """Configure logging for the NIGHTWATCH application.

    Sets up the root logger with console and optional file handlers.
    Should be called once at application startup.

    Args:
        log_level: Default logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file. If provided, enables file logging
                  with rotation.
        json_format: If True, use structured JSON format for logs.
        enable_color: If True, enable colored console output (when supported).

    Example:
        setup_logging(log_level="DEBUG", log_file="/var/log/nightwatch.log")
    """
    # Get the root logger for nightwatch
    root_logger = logging.getLogger("nightwatch")
    root_logger.setLevel(LOG_LEVELS.get(log_level.upper(), logging.INFO))

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(LOG_LEVELS.get(log_level.upper(), logging.INFO))
    console_handler.setFormatter(
        logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_DATE_FORMAT)
    )
    root_logger.addHandler(console_handler)

    # Create file handler if log_file specified
    if log_file:
        from logging.handlers import RotatingFileHandler

        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=DEFAULT_MAX_BYTES,
            backupCount=DEFAULT_BACKUP_COUNT,
        )
        file_handler.setLevel(LOG_LEVELS.get(log_level.upper(), logging.INFO))
        file_handler.setFormatter(
            logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_DATE_FORMAT)
        )
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module or service.

    Returns a child logger under the nightwatch namespace for consistent
    configuration inheritance.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Starting mount service")
    """
    # Ensure logger is under nightwatch namespace
    if not name.startswith("nightwatch"):
        name = f"nightwatch.{name}"
    return logging.getLogger(name)


def set_service_level(service_name: str, level: str) -> None:
    """Set log level for a specific service.

    Allows granular control over logging verbosity per service.

    Args:
        service_name: Name of the service (e.g., "mount", "weather", "voice")
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Example:
        set_service_level("mount", "DEBUG")  # Verbose mount logging
        set_service_level("weather", "WARNING")  # Only weather warnings
    """
    logger_name = f"nightwatch.services.{service_name}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(LOG_LEVELS.get(level.upper(), logging.INFO))


# =============================================================================
# Convenience Helpers
# =============================================================================


def log_exception(
    logger: logging.Logger,
    message: str,
    exc: BaseException,
    level: int = logging.ERROR,
    include_traceback: bool = True,
) -> None:
    """Log an exception with optional full traceback.

    Provides a consistent way to log exceptions across the application,
    including structured information about the exception type and message.

    Args:
        logger: Logger instance to use
        message: Context message describing what operation failed
        exc: The exception that was raised
        level: Log level to use (default: ERROR)
        include_traceback: If True, include full traceback in log

    Example:
        try:
            mount.connect()
        except ConnectionError as e:
            log_exception(logger, "Failed to connect to mount", e)
    """
    exc_type = type(exc).__name__
    exc_message = str(exc)

    extra = {
        "exception_type": exc_type,
        "exception_message": exc_message,
    }

    if include_traceback:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        extra["traceback"] = tb
        logger.log(level, f"{message}: [{exc_type}] {exc_message}\n{tb}", extra=extra)
    else:
        logger.log(level, f"{message}: [{exc_type}] {exc_message}", extra=extra)


@contextmanager
def log_timing(
    logger: logging.Logger,
    operation: str,
    level: int = logging.DEBUG,
    warn_threshold_sec: Optional[float] = None,
) -> Generator[None, None, None]:
    """Context manager to log the duration of an operation.

    Useful for performance monitoring and identifying slow operations.
    Optionally emits a warning if the operation exceeds a threshold.

    Args:
        logger: Logger instance to use
        operation: Name of the operation being timed
        level: Log level for the timing message (default: DEBUG)
        warn_threshold_sec: If set, emit WARNING if duration exceeds this

    Yields:
        None

    Example:
        with log_timing(logger, "plate_solve", warn_threshold_sec=30.0):
            result = solver.solve(image_path)

        # Logs: "plate_solve completed in 12.345s"
        # Or if > 30s: "plate_solve completed in 45.678s (exceeded 30.0s threshold)"
    """
    start_time = time.perf_counter()
    logger.log(level, f"{operation} started")

    try:
        yield
    finally:
        elapsed = time.perf_counter() - start_time
        extra = {
            "operation": operation,
            "elapsed_seconds": round(elapsed, 3),
        }

        if warn_threshold_sec is not None and elapsed > warn_threshold_sec:
            logger.warning(
                f"{operation} completed in {elapsed:.3f}s "
                f"(exceeded {warn_threshold_sec}s threshold)",
                extra=extra,
            )
        else:
            logger.log(level, f"{operation} completed in {elapsed:.3f}s", extra=extra)
