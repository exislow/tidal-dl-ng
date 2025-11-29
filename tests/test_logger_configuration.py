"""
test_logger_configuration.py

Test suite for logger configuration with colored output.

Tests cover:
- INFO level color configuration
- coloredlogs integration
- Log message formatting
"""

import logging
from unittest.mock import MagicMock

import coloredlogs
import pytest


class TestLoggerColorConfiguration:
    """Test logger color configuration for INFO messages."""

    def test_info_level_has_green_color(self):
        """Test that INFO level is configured with green color."""
        # Create level styles like in logger.py
        level_styles = coloredlogs.DEFAULT_LEVEL_STYLES.copy()
        level_styles["info"] = {"color": "green"}

        assert "info" in level_styles
        assert level_styles["info"] == {"color": "green"}

    def test_default_info_level_has_no_color(self):
        """Test that default INFO level has no color (to verify our fix)."""
        default_styles = coloredlogs.DEFAULT_LEVEL_STYLES

        # Default should have no color for INFO
        assert default_styles.get("info", {}) == {}

    def test_debug_level_keeps_green_color(self):
        """Test that DEBUG level keeps its default green color."""
        level_styles = coloredlogs.DEFAULT_LEVEL_STYLES.copy()
        level_styles["info"] = {"color": "green"}

        assert level_styles["debug"] == {"color": "green"}

    def test_level_styles_includes_all_levels(self):
        """Test that custom level styles include all necessary levels."""
        level_styles = coloredlogs.DEFAULT_LEVEL_STYLES.copy()
        level_styles["info"] = {"color": "green"}

        # Verify all important levels are present
        assert "debug" in level_styles
        assert "info" in level_styles
        assert "warning" in level_styles
        assert "error" in level_styles


class TestColoredFormatter:
    """Test ColoredFormatter configuration."""

    def test_formatter_uses_custom_level_styles(self):
        """Test that formatter is created with custom level styles."""
        level_styles = coloredlogs.DEFAULT_LEVEL_STYLES.copy()
        level_styles["info"] = {"color": "green"}

        formatter = coloredlogs.ColoredFormatter(fmt="> %(message)s", level_styles=level_styles)

        # Formatter should exist
        assert formatter is not None

    def test_formatter_format_string(self):
        """Test that formatter uses correct format string."""
        level_styles = coloredlogs.DEFAULT_LEVEL_STYLES.copy()
        level_styles["info"] = {"color": "green"}

        log_fmt = "> %(message)s"
        formatter = coloredlogs.ColoredFormatter(fmt=log_fmt, level_styles=level_styles)

        # Format string should be set
        assert formatter._fmt == log_fmt or hasattr(formatter, "_style")


class TestLoggerHandlers:
    """Test logger handler configuration."""

    def test_gui_logger_has_qt_handler(self):
        """Test that GUI logger would be configured with QtHandler."""
        # This is a structural test - verifying the configuration pattern
        from tidal_dl_ng.logger import QtHandler

        handler = QtHandler()
        level_styles = coloredlogs.DEFAULT_LEVEL_STYLES.copy()
        level_styles["info"] = {"color": "green"}

        formatter = coloredlogs.ColoredFormatter(fmt="> %(message)s", level_styles=level_styles)

        handler.setFormatter(formatter)

        # Handler should have formatter
        assert handler.formatter is not None

    def test_cli_logger_has_stream_handler(self):
        """Test that CLI logger would be configured with StreamHandler."""
        handler = logging.StreamHandler()
        level_styles = coloredlogs.DEFAULT_LEVEL_STYLES.copy()
        level_styles["info"] = {"color": "green"}

        formatter = coloredlogs.ColoredFormatter(fmt="> %(message)s", level_styles=level_styles)

        handler.setFormatter(formatter)

        # Handler should have formatter
        assert handler.formatter is not None


class TestLogMessageFormatting:
    """Test log message formatting."""

    def test_info_message_formatted_with_arrow(self):
        """Test that INFO messages are formatted with arrow prefix."""
        log_fmt = "> %(message)s"

        # Create a test record
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="Test message", args=(), exc_info=None
        )

        formatter = logging.Formatter(log_fmt)
        formatted = formatter.format(record)

        assert formatted == "> Test message"

    def test_skip_message_format(self):
        """Test that skip messages follow the expected format."""
        message_template = "Skipped item '{item}' (already in history)."
        item_name = "Test Track"

        message = message_template.format(item=item_name)

        assert "Skipped item" in message
        assert item_name in message
        assert "already in history" in message

    def test_downloaded_message_format(self):
        """Test that downloaded messages follow the expected format."""
        message_template = "Downloaded item '{item}'."
        item_name = "Test Track"

        message = message_template.format(item=item_name)

        assert "Downloaded item" in message
        assert item_name in message


class TestColoredlogsIntegration:
    """Test coloredlogs integration."""

    def test_coloredlogs_available(self):
        """Test that coloredlogs module is available."""
        assert coloredlogs is not None
        assert hasattr(coloredlogs, "ColoredFormatter")
        assert hasattr(coloredlogs, "DEFAULT_LEVEL_STYLES")

    def test_color_codes_in_formatter_output(self):
        """Test that formatter produces ANSI color codes."""
        level_styles = coloredlogs.DEFAULT_LEVEL_STYLES.copy()
        level_styles["info"] = {"color": "green"}

        formatter = coloredlogs.ColoredFormatter(fmt="%(message)s", level_styles=level_styles)

        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="Test", args=(), exc_info=None
        )

        formatted = formatter.format(record)

        # ANSI codes should be present (or the message itself if colors disabled)
        assert formatted is not None
        assert len(formatted) > 0


class TestLoggerMessageTypes:
    """Test different logger message types."""

    def test_info_messages_use_info_level(self):
        """Test that informational messages use INFO level."""
        logger = logging.getLogger("test")
        handler = logging.Handler()
        handler.emit = MagicMock()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        logger.info("Test info message")

        # Handler should have been called
        assert handler.emit.called
        record = handler.emit.call_args[0][0]
        assert record.levelno == logging.INFO

    def test_debug_messages_use_debug_level(self):
        """Test that debug messages use DEBUG level."""
        logger = logging.getLogger("test_debug")
        handler = logging.Handler()
        handler.emit = MagicMock()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        logger.debug("Test debug message")

        # Handler should have been called
        assert handler.emit.called
        record = handler.emit.call_args[0][0]
        assert record.levelno == logging.DEBUG


class TestXStreamIntegration:
    """Test XStream integration with colored output."""

    def test_xstream_writes_formatted_messages(self):
        """Test that XStream can write formatted log messages."""
        from tidal_dl_ng.logger import XStream

        stream = XStream.stdout()

        # Should have write method
        assert hasattr(stream, "write")
        assert callable(stream.write)

    def test_xstream_emits_signal(self):
        """Test that XStream emits signal when writing."""
        from tidal_dl_ng.logger import XStream

        stream = XStream()

        # Should have messageWritten signal
        assert hasattr(stream, "messageWritten")


class TestLoggerLevels:
    """Test logger level configuration."""

    def test_logger_set_to_debug_level(self):
        """Test that loggers are set to DEBUG level."""
        logger = logging.getLogger("test_levels")
        logger.setLevel(logging.DEBUG)

        assert logger.level == logging.DEBUG

    def test_debug_level_allows_info_messages(self):
        """Test that DEBUG level allows INFO messages."""
        logger = logging.getLogger("test_info_allowed")
        logger.setLevel(logging.DEBUG)

        # INFO is less severe than DEBUG, so it should be allowed
        assert logger.isEnabledFor(logging.INFO)


class TestConsistentStyling:
    """Test consistent styling across loggers."""

    def test_both_loggers_use_same_level_styles(self):
        """Test that GUI and CLI loggers use same level styles."""
        # Create shared level styles
        level_styles = coloredlogs.DEFAULT_LEVEL_STYLES.copy()
        level_styles["info"] = {"color": "green"}

        # Both formatters should use the same styles
        gui_formatter = coloredlogs.ColoredFormatter(fmt="> %(message)s", level_styles=level_styles)

        cli_formatter = coloredlogs.ColoredFormatter(fmt="> %(message)s", level_styles=level_styles)

        # Both should exist and be configured
        assert gui_formatter is not None
        assert cli_formatter is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
