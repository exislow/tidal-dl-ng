"""Helper functions for CLI operations."""

from datetime import UTC, datetime

import typer


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse a timestamp string in various formats.

    Args:
        timestamp_str (str): Timestamp string in format YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, or Unix timestamp.

    Returns:
        datetime: Parsed datetime object (timezone-aware, UTC).

    Raises:
        typer.BadParameter: If the timestamp format is invalid.
    """
    # Try Unix timestamp first (numeric string)
    try:
        unix_timestamp: float = float(timestamp_str)
        return datetime.fromtimestamp(unix_timestamp, tz=UTC)
    except ValueError:
        pass

    # Try ISO format variants
    timestamp_formats: list[str] = [
        "%Y-%m-%d",  # 2024-01-15
        "%Y-%m-%dT%H:%M:%S",  # 2024-01-15T14:30:00
        "%Y-%m-%d %H:%M:%S",  # 2024-01-15 14:30:00
        "%Y/%m/%d",  # 2024/01/15
        "%Y-%m-%dT%H:%M:%S.%f",  # 2024-01-15T14:30:00.123456
    ]

    for fmt in timestamp_formats:
        try:
            # Parse the timestamp and make it timezone-aware (UTC)
            naive_dt: datetime = datetime.strptime(timestamp_str, fmt)
            return naive_dt.replace(tzinfo=UTC)
        except ValueError:
            continue

    msg: str = f"Invalid timestamp format: '{timestamp_str}'."
    raise typer.BadParameter(msg)
