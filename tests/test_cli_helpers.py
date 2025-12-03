"""Unit tests for CLI helper functions."""

from datetime import UTC, datetime

import pytest
import typer

from tidal_dl_ng.helper.cli import parse_timestamp


class TestParseTimestamp:
    """Test cases for parse_timestamp function."""

    def test_parse_unix_timestamp_integer(self) -> None:
        """Test parsing Unix timestamp as integer string."""
        # Unix timestamp for 2024-01-15 14:50:00 UTC
        timestamp_str: str = "1705330200"
        result: datetime = parse_timestamp(timestamp_str)

        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 14
        assert result.minute == 50
        assert result.second == 0
        assert result.tzinfo == UTC

    def test_parse_unix_timestamp_float(self) -> None:
        """Test parsing Unix timestamp with decimal precision."""
        # Unix timestamp with microseconds
        timestamp_str: str = "1705330200.123456"
        result: datetime = parse_timestamp(timestamp_str)

        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.microsecond == 123456
        assert result.tzinfo == UTC

    def test_parse_unix_timestamp_zero(self) -> None:
        """Test parsing Unix epoch (0)."""
        timestamp_str: str = "0"
        result: datetime = parse_timestamp(timestamp_str)

        assert result == datetime(1970, 1, 1, 0, 0, 0, tzinfo=UTC)

    def test_parse_iso_date_only(self) -> None:
        """Test parsing date in YYYY-MM-DD format."""
        timestamp_str: str = "2024-01-15"
        result: datetime = parse_timestamp(timestamp_str)

        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
        assert result.tzinfo == UTC

    def test_parse_iso_datetime_with_t(self) -> None:
        """Test parsing datetime in YYYY-MM-DDTHH:MM:SS format."""
        timestamp_str: str = "2024-01-15T14:30:45"
        result: datetime = parse_timestamp(timestamp_str)

        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 45
        assert result.tzinfo == UTC

    def test_parse_iso_datetime_with_space(self) -> None:
        """Test parsing datetime in YYYY-MM-DD HH:MM:SS format."""
        timestamp_str: str = "2024-01-15 14:30:45"
        result: datetime = parse_timestamp(timestamp_str)

        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 45
        assert result.tzinfo == UTC

    def test_parse_date_with_slashes(self) -> None:
        """Test parsing date in YYYY/MM/DD format."""
        timestamp_str: str = "2024/01/15"
        result: datetime = parse_timestamp(timestamp_str)

        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
        assert result.tzinfo == UTC

    def test_parse_iso_datetime_with_microseconds(self) -> None:
        """Test parsing datetime with microseconds in YYYY-MM-DDTHH:MM:SS.ffffff format."""
        timestamp_str: str = "2024-01-15T14:30:45.123456"
        result: datetime = parse_timestamp(timestamp_str)

        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 45
        assert result.microsecond == 123456
        assert result.tzinfo == UTC

    def test_parse_leap_year_date(self) -> None:
        """Test parsing a leap year date."""
        timestamp_str: str = "2024-02-29"
        result: datetime = parse_timestamp(timestamp_str)

        assert result.year == 2024
        assert result.month == 2
        assert result.day == 29
        assert result.tzinfo == UTC

    def test_parse_end_of_year(self) -> None:
        """Test parsing last day of year."""
        timestamp_str: str = "2024-12-31T23:59:59"
        result: datetime = parse_timestamp(timestamp_str)

        assert result.year == 2024
        assert result.month == 12
        assert result.day == 31
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59
        assert result.tzinfo == UTC

    def test_parse_invalid_format_raises_error(self) -> None:
        """Test that invalid timestamp format raises typer.BadParameter."""
        timestamp_str: str = "invalid-timestamp"

        with pytest.raises(typer.BadParameter) as exc_info:
            parse_timestamp(timestamp_str)

        assert "Invalid timestamp format" in str(exc_info.value)
        assert "invalid-timestamp" in str(exc_info.value)

    def test_parse_invalid_date_raises_error(self) -> None:
        """Test that invalid date (non-leap year Feb 29) raises typer.BadParameter."""
        timestamp_str: str = "2023-02-29"

        with pytest.raises(typer.BadParameter) as exc_info:
            parse_timestamp(timestamp_str)

        assert "Invalid timestamp format" in str(exc_info.value)

    def test_parse_invalid_month_raises_error(self) -> None:
        """Test that invalid month raises typer.BadParameter."""
        timestamp_str: str = "2024-13-01"

        with pytest.raises(typer.BadParameter) as exc_info:
            parse_timestamp(timestamp_str)

        assert "Invalid timestamp format" in str(exc_info.value)

    def test_parse_invalid_day_raises_error(self) -> None:
        """Test that invalid day raises typer.BadParameter."""
        timestamp_str: str = "2024-01-32"

        with pytest.raises(typer.BadParameter) as exc_info:
            parse_timestamp(timestamp_str)

        assert "Invalid timestamp format" in str(exc_info.value)

    def test_parse_empty_string_raises_error(self) -> None:
        """Test that empty string raises typer.BadParameter."""
        timestamp_str: str = ""

        with pytest.raises(typer.BadParameter) as exc_info:
            parse_timestamp(timestamp_str)

        assert "Invalid timestamp format" in str(exc_info.value)

    def test_parse_partial_datetime_raises_error(self) -> None:
        """Test that incomplete datetime format raises typer.BadParameter."""
        timestamp_str: str = "2024-01-15T14"

        with pytest.raises(typer.BadParameter) as exc_info:
            parse_timestamp(timestamp_str)

        assert "Invalid timestamp format" in str(exc_info.value)

    def test_parse_negative_unix_timestamp(self) -> None:
        """Test parsing negative Unix timestamp (before epoch)."""
        # Unix timestamp for 1969-12-31 23:59:59 UTC
        timestamp_str: str = "-1"
        result: datetime = parse_timestamp(timestamp_str)

        assert result.year == 1969
        assert result.month == 12
        assert result.day == 31
        assert result.tzinfo == UTC

    def test_parse_single_digit_month_and_day(self) -> None:
        """Test that single-digit month and day are accepted (Python's strptime allows them)."""
        # Python's strptime with %Y-%m-%d accepts single-digit months and days
        timestamp_str: str = "2024-1-5"
        result: datetime = parse_timestamp(timestamp_str)

        assert result.year == 2024
        assert result.month == 1
        assert result.day == 5
        assert result.tzinfo == UTC

    def test_parse_timezone_aware_result(self) -> None:
        """Test that all parsed timestamps are timezone-aware with UTC."""
        test_cases: list[str] = [
            "1705330200",
            "2024-01-15",
            "2024-01-15T14:30:45",
            "2024-01-15 14:30:45",
            "2024/01/15",
        ]

        for timestamp_str in test_cases:
            result: datetime = parse_timestamp(timestamp_str)
            assert result.tzinfo is not None, f"Result for '{timestamp_str}' is not timezone-aware"
            assert result.tzinfo == UTC, f"Result for '{timestamp_str}' is not UTC"

    def test_parse_whitespace_in_string_raises_error(self) -> None:
        """Test that leading/trailing whitespace causes error."""
        timestamp_str: str = " 2024-01-15 "

        with pytest.raises(typer.BadParameter) as exc_info:
            parse_timestamp(timestamp_str)

        assert "Invalid timestamp format" in str(exc_info.value)
