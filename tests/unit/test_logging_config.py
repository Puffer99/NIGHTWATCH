"""
NIGHTWATCH Unit Tests - Logging Configuration

Unit tests for nightwatch/logging_config.py.
Tests setup_logging, get_logger, set_service_level, correlation ID, and helper functions.

Run:
    pytest tests/unit/test_logging_config.py -v
"""

import logging
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch
import threading

import pytest


# =============================================================================
# Test setup_logging Function
# =============================================================================

class TestSetupLogging:
    """Unit tests for setup_logging function."""

    def test_setup_logging_default(self):
        """Test setup_logging with default parameters."""
        from nightwatch.logging_config import setup_logging, get_logger

        setup_logging()

        logger = get_logger("test_default")
        assert logger is not None
        assert logger.name == "nightwatch.test_default"

    def test_setup_logging_custom_level(self):
        """Test setup_logging with custom log level."""
        from nightwatch.logging_config import setup_logging

        setup_logging(log_level="DEBUG")

        root_logger = logging.getLogger("nightwatch")
        assert root_logger.level == logging.DEBUG

    def test_setup_logging_warning_level(self):
        """Test setup_logging with WARNING level."""
        from nightwatch.logging_config import setup_logging

        setup_logging(log_level="WARNING")

        root_logger = logging.getLogger("nightwatch")
        assert root_logger.level == logging.WARNING

    def test_setup_logging_with_file(self):
        """Test setup_logging creates file handler when log_file specified."""
        from nightwatch.logging_config import setup_logging

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test.log"
            setup_logging(log_file=log_path)

            # Get the nightwatch logger and verify handlers
            root_logger = logging.getLogger("nightwatch")

            # Should have at least 2 handlers (console + file)
            assert len(root_logger.handlers) >= 2

            # Find the file handler
            file_handlers = [
                h for h in root_logger.handlers
                if hasattr(h, 'baseFilename')
            ]
            assert len(file_handlers) == 1
            assert Path(file_handlers[0].baseFilename) == log_path

            # Close file handler before temp dir cleanup (Windows fix)
            for h in file_handlers:
                h.close()
                root_logger.removeHandler(h)

    def test_setup_logging_creates_parent_directory(self):
        """Test that setup_logging creates parent directories for log file."""
        from nightwatch.logging_config import setup_logging

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "subdir" / "nested" / "test.log"
            setup_logging(log_file=log_path)

            assert log_path.parent.exists()

            # Close file handler before temp dir cleanup (Windows fix)
            root_logger = logging.getLogger("nightwatch")
            for h in list(root_logger.handlers):
                if hasattr(h, 'baseFilename'):
                    h.close()
                    root_logger.removeHandler(h)

    def test_setup_logging_clears_existing_handlers(self):
        """Test that setup_logging clears existing handlers on re-initialization."""
        from nightwatch.logging_config import setup_logging

        # Setup twice
        setup_logging(log_level="INFO")
        setup_logging(log_level="DEBUG")

        root_logger = logging.getLogger("nightwatch")
        # Should not accumulate handlers
        assert len(root_logger.handlers) == 1  # Only console handler


# =============================================================================
# Test get_logger Function
# =============================================================================

class TestGetLogger:
    """Unit tests for get_logger function."""

    def test_get_logger_returns_logger(self):
        """Test get_logger returns a Logger instance."""
        from nightwatch.logging_config import get_logger

        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_adds_nightwatch_prefix(self):
        """Test get_logger adds nightwatch prefix to logger name."""
        from nightwatch.logging_config import get_logger

        logger = get_logger("services.mount")
        assert logger.name == "nightwatch.services.mount"

    def test_get_logger_preserves_existing_prefix(self):
        """Test get_logger preserves existing nightwatch prefix."""
        from nightwatch.logging_config import get_logger

        logger = get_logger("nightwatch.services.mount")
        assert logger.name == "nightwatch.services.mount"

    def test_get_logger_dunder_name(self):
        """Test get_logger with typical __name__ style input."""
        from nightwatch.logging_config import get_logger

        logger = get_logger("services.weather.ecowitt")
        assert logger.name == "nightwatch.services.weather.ecowitt"


# =============================================================================
# Test set_service_level Function
# =============================================================================

class TestSetServiceLevel:
    """Unit tests for set_service_level function."""

    def test_set_service_level_debug(self):
        """Test setting service level to DEBUG."""
        from nightwatch.logging_config import setup_logging, set_service_level

        setup_logging()
        set_service_level("mount", "DEBUG")

        service_logger = logging.getLogger("nightwatch.services.mount")
        assert service_logger.level == logging.DEBUG

    def test_set_service_level_warning(self):
        """Test setting service level to WARNING."""
        from nightwatch.logging_config import setup_logging, set_service_level

        setup_logging()
        set_service_level("weather", "WARNING")

        service_logger = logging.getLogger("nightwatch.services.weather")
        assert service_logger.level == logging.WARNING

    def test_set_service_level_case_insensitive(self):
        """Test that level names are case-insensitive."""
        from nightwatch.logging_config import setup_logging, set_service_level

        setup_logging()
        set_service_level("camera", "debug")

        service_logger = logging.getLogger("nightwatch.services.camera")
        assert service_logger.level == logging.DEBUG

    def test_set_service_level_invalid_defaults_to_info(self):
        """Test that invalid level defaults to INFO."""
        from nightwatch.logging_config import setup_logging, set_service_level

        setup_logging()
        set_service_level("guiding", "INVALID_LEVEL")

        service_logger = logging.getLogger("nightwatch.services.guiding")
        assert service_logger.level == logging.INFO


# =============================================================================
# Test log_exception Helper
# =============================================================================

class TestLogException:
    """Unit tests for log_exception helper function."""

    def test_log_exception_logs_at_error_level(self):
        """Test log_exception logs at ERROR level by default."""
        from nightwatch.logging_config import setup_logging, get_logger, log_exception

        setup_logging(log_level="DEBUG")
        logger = get_logger("test_exception")

        with patch.object(logger, 'log') as mock_log:
            exc = ValueError("test error message")
            log_exception(logger, "Operation failed", exc)

            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][0] == logging.ERROR  # First arg is level

    def test_log_exception_includes_exception_type(self):
        """Test log_exception includes exception type in message."""
        from nightwatch.logging_config import setup_logging, get_logger, log_exception

        setup_logging(log_level="DEBUG")
        logger = get_logger("test_exception_type")

        with patch.object(logger, 'log') as mock_log:
            exc = RuntimeError("runtime error")
            log_exception(logger, "Something broke", exc)

            call_args = mock_log.call_args
            message = call_args[0][1]
            assert "RuntimeError" in message
            assert "runtime error" in message

    def test_log_exception_custom_level(self):
        """Test log_exception with custom log level."""
        from nightwatch.logging_config import setup_logging, get_logger, log_exception

        setup_logging(log_level="DEBUG")
        logger = get_logger("test_custom_level")

        with patch.object(logger, 'log') as mock_log:
            exc = ValueError("test")
            log_exception(logger, "Test", exc, level=logging.WARNING)

            call_args = mock_log.call_args
            assert call_args[0][0] == logging.WARNING

    def test_log_exception_without_traceback(self):
        """Test log_exception without traceback when include_traceback=False."""
        from nightwatch.logging_config import setup_logging, get_logger, log_exception

        setup_logging(log_level="DEBUG")
        logger = get_logger("test_no_traceback")

        with patch.object(logger, 'log') as mock_log:
            exc = ValueError("no trace")
            log_exception(logger, "Error", exc, include_traceback=False)

            call_args = mock_log.call_args
            extra = call_args[1].get('extra', {})
            # traceback key should not be in extra
            assert 'traceback' not in extra

    def test_log_exception_with_traceback(self):
        """Test log_exception includes traceback by default."""
        from nightwatch.logging_config import setup_logging, get_logger, log_exception

        setup_logging(log_level="DEBUG")
        logger = get_logger("test_with_traceback")

        with patch.object(logger, 'log') as mock_log:
            try:
                raise ValueError("with trace")
            except ValueError as exc:
                log_exception(logger, "Error", exc, include_traceback=True)

            call_args = mock_log.call_args
            extra = call_args[1].get('extra', {})
            assert 'traceback' in extra
            assert 'ValueError' in extra['traceback']


# =============================================================================
# Test log_timing Context Manager
# =============================================================================

class TestLogTiming:
    """Unit tests for log_timing context manager."""

    def test_log_timing_logs_start_and_end(self):
        """Test log_timing logs operation start and completion."""
        from nightwatch.logging_config import setup_logging, get_logger, log_timing

        setup_logging(log_level="DEBUG")
        logger = get_logger("test_timing")

        with patch.object(logger, 'log') as mock_log:
            with log_timing(logger, "test_operation"):
                pass

            # Should be called at least twice (start + end)
            assert mock_log.call_count >= 2

    def test_log_timing_measures_duration(self):
        """Test log_timing accurately measures operation duration."""
        from nightwatch.logging_config import setup_logging, get_logger, log_timing

        setup_logging(log_level="DEBUG")
        logger = get_logger("test_duration")

        with patch.object(logger, 'log') as mock_log:
            with log_timing(logger, "sleep_operation"):
                time.sleep(0.1)  # Sleep for 100ms

            # Check the completion message includes timing
            calls = mock_log.call_args_list
            completion_call = calls[-1]
            message = completion_call[0][1]
            # Should contain "completed in X.XXXs" format
            assert "completed in" in message

    def test_log_timing_warns_on_threshold_exceeded(self):
        """Test log_timing emits warning when threshold exceeded."""
        from nightwatch.logging_config import setup_logging, get_logger, log_timing

        setup_logging(log_level="DEBUG")
        logger = get_logger("test_threshold")

        with patch.object(logger, 'warning') as mock_warning:
            with log_timing(logger, "slow_operation", warn_threshold_sec=0.01):
                time.sleep(0.05)  # Sleep longer than threshold

            mock_warning.assert_called_once()
            call_args = mock_warning.call_args
            message = call_args[0][0]
            assert "exceeded" in message
            assert "threshold" in message

    def test_log_timing_no_warning_under_threshold(self):
        """Test log_timing does not warn when under threshold."""
        from nightwatch.logging_config import setup_logging, get_logger, log_timing

        setup_logging(log_level="DEBUG")
        logger = get_logger("test_under_threshold")

        with patch.object(logger, 'warning') as mock_warning:
            with log_timing(logger, "fast_operation", warn_threshold_sec=10.0):
                pass  # Instant operation

            mock_warning.assert_not_called()

    def test_log_timing_includes_extra_data(self):
        """Test log_timing includes operation name in extra data."""
        from nightwatch.logging_config import setup_logging, get_logger, log_timing

        setup_logging(log_level="DEBUG")
        logger = get_logger("test_extra")

        with patch.object(logger, 'log') as mock_log:
            with log_timing(logger, "my_operation"):
                pass

            # Check completion log has extra data
            calls = mock_log.call_args_list
            completion_call = calls[-1]
            extra = completion_call[1].get('extra', {})
            assert 'operation' in extra
            assert extra['operation'] == "my_operation"
            assert 'elapsed_seconds' in extra

    def test_log_timing_works_with_exception(self):
        """Test log_timing still logs completion even if exception raised."""
        from nightwatch.logging_config import setup_logging, get_logger, log_timing

        setup_logging(log_level="DEBUG")
        logger = get_logger("test_exception_timing")

        with patch.object(logger, 'log') as mock_log:
            with pytest.raises(RuntimeError):
                with log_timing(logger, "failing_operation"):
                    raise RuntimeError("Intentional error")

            # Should still have logged start and completion
            assert mock_log.call_count >= 2


# =============================================================================
# Test Log Level Constants
# =============================================================================

class TestLogLevels:
    """Unit tests for log level constants."""

    def test_log_levels_mapping_contains_standard_levels(self):
        """Test LOG_LEVELS contains all standard Python log levels."""
        from nightwatch.logging_config import LOG_LEVELS

        assert "DEBUG" in LOG_LEVELS
        assert "INFO" in LOG_LEVELS
        assert "WARNING" in LOG_LEVELS
        assert "ERROR" in LOG_LEVELS
        assert "CRITICAL" in LOG_LEVELS

    def test_log_levels_map_to_correct_values(self):
        """Test LOG_LEVELS maps to correct logging module values."""
        from nightwatch.logging_config import LOG_LEVELS

        assert LOG_LEVELS["DEBUG"] == logging.DEBUG
        assert LOG_LEVELS["INFO"] == logging.INFO
        assert LOG_LEVELS["WARNING"] == logging.WARNING
        assert LOG_LEVELS["ERROR"] == logging.ERROR
        assert LOG_LEVELS["CRITICAL"] == logging.CRITICAL


# =============================================================================
# Test Default Constants
# =============================================================================

class TestDefaultConstants:
    """Unit tests for default logging constants."""

    def test_default_max_bytes(self):
        """Test DEFAULT_MAX_BYTES is 10MB."""
        from nightwatch.logging_config import DEFAULT_MAX_BYTES

        assert DEFAULT_MAX_BYTES == 10 * 1024 * 1024  # 10 MB

    def test_default_backup_count(self):
        """Test DEFAULT_BACKUP_COUNT is 5."""
        from nightwatch.logging_config import DEFAULT_BACKUP_COUNT

        assert DEFAULT_BACKUP_COUNT == 5

    def test_default_log_level(self):
        """Test DEFAULT_LOG_LEVEL is INFO."""
        from nightwatch.logging_config import DEFAULT_LOG_LEVEL

        assert DEFAULT_LOG_LEVEL == "INFO"


# =============================================================================
# Test Correlation ID Functions (Step 27)
# =============================================================================

class TestCorrelationId:
    """Unit tests for correlation ID functionality."""

    def test_get_correlation_id_returns_none_by_default(self):
        """Test get_correlation_id returns None when not set."""
        from nightwatch.logging_config import get_correlation_id, set_correlation_id

        # Ensure clean state
        set_correlation_id(None)
        assert get_correlation_id() is None

    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation ID."""
        from nightwatch.logging_config import get_correlation_id, set_correlation_id

        set_correlation_id("test-123")
        assert get_correlation_id() == "test-123"

        # Clean up
        set_correlation_id(None)

    def test_generate_correlation_id_format(self):
        """Test generated correlation IDs have correct format."""
        from nightwatch.logging_config import generate_correlation_id

        cid = generate_correlation_id()
        assert cid.startswith("nw-")
        assert len(cid) == 11  # "nw-" + 8 hex chars

    def test_generate_correlation_id_custom_prefix(self):
        """Test generate_correlation_id with custom prefix."""
        from nightwatch.logging_config import generate_correlation_id

        cid = generate_correlation_id(prefix="voice")
        assert cid.startswith("voice-")
        assert len(cid) == 14  # "voice-" + 8 hex chars

    def test_generate_correlation_id_uniqueness(self):
        """Test generated correlation IDs are unique."""
        from nightwatch.logging_config import generate_correlation_id

        ids = {generate_correlation_id() for _ in range(100)}
        assert len(ids) == 100  # All unique


class TestCorrelationContext:
    """Unit tests for correlation_context context manager."""

    def test_correlation_context_sets_id(self):
        """Test correlation_context sets the correlation ID."""
        from nightwatch.logging_config import correlation_context, get_correlation_id

        with correlation_context("ctx-test-123"):
            assert get_correlation_id() == "ctx-test-123"

    def test_correlation_context_clears_on_exit(self):
        """Test correlation_context clears ID on exit."""
        from nightwatch.logging_config import correlation_context, get_correlation_id, set_correlation_id

        set_correlation_id(None)  # Clean state
        with correlation_context("ctx-test"):
            pass
        assert get_correlation_id() is None

    def test_correlation_context_auto_generates_id(self):
        """Test correlation_context generates ID when none provided."""
        from nightwatch.logging_config import correlation_context

        with correlation_context() as cid:
            assert cid is not None
            assert cid.startswith("nw-")

    def test_correlation_context_custom_prefix(self):
        """Test correlation_context with custom prefix for auto-generated ID."""
        from nightwatch.logging_config import correlation_context

        with correlation_context(prefix="mount") as cid:
            assert cid.startswith("mount-")

    def test_correlation_context_yields_provided_id(self):
        """Test correlation_context yields the provided ID."""
        from nightwatch.logging_config import correlation_context

        with correlation_context("my-id-123") as cid:
            assert cid == "my-id-123"

    def test_correlation_context_nested(self):
        """Test nested correlation contexts."""
        from nightwatch.logging_config import correlation_context, get_correlation_id

        with correlation_context("outer"):
            assert get_correlation_id() == "outer"
            with correlation_context("inner"):
                assert get_correlation_id() == "inner"
            assert get_correlation_id() == "outer"

    def test_correlation_context_exception_safe(self):
        """Test correlation_context cleans up even on exception."""
        from nightwatch.logging_config import correlation_context, get_correlation_id, set_correlation_id

        set_correlation_id(None)
        with pytest.raises(RuntimeError):
            with correlation_context("error-test"):
                raise RuntimeError("Test exception")

        assert get_correlation_id() is None


class TestCorrelationIdFilter:
    """Unit tests for CorrelationIdFilter logging filter."""

    def test_filter_adds_correlation_id_to_record(self):
        """Test CorrelationIdFilter adds correlation_id attribute."""
        from nightwatch.logging_config import CorrelationIdFilter, set_correlation_id

        set_correlation_id("filter-test")
        filter_instance = CorrelationIdFilter()

        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="",
            lineno=0, msg="test", args=(), exc_info=None
        )

        result = filter_instance.filter(record)
        assert result is True
        assert hasattr(record, 'correlation_id')
        assert record.correlation_id == "filter-test"

        set_correlation_id(None)

    def test_filter_uses_dash_when_no_correlation_id(self):
        """Test filter uses '-' when no correlation ID is set."""
        from nightwatch.logging_config import CorrelationIdFilter, set_correlation_id

        set_correlation_id(None)
        filter_instance = CorrelationIdFilter()

        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="",
            lineno=0, msg="test", args=(), exc_info=None
        )

        filter_instance.filter(record)
        assert record.correlation_id == "-"


class TestSetupLoggingWithCorrelation:
    """Unit tests for setup_logging with correlation ID support."""

    def test_setup_logging_enables_correlation_by_default(self):
        """Test setup_logging enables correlation ID by default."""
        from nightwatch.logging_config import setup_logging

        setup_logging()

        root_logger = logging.getLogger("nightwatch")
        # Check that CorrelationIdFilter is added
        filter_types = [type(f).__name__ for f in root_logger.filters]
        assert "CorrelationIdFilter" in filter_types

    def test_setup_logging_disables_correlation(self):
        """Test setup_logging can disable correlation ID."""
        from nightwatch.logging_config import setup_logging

        setup_logging(enable_correlation=False)

        root_logger = logging.getLogger("nightwatch")
        filter_types = [type(f).__name__ for f in root_logger.filters]
        assert "CorrelationIdFilter" not in filter_types

    def test_correlation_id_appears_in_log_output(self):
        """Test correlation ID appears in formatted log output."""
        from nightwatch.logging_config import setup_logging, get_logger, correlation_context

        setup_logging(log_level="DEBUG", enable_correlation=True)
        logger = get_logger("correlation_test")

        with patch.object(logger, 'info') as mock_info:
            with correlation_context("test-cid-456"):
                logger.info("Test message")

            mock_info.assert_called_once()


class TestCorrelationIdThreadSafety:
    """Unit tests for correlation ID thread safety."""

    def test_correlation_id_isolated_between_threads(self):
        """Test correlation IDs are isolated between threads."""
        from nightwatch.logging_config import correlation_context, get_correlation_id

        results = {}

        def thread_func(thread_id, cid):
            with correlation_context(cid):
                # Small sleep to increase chance of interleaving
                time.sleep(0.01)
                results[thread_id] = get_correlation_id()

        threads = [
            threading.Thread(target=thread_func, args=(i, f"thread-{i}"))
            for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Each thread should see its own correlation ID
        for i in range(5):
            assert results[i] == f"thread-{i}"
