"""Helper module for Camelot wheel notation conversions.

The Camelot wheel is a tool for harmonic mixing in DJing. It has two notation systems:
- Classic: 1A, 2A, ..., 12A (minor keys) and 1B, 2B, ..., 12B (major keys)
- Alphanumeric/Open Key: Abm, Dbm, ... (minor) and B, E, ... (major)

This module provides bidirectional conversion between these formats.
"""

from enum import StrEnum


class KeyScale(StrEnum):
    """Musical key scale types."""

    MAJOR = "MAJOR"
    MINOR = "MINOR"


class CamelotNotation(StrEnum):
    """Camelot wheel notation types."""

    CLASSIC = "classic"  # Abm, B, Dbm, E format (Open Key)
    ALPHANUMERIC = "alphanumeric"  # 1A, 2A, ..., 12B format


# Mapping: (key, scale) -> Camelot alphanumeric notation
_KEY_TO_ALPHANUMERIC: dict[tuple[str, KeyScale], str] = {
    # Minor keys (A)
    ("Ab", KeyScale.MINOR): "1A",
    ("Eb", KeyScale.MINOR): "2A",
    ("Bb", KeyScale.MINOR): "3A",
    ("F", KeyScale.MINOR): "4A",
    ("C", KeyScale.MINOR): "5A",
    ("G", KeyScale.MINOR): "6A",
    ("D", KeyScale.MINOR): "7A",
    ("A", KeyScale.MINOR): "8A",
    ("E", KeyScale.MINOR): "9A",
    ("B", KeyScale.MINOR): "10A",
    ("FSharp", KeyScale.MINOR): "11A",
    ("Db", KeyScale.MINOR): "12A",
    # Major keys (B)
    ("B", KeyScale.MAJOR): "1B",
    ("FSharp", KeyScale.MAJOR): "2B",
    ("Db", KeyScale.MAJOR): "3B",
    ("Ab", KeyScale.MAJOR): "4B",
    ("Eb", KeyScale.MAJOR): "5B",
    ("Bb", KeyScale.MAJOR): "6B",
    ("F", KeyScale.MAJOR): "7B",
    ("C", KeyScale.MAJOR): "8B",
    ("G", KeyScale.MAJOR): "9B",
    ("D", KeyScale.MAJOR): "10B",
    ("A", KeyScale.MAJOR): "11B",
    ("E", KeyScale.MAJOR): "12B",
}

# Reverse mapping: Camelot alphanumeric -> (key, scale)
_ALPHANUMERIC_TO_KEY: dict[str, tuple[str, KeyScale]] = {v: k for k, v in _KEY_TO_ALPHANUMERIC.items()}

# Classic display format mapping
_KEY_TO_CLASSIC: dict[tuple[str, KeyScale], str] = {
    # Minor keys
    ("Ab", KeyScale.MINOR): "Abm",
    ("Eb", KeyScale.MINOR): "Ebm",
    ("Bb", KeyScale.MINOR): "Bbm",
    ("F", KeyScale.MINOR): "Fm",
    ("C", KeyScale.MINOR): "Cm",
    ("G", KeyScale.MINOR): "Gm",
    ("D", KeyScale.MINOR): "Dm",
    ("A", KeyScale.MINOR): "Am",
    ("E", KeyScale.MINOR): "Em",
    ("B", KeyScale.MINOR): "Bm",
    ("FSharp", KeyScale.MINOR): "F#m",
    ("Db", KeyScale.MINOR): "Dbm",
    # Major keys
    ("B", KeyScale.MAJOR): "B",
    ("FSharp", KeyScale.MAJOR): "Gb",
    ("Db", KeyScale.MAJOR): "Db",
    ("Ab", KeyScale.MAJOR): "Ab",
    ("Eb", KeyScale.MAJOR): "Eb",
    ("Bb", KeyScale.MAJOR): "Bb",
    ("F", KeyScale.MAJOR): "F",
    ("C", KeyScale.MAJOR): "C",
    ("G", KeyScale.MAJOR): "G",
    ("D", KeyScale.MAJOR): "D",
    ("A", KeyScale.MAJOR): "A",
    ("E", KeyScale.MAJOR): "E",
}

# Reverse mapping: Classic -> (key, scale)
_CLASSIC_TO_KEY: dict[str, tuple[str, KeyScale]] = {v: k for k, v in _KEY_TO_CLASSIC.items()}


def key_to_alphanumeric(key: str, key_scale: KeyScale | str) -> str | None:
    """Convert key and scale to Camelot alphanumeric notation.

    Args:
        key (str): Musical key (e.g., 'C', 'Eb', 'FSharp').
        key_scale (KeyScale | str): Scale type ('MAJOR' or 'MINOR').

    Returns:
        str | None: Alphanumeric notation (e.g., "8B", "6A", "11A") or None if invalid.

    Example:
        >>> key_to_alphanumeric("C", KeyScale.MAJOR)
        '8B'
        >>> key_to_alphanumeric("G", "MINOR")
        '6A'
        >>> key_to_alphanumeric("FSharp", KeyScale.MAJOR)
        '2B'
    """
    # Normalize key_scale to enum
    if isinstance(key_scale, str):
        try:
            key_scale = KeyScale(key_scale.upper())
        except ValueError:
            return None

    # Normalize key input
    normalized_key = _normalize_key_input(key)

    return _KEY_TO_ALPHANUMERIC.get((normalized_key, key_scale))


def key_to_classic(key: str, key_scale: KeyScale | str) -> str | None:
    """Convert key and scale to Camelot classic (Open Key) notation.

    Args:
        key (str): Musical key (e.g., 'C', 'Eb', 'FSharp').
        key_scale (KeyScale | str): Scale type ('MAJOR' or 'MINOR').

    Returns:
        str | None: Classic notation (e.g., "C", "Gm", "Gb") or None if invalid.

    Example:
        >>> key_to_classic("C", KeyScale.MAJOR)
        'C'
        >>> key_to_classic("G", "MINOR")
        'Gm'
        >>> key_to_classic("FSharp", KeyScale.MINOR)
        'F#m'
    """
    # Normalize key_scale to enum
    if isinstance(key_scale, str):
        try:
            key_scale = KeyScale(key_scale.upper())
        except ValueError:
            return None

    # Normalize key input (handle variations)
    normalized_key = _normalize_key_input(key)

    return _KEY_TO_CLASSIC.get((normalized_key, key_scale))


def classic_to_key(classic: str) -> tuple[str, KeyScale] | None:
    """Convert Camelot classic (Open Key) notation to key and scale.

    Args:
        classic (str): Classic notation (e.g., "C", "Gm", "F#m").

    Returns:
        tuple[str, KeyScale] | None: Tuple of (key, scale) or None if invalid.

    Example:
        >>> classic_to_key("C")
        ('C', <KeyScale.MAJOR: 'MAJOR'>)
        >>> classic_to_key("Gm")
        ('G', <KeyScale.MINOR: 'MINOR'>)
    """
    # Normalize input to handle case variations
    classic_normalized = classic.strip()

    # Try direct lookup first
    if result := _CLASSIC_TO_KEY.get(classic_normalized):
        return result

    # Try with different casing (e.g., "gm" -> "Gm")
    if len(classic_normalized) >= 2:
        # Try capitalizing first letter
        classic_normalized = classic_normalized[0].upper() + classic_normalized[1:]
        return _CLASSIC_TO_KEY.get(classic_normalized)

    return None


def alphanumeric_to_key(alphanumeric: str) -> tuple[str, KeyScale] | None:
    """Convert Camelot alphanumeric notation to key and scale.

    Args:
        alphanumeric (str): Alphanumeric notation (e.g., "8B", "6A", "11A").

    Returns:
        tuple[str, KeyScale] | None: Tuple of (key, scale) or None if invalid.

    Example:
        >>> alphanumeric_to_key("8B")
        ('C', <KeyScale.MAJOR: 'MAJOR'>)
        >>> alphanumeric_to_key("6A")
        ('G', <KeyScale.MINOR: 'MINOR'>)
        >>> alphanumeric_to_key("11A")
        ('FSharp', <KeyScale.MINOR: 'MINOR'>)
    """
    return _ALPHANUMERIC_TO_KEY.get(alphanumeric.upper())


def classic_to_alphanumeric(classic: str) -> str | None:
    """Convert Camelot classic notation to alphanumeric notation.

    Args:
        classic (str): Classic notation (e.g., "C", "Gm", "F#m").

    Returns:
        str | None: Alphanumeric notation (e.g., "8B", "6A") or None if invalid.

    Example:
        >>> classic_to_alphanumeric("C")
        '8B'
        >>> classic_to_alphanumeric("Gm")
        '6A'
    """
    key_scale_tuple = classic_to_key(classic)
    if not key_scale_tuple:
        return None

    key, scale = key_scale_tuple
    return key_to_alphanumeric(key, scale)


def alphanumeric_to_classic(alphanumeric: str) -> str | None:
    """Convert Camelot alphanumeric notation to classic notation.

    Args:
        alphanumeric (str): Alphanumeric notation (e.g., "8B", "6A").

    Returns:
        str | None: Classic notation (e.g., "C", "Gm") or None if invalid.

    Example:
        >>> alphanumeric_to_classic("8B")
        'C'
        >>> alphanumeric_to_classic("6A")
        'Gm'
    """
    key_scale_tuple = alphanumeric_to_key(alphanumeric)
    if not key_scale_tuple:
        return None

    key, scale = key_scale_tuple
    return key_to_classic(key, scale)


def format_initial_key(key: str, key_scale: str, initial_key_format: CamelotNotation | str) -> str:
    """Format musical key according to specified notation system.

    Converts a musical key and scale into the requested Camelot notation format.
    Returns empty string if key or scale is UNKNOWN, or if conversion fails.

    Args:
        key (str): Musical key (e.g., 'C', 'Eb', 'FSharp') or 'UNKNOWN'.
        key_scale (str): Scale type ('MAJOR', 'MINOR') or 'UNKNOWN'.
        initial_key_format (CamelotNotation | str): Desired output format
            ('classic' or 'alphanumeric').

    Returns:
        str: Formatted key string or empty string if invalid/unknown.

    Example:
        >>> format_initial_key("C", "MAJOR", CamelotNotation.CLASSIC)
        'C'
        >>> format_initial_key("C", "MAJOR", "alphanumeric")
        '8B'
        >>> format_initial_key("UNKNOWN", "MAJOR", CamelotNotation.CLASSIC)
        ''
        >>> format_initial_key("C", "UNKNOWN", CamelotNotation.CLASSIC)
        ''
    """
    # Early return for UNKNOWN values
    if not key or not key_scale or key == "UNKNOWN" or key_scale == "UNKNOWN":
        return ""

    # Normalize format parameter to enum
    if isinstance(initial_key_format, str):
        try:
            initial_key_format = CamelotNotation(initial_key_format.lower())
        except ValueError:
            return ""

    # Convert to requested format
    result: str | None = None

    if initial_key_format == CamelotNotation.CLASSIC:
        result = key_to_classic(key, key_scale)
    elif initial_key_format == CamelotNotation.ALPHANUMERIC:
        result = key_to_alphanumeric(key, key_scale)

    # Return formatted string or empty string if conversion failed
    return result if result is not None else ""


def is_valid_key(key: str, key_scale: KeyScale | str) -> bool:
    """Check if key and scale combination is valid.

    Args:
        key (str): Musical key to validate.
        key_scale (KeyScale | str): Scale type.

    Returns:
        bool: True if valid key/scale combination.

    Example:
        >>> is_valid_key("C", KeyScale.MAJOR)
        True
        >>> is_valid_key("H", KeyScale.MINOR)
        False
    """
    if isinstance(key_scale, str):
        try:
            key_scale = KeyScale(key_scale.upper())
        except ValueError:
            return False

    normalized_key = _normalize_key_input(key)
    return (normalized_key, key_scale) in _KEY_TO_ALPHANUMERIC


def is_valid_classic(classic: str) -> bool:
    """Check if a string is valid Camelot classic notation.

    Args:
        classic (str): String to validate.

    Returns:
        bool: True if valid classic notation (e.g., "C", "Gm", "F#m").

    Example:
        >>> is_valid_classic("C")
        True
        >>> is_valid_classic("Gm")
        True
        >>> is_valid_classic("H")
        False
    """
    return classic_to_key(classic) is not None


def is_valid_alphanumeric(alphanumeric: str) -> bool:
    """Check if a string is valid Camelot alphanumeric notation.

    Args:
        alphanumeric (str): String to validate.

    Returns:
        bool: True if valid alphanumeric notation (1A-12A, 1B-12B).

    Example:
        >>> is_valid_alphanumeric("8B")
        True
        >>> is_valid_alphanumeric("6A")
        True
        >>> is_valid_alphanumeric("13A")
        False
    """
    return alphanumeric.upper() in _ALPHANUMERIC_TO_KEY


def _normalize_key_input(key: str) -> str:
    """Normalize key input variations to standard format.

    Handles variations like 'F#', 'Gb', 'f sharp', etc.

    Args:
        key (str): Key input string.

    Returns:
        str: Normalized key (e.g., 'C', 'Eb', 'FSharp').
    """
    # Remove spaces and convert to title case
    key_clean = key.replace(" ", "").replace("sharp", "Sharp").replace("#", "Sharp")

    # Handle flat notation
    if "b" in key_clean and "Sharp" not in key_clean:
        # Already in flat format (e.g., 'Eb', 'Ab')
        return key_clean

    # Map sharp keys to their enharmonic flat equivalents where needed
    sharp_to_flat: dict[str, str] = {
        "CSharp": "Db",
        "DSharp": "Eb",
        "GSharp": "Ab",
        "ASharp": "Bb",
        # FSharp stays as is (it's used in the mapping)
    }

    return sharp_to_flat.get(key_clean, key_clean)
