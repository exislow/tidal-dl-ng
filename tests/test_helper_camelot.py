"""Tests for Camelot wheel notation conversions."""

from tidal_dl_ng.helper.camelot import (
    CamelotNotation,
    KeyScale,
    alphanumeric_to_classic,
    alphanumeric_to_key,
    classic_to_alphanumeric,
    classic_to_key,
    format_initial_key,
    is_valid_alphanumeric,
    is_valid_classic,
    is_valid_key,
    key_to_alphanumeric,
    key_to_classic,
)


class TestKeyToAlphanumeric:
    """Test key_to_alphanumeric function."""

    def test_major_keys(self):
        """Test conversion of major keys to alphanumeric notation."""
        assert key_to_alphanumeric("C", KeyScale.MAJOR) == "8B"
        assert key_to_alphanumeric("E", KeyScale.MAJOR) == "12B"
        assert key_to_alphanumeric("G", KeyScale.MAJOR) == "9B"

    def test_minor_keys(self):
        """Test conversion of minor keys to alphanumeric notation."""
        assert key_to_alphanumeric("G", KeyScale.MINOR) == "6A"
        assert key_to_alphanumeric("A", KeyScale.MINOR) == "8A"
        assert key_to_alphanumeric("D", KeyScale.MINOR) == "7A"

    def test_flat_keys(self):
        """Test conversion of flat keys to alphanumeric notation."""
        assert key_to_alphanumeric("Eb", KeyScale.MINOR) == "2A"
        assert key_to_alphanumeric("Ab", KeyScale.MAJOR) == "4B"
        assert key_to_alphanumeric("Bb", KeyScale.MAJOR) == "6B"

    def test_sharp_keys(self):
        """Test conversion of sharp keys (FSharp) to alphanumeric notation."""
        assert key_to_alphanumeric("FSharp", KeyScale.MAJOR) == "2B"
        assert key_to_alphanumeric("FSharp", KeyScale.MINOR) == "11A"

    def test_string_scale_parameter(self):
        """Test that string scale parameters work."""
        assert key_to_alphanumeric("C", "MAJOR") == "8B"
        assert key_to_alphanumeric("G", "MINOR") == "6A"

    def test_invalid_key(self):
        """Test that invalid keys return None."""
        assert key_to_alphanumeric("H", KeyScale.MAJOR) is None
        assert key_to_alphanumeric("X", KeyScale.MINOR) is None

    def test_invalid_scale(self):
        """Test that invalid scale strings return None."""
        assert key_to_alphanumeric("C", "INVALID") is None


class TestKeyToClassic:
    """Test key_to_classic function."""

    def test_major_keys(self):
        """Test conversion of major keys to classic notation."""
        assert key_to_classic("C", KeyScale.MAJOR) == "C"
        assert key_to_classic("E", KeyScale.MAJOR) == "E"
        assert key_to_classic("G", KeyScale.MAJOR) == "G"

    def test_minor_keys(self):
        """Test conversion of minor keys to classic notation."""
        assert key_to_classic("G", KeyScale.MINOR) == "Gm"
        assert key_to_classic("A", KeyScale.MINOR) == "Am"
        assert key_to_classic("Db", KeyScale.MINOR) == "Dbm"

    def test_flat_keys(self):
        """Test conversion of flat keys to classic notation."""
        assert key_to_classic("Eb", KeyScale.MINOR) == "Ebm"
        assert key_to_classic("Ab", KeyScale.MAJOR) == "Ab"

    def test_sharp_keys(self):
        """Test conversion of sharp keys to classic notation."""
        assert key_to_classic("FSharp", KeyScale.MINOR) == "F#m"
        assert key_to_classic("FSharp", KeyScale.MAJOR) == "Gb"

    def test_string_scale_parameter(self):
        """Test that string scale parameters work."""
        assert key_to_classic("C", "MAJOR") == "C"
        assert key_to_classic("G", "MINOR") == "Gm"

    def test_invalid_key(self):
        """Test that invalid keys return None."""
        assert key_to_classic("H", KeyScale.MAJOR) is None


class TestClassicToKey:
    """Test classic_to_key function."""

    def test_major_keys(self):
        """Test conversion of classic notation to major keys."""
        result = classic_to_key("C")
        assert result is not None
        key, scale = result
        assert key == "C"
        assert scale == KeyScale.MAJOR

        result = classic_to_key("E")
        assert result is not None
        key, scale = result
        assert key == "E"
        assert scale == KeyScale.MAJOR

    def test_minor_keys(self):
        """Test conversion of classic notation to minor keys."""
        result = classic_to_key("Gm")
        assert result is not None
        key, scale = result
        assert key == "G"
        assert scale == KeyScale.MINOR

        result = classic_to_key("Am")
        assert result is not None
        key, scale = result
        assert key == "A"
        assert scale == KeyScale.MINOR

    def test_case_insensitive(self):
        """Test that classic notation is case-insensitive."""
        result = classic_to_key("gm")
        assert result is not None
        key, scale = result
        assert key == "G"
        assert scale == KeyScale.MINOR

    def test_invalid_notation(self):
        """Test that invalid classic notation returns None."""
        assert classic_to_key("H") is None
        assert classic_to_key("Xm") is None
        assert classic_to_key("Z") is None


class TestAlphanumericToKey:
    """Test alphanumeric_to_key function."""

    def test_major_keys(self):
        """Test conversion of alphanumeric notation to major keys."""
        result = alphanumeric_to_key("8B")
        assert result is not None
        key, scale = result
        assert key == "C"
        assert scale == KeyScale.MAJOR

        result = alphanumeric_to_key("12B")
        assert result is not None
        key, scale = result
        assert key == "E"
        assert scale == KeyScale.MAJOR

    def test_minor_keys(self):
        """Test conversion of alphanumeric notation to minor keys."""
        result = alphanumeric_to_key("6A")
        assert result is not None
        key, scale = result
        assert key == "G"
        assert scale == KeyScale.MINOR

        result = alphanumeric_to_key("8A")
        assert result is not None
        key, scale = result
        assert key == "A"
        assert scale == KeyScale.MINOR

    def test_sharp_notation(self):
        """Test conversion of FSharp alphanumeric notation."""
        result = alphanumeric_to_key("11A")
        assert result is not None
        key, scale = result
        assert key == "FSharp"
        assert scale == KeyScale.MINOR

    def test_case_variations(self):
        """Test that case variations are handled."""
        result = alphanumeric_to_key("6a")
        assert result is not None
        key, scale = result
        assert key == "G"
        assert scale == KeyScale.MINOR

    def test_invalid_notation(self):
        """Test that invalid alphanumeric notation returns None."""
        assert alphanumeric_to_key("13A") is None
        assert alphanumeric_to_key("0B") is None


class TestClassicToAlphanumeric:
    """Test classic_to_alphanumeric function."""

    def test_major_conversions(self):
        """Test conversion from classic to alphanumeric for major keys."""
        assert classic_to_alphanumeric("C") == "8B"
        assert classic_to_alphanumeric("E") == "12B"
        assert classic_to_alphanumeric("G") == "9B"

    def test_minor_conversions(self):
        """Test conversion from classic to alphanumeric for minor keys."""
        assert classic_to_alphanumeric("Gm") == "6A"
        assert classic_to_alphanumeric("Am") == "8A"
        assert classic_to_alphanumeric("Dbm") == "12A"

    def test_invalid_notation(self):
        """Test that invalid classic notation returns None."""
        assert classic_to_alphanumeric("H") is None


class TestAlphanumericToClassic:
    """Test alphanumeric_to_classic function."""

    def test_major_conversions(self):
        """Test conversion from alphanumeric to classic for major keys."""
        assert alphanumeric_to_classic("8B") == "C"
        assert alphanumeric_to_classic("12B") == "E"
        assert alphanumeric_to_classic("9B") == "G"

    def test_minor_conversions(self):
        """Test conversion from alphanumeric to classic for minor keys."""
        assert alphanumeric_to_classic("6A") == "Gm"
        assert alphanumeric_to_classic("8A") == "Am"
        assert alphanumeric_to_classic("12A") == "Dbm"

    def test_invalid_notation(self):
        """Test that invalid alphanumeric notation returns None."""
        assert alphanumeric_to_classic("13A") is None


class TestValidationFunctions:
    """Test validation functions."""

    def test_is_valid_key(self):
        """Test is_valid_key function."""
        assert is_valid_key("C", KeyScale.MAJOR) is True
        assert is_valid_key("G", KeyScale.MINOR) is True
        assert is_valid_key("FSharp", KeyScale.MAJOR) is True
        assert is_valid_key("H", KeyScale.MAJOR) is False
        assert is_valid_key("C", "INVALID") is False

    def test_is_valid_classic(self):
        """Test is_valid_classic function."""
        assert is_valid_classic("C") is True
        assert is_valid_classic("Gm") is True
        assert is_valid_classic("F#m") is True
        assert is_valid_classic("H") is False
        assert is_valid_classic("Xm") is False
        assert is_valid_classic("13A") is False

    def test_is_valid_alphanumeric(self):
        """Test is_valid_alphanumeric function."""
        assert is_valid_alphanumeric("8B") is True
        assert is_valid_alphanumeric("6A") is True
        assert is_valid_alphanumeric("12A") is True
        assert is_valid_alphanumeric("13A") is False
        assert is_valid_alphanumeric("0B") is False


class TestFormatInitialKey:
    """Test format_initial_key function."""

    def test_format_classic_major(self):
        """Test formatting to classic notation for major keys."""
        assert format_initial_key("C", "MAJOR", CamelotNotation.CLASSIC) == "C"
        assert format_initial_key("E", "MAJOR", "classic") == "E"

    def test_format_classic_minor(self):
        """Test formatting to classic notation for minor keys."""
        assert format_initial_key("G", "MINOR", CamelotNotation.CLASSIC) == "Gm"
        assert format_initial_key("A", "MINOR", "classic") == "Am"

    def test_format_alphanumeric_major(self):
        """Test formatting to alphanumeric notation for major keys."""
        assert format_initial_key("C", "MAJOR", CamelotNotation.ALPHANUMERIC) == "8B"
        assert format_initial_key("E", "MAJOR", "alphanumeric") == "12B"

    def test_format_alphanumeric_minor(self):
        """Test formatting to alphanumeric notation for minor keys."""
        assert format_initial_key("G", "MINOR", CamelotNotation.ALPHANUMERIC) == "6A"
        assert format_initial_key("A", "MINOR", "alphanumeric") == "8A"

    def test_format_unknown_key(self):
        """Test that UNKNOWN key returns empty string."""
        assert format_initial_key("UNKNOWN", "MAJOR", CamelotNotation.CLASSIC) == ""
        assert format_initial_key("UNKNOWN", "MINOR", CamelotNotation.ALPHANUMERIC) == ""

    def test_format_unknown_scale(self):
        """Test that UNKNOWN scale returns empty string."""
        assert format_initial_key("C", "UNKNOWN", CamelotNotation.CLASSIC) == ""
        assert format_initial_key("G", "UNKNOWN", CamelotNotation.ALPHANUMERIC) == ""

    def test_format_both_unknown(self):
        """Test that both UNKNOWN returns empty string."""
        assert format_initial_key("UNKNOWN", "UNKNOWN", CamelotNotation.CLASSIC) == ""
        assert format_initial_key("UNKNOWN", "UNKNOWN", CamelotNotation.ALPHANUMERIC) == ""

    def test_format_invalid_key(self):
        """Test that invalid key returns empty string."""
        assert format_initial_key("InvalidKey", "MAJOR", CamelotNotation.CLASSIC) == ""
        assert format_initial_key("H", "MINOR", CamelotNotation.ALPHANUMERIC) == ""

    def test_format_invalid_format(self):
        """Test that invalid format returns empty string."""
        assert format_initial_key("C", "MAJOR", "invalid_format") == ""

    def test_format_fsharp_keys(self):
        """Test formatting FSharp keys in both notations."""
        assert format_initial_key("FSharp", "MINOR", CamelotNotation.CLASSIC) == "F#m"
        assert format_initial_key("FSharp", "MINOR", CamelotNotation.ALPHANUMERIC) == "11A"
        assert format_initial_key("FSharp", "MAJOR", CamelotNotation.CLASSIC) == "Gb"
        assert format_initial_key("FSharp", "MAJOR", CamelotNotation.ALPHANUMERIC) == "2B"


class TestRoundTripConversions:
    """Test round-trip conversions to ensure consistency."""

    def test_key_to_alphanumeric_to_key(self):
        """Test that key -> alphanumeric -> key preserves values."""
        original_key = "C"
        original_scale = KeyScale.MAJOR

        alphanumeric = key_to_alphanumeric(original_key, original_scale)
        assert alphanumeric is not None

        result = alphanumeric_to_key(alphanumeric)
        assert result is not None

        result_key, result_scale = result
        assert result_key == original_key
        assert result_scale == original_scale

    def test_key_to_classic_to_key(self):
        """Test that key -> classic -> key preserves values."""
        original_key = "G"
        original_scale = KeyScale.MINOR

        classic = key_to_classic(original_key, original_scale)
        assert classic is not None

        result = classic_to_key(classic)
        assert result is not None

        result_key, result_scale = result
        assert result_key == original_key
        assert result_scale == original_scale

    def test_alphanumeric_to_classic_to_alphanumeric(self):
        """Test that alphanumeric -> classic -> alphanumeric preserves values."""
        original_alphanumeric = "8B"

        classic = alphanumeric_to_classic(original_alphanumeric)
        assert classic is not None

        result_alphanumeric = classic_to_alphanumeric(classic)
        assert result_alphanumeric == original_alphanumeric
