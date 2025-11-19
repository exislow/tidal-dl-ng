"""Unit and integration tests for the artist separator configuration feature.

This module tests the new customizable artist separator functionality including:
- Delimiter construction from atomic parameters
- Configuration persistence and migration
- Integration with metadata tagging
- Backward compatibility with legacy delimiter format
"""

import json
import tempfile
from pathlib import Path

import pytest

from tidal_dl_ng.config import Settings
from tidal_dl_ng.constants import ArtistSeparator
from tidal_dl_ng.model.cfg import Settings as ModelSettings


class TestDelimiterConstruction:
    """Test the _build_delimiter static method with all possible combinations."""

    @pytest.mark.parametrize(
        "separator,space_before,space_after,expected",
        [
            # Comma variations
            (ArtistSeparator.COMMA, False, False, ","),
            (ArtistSeparator.COMMA, False, True, ", "),
            (ArtistSeparator.COMMA, True, False, " ,"),
            (ArtistSeparator.COMMA, True, True, " , "),
            # Semicolon variations
            (ArtistSeparator.SEMICOLON, False, False, ";"),
            (ArtistSeparator.SEMICOLON, False, True, "; "),
            (ArtistSeparator.SEMICOLON, True, False, " ;"),
            (ArtistSeparator.SEMICOLON, True, True, " ; "),
            # Ampersand variations
            (ArtistSeparator.AMPERSAND, False, False, "&"),
            (ArtistSeparator.AMPERSAND, False, True, "& "),
            (ArtistSeparator.AMPERSAND, True, False, " &"),
            (ArtistSeparator.AMPERSAND, True, True, " & "),
            # Plus variations
            (ArtistSeparator.PLUS, False, False, "+"),
            (ArtistSeparator.PLUS, False, True, "+ "),
            (ArtistSeparator.PLUS, True, False, " +"),
            (ArtistSeparator.PLUS, True, True, " + "),
            # Hyphen variations
            (ArtistSeparator.HYPHEN, False, False, "-"),
            (ArtistSeparator.HYPHEN, False, True, "- "),
            (ArtistSeparator.HYPHEN, True, False, " -"),
            (ArtistSeparator.HYPHEN, True, True, " - "),
            # Bullet variations
            (ArtistSeparator.BULLET, False, False, "•"),
            (ArtistSeparator.BULLET, False, True, "• "),
            (ArtistSeparator.BULLET, True, False, " •"),
            (ArtistSeparator.BULLET, True, True, " • "),
        ],
    )
    def test_build_delimiter_all_combinations(self, separator, space_before, space_after, expected):
        """Test all possible combinations of separators and spacing options."""
        result = Settings._build_delimiter(separator, space_before, space_after)
        assert result == expected, f"Expected '{expected}', got '{result}'"


class TestDelimiterHelperMethods:
    """Test the helper methods that construct delimiters from configuration."""

    def test_get_metadata_artist_delimiter_default(self):
        """Test default metadata artist delimiter is ', ' (backward compatible)."""
        # Use ModelSettings directly to get fresh defaults, not Settings which loads from file
        from tidal_dl_ng.model.cfg import Settings as ModelSettings

        settings_data = ModelSettings()
        delimiter = Settings._build_delimiter(
            settings_data.metadata_artist_separator,
            settings_data.metadata_artist_space_before,
            settings_data.metadata_artist_space_after,
        )
        assert delimiter == ", ", f"Expected ', ', got '{delimiter}'"

    def test_get_metadata_artist_delimiter_custom(self):
        """Test custom metadata artist delimiter with semicolon and spaces."""
        settings = Settings()
        settings.data.metadata_artist_separator = ArtistSeparator.SEMICOLON
        settings.data.metadata_artist_space_before = True
        settings.data.metadata_artist_space_after = True
        delimiter = settings.get_metadata_artist_delimiter()
        assert delimiter == " ; ", f"Expected ' ; ', got '{delimiter}'"

    def test_get_filename_artist_delimiter_no_spaces(self):
        """Test filename artist delimiter without spaces."""
        settings = Settings()
        settings.data.filename_artist_separator = ArtistSeparator.HYPHEN
        settings.data.filename_artist_space_before = False
        settings.data.filename_artist_space_after = False
        delimiter = settings.get_filename_artist_delimiter()
        assert delimiter == "-", f"Expected '-', got '{delimiter}'"

    def test_all_four_delimiter_types(self):
        """Test that all four delimiter types can be configured independently."""
        settings = Settings()

        # Configure each type differently
        settings.data.metadata_artist_separator = ArtistSeparator.COMMA
        settings.data.metadata_artist_space_before = False
        settings.data.metadata_artist_space_after = True

        settings.data.metadata_album_artist_separator = ArtistSeparator.SEMICOLON
        settings.data.metadata_album_artist_space_before = True
        settings.data.metadata_album_artist_space_after = True

        settings.data.filename_artist_separator = ArtistSeparator.HYPHEN
        settings.data.filename_artist_space_before = False
        settings.data.filename_artist_space_after = False

        settings.data.filename_album_artist_separator = ArtistSeparator.AMPERSAND
        settings.data.filename_album_artist_space_before = True
        settings.data.filename_album_artist_space_after = False

        # Verify each returns correct value
        assert settings.get_metadata_artist_delimiter() == ", "
        assert settings.get_metadata_album_artist_delimiter() == " ; "
        assert settings.get_filename_artist_delimiter() == "-"
        assert settings.get_filename_album_artist_delimiter() == " &"


class TestLegacyMigration:
    """Test backward compatibility and migration from legacy delimiter format."""

    def test_parse_legacy_delimiter_standard(self):
        """Test parsing standard legacy delimiter ', '."""
        settings = Settings()
        settings._parse_legacy_delimiter(
            ", ",
            "metadata_artist_separator",
            "metadata_artist_space_before",
            "metadata_artist_space_after",
        )

        assert settings.data.metadata_artist_separator == ArtistSeparator.COMMA
        assert settings.data.metadata_artist_space_before is False
        assert settings.data.metadata_artist_space_after is True

    def test_parse_legacy_delimiter_semicolon_spaces(self):
        """Test parsing legacy delimiter ' ; ' (Jellyfin format)."""
        settings = Settings()
        settings._parse_legacy_delimiter(
            " ; ",
            "metadata_artist_separator",
            "metadata_artist_space_before",
            "metadata_artist_space_after",
        )

        assert settings.data.metadata_artist_separator == ArtistSeparator.SEMICOLON
        assert settings.data.metadata_artist_space_before is True
        assert settings.data.metadata_artist_space_after is True

    def test_parse_legacy_delimiter_hyphen_no_spaces(self):
        """Test parsing legacy delimiter '-' (no spaces)."""
        settings = Settings()
        settings._parse_legacy_delimiter(
            "-",
            "filename_artist_separator",
            "filename_artist_space_before",
            "filename_artist_space_after",
        )

        assert settings.data.filename_artist_separator == ArtistSeparator.HYPHEN
        assert settings.data.filename_artist_space_before is False
        assert settings.data.filename_artist_space_after is False

    def test_parse_legacy_delimiter_invalid_fallback(self, caplog):
        """Test that invalid separators fallback to comma with warning."""
        import logging

        settings = Settings()

        with caplog.at_level(logging.WARNING):
            settings._parse_legacy_delimiter(
                "###",  # Invalid separator
                "metadata_artist_separator",
                "metadata_artist_space_before",
                "metadata_artist_space_after",
            )

        # Should fallback to comma
        assert settings.data.metadata_artist_separator == ArtistSeparator.COMMA

        # Should log warning
        assert "Warning" in caplog.text or "Invalid separator" in caplog.text
        assert "###" in caplog.text


class TestConfigurationPersistence:
    """Test saving and loading configuration to/from JSON files."""

    def test_save_and_load_custom_separators(self):
        """Test that custom separator configuration persists correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create custom settings
            test_file = Path(tmpdir) / "test_settings.json"

            # Create a settings object with custom config
            settings_data = ModelSettings()
            settings_data.metadata_artist_separator = ArtistSeparator.SEMICOLON
            settings_data.metadata_artist_space_before = True
            settings_data.metadata_artist_space_after = True
            settings_data.filename_artist_separator = ArtistSeparator.PLUS
            settings_data.filename_artist_space_before = False
            settings_data.filename_artist_space_after = False

            # Save to file
            with open(test_file, "w", encoding="utf-8") as f:
                json_data = json.loads(settings_data.to_json())
                json.dump(json_data, f, indent=4)

            # Load from file
            with open(test_file, encoding="utf-8") as f:
                json_str = f.read()
                loaded_data = ModelSettings.from_json(json_str)

            # Verify all fields persisted correctly
            assert loaded_data.metadata_artist_separator == ArtistSeparator.SEMICOLON
            assert loaded_data.metadata_artist_space_before is True
            assert loaded_data.metadata_artist_space_after is True
            assert loaded_data.filename_artist_separator == ArtistSeparator.PLUS
            assert loaded_data.filename_artist_space_before is False
            assert loaded_data.filename_artist_space_after is False


class TestIntegrationWithArtistNames:
    """Integration tests with mock artist name lists."""

    def test_artist_join_default_separator(self):
        """Test joining artist names with default separator."""
        artists = ["Artist A", "Artist B", "Artist C"]
        delimiter = Settings._build_delimiter(ArtistSeparator.COMMA, False, True)
        result = delimiter.join(artists)
        assert result == "Artist A, Artist B, Artist C"

    def test_artist_join_semicolon_spaces(self):
        """Test joining artist names with semicolon and spaces (Jellyfin format)."""
        artists = ["Artist A", "Artist B"]
        delimiter = Settings._build_delimiter(ArtistSeparator.SEMICOLON, True, True)
        result = delimiter.join(artists)
        assert result == "Artist A ; Artist B"

    def test_artist_join_hyphen_no_spaces(self):
        """Test joining artist names with hyphen no spaces."""
        artists = ["Artist A", "Artist B"]
        delimiter = Settings._build_delimiter(ArtistSeparator.HYPHEN, False, False)
        result = delimiter.join(artists)
        assert result == "Artist A-Artist B"

    def test_artist_join_bullet_with_spaces(self):
        """Test joining artist names with bullet point and spaces (clean visual)."""
        artists = ["Artist A", "Artist B"]
        delimiter = Settings._build_delimiter(ArtistSeparator.BULLET, True, True)
        result = delimiter.join(artists)
        assert result == "Artist A • Artist B"

    def test_artist_join_single_artist(self):
        """Test that single artist name works correctly with any separator."""
        artists = ["Solo Artist"]
        delimiter = Settings._build_delimiter(ArtistSeparator.SEMICOLON, True, True)
        result = delimiter.join(artists)
        # With single artist, separator doesn't matter
        assert result == "Solo Artist"

    def test_artist_join_empty_list(self):
        """Test that empty artist list returns empty string."""
        artists = []
        delimiter = Settings._build_delimiter(ArtistSeparator.COMMA, False, True)
        result = delimiter.join(artists)
        assert result == ""


class TestBackwardCompatibility:
    """Test that new code maintains backward compatibility with old configs."""

    def test_default_values_match_legacy(self):
        """Test that default atomic parameters produce same result as legacy default."""
        # Test default values directly from ModelSettings dataclass
        # rather than loading from potentially existing config file
        from tidal_dl_ng.model.cfg import Settings as ModelSettings

        settings_data = ModelSettings()

        # Build delimiters from default atomic parameters
        metadata_artist = Settings._build_delimiter(
            settings_data.metadata_artist_separator,
            settings_data.metadata_artist_space_before,
            settings_data.metadata_artist_space_after,
        )
        metadata_album_artist = Settings._build_delimiter(
            settings_data.metadata_album_artist_separator,
            settings_data.metadata_album_artist_space_before,
            settings_data.metadata_album_artist_space_after,
        )
        filename_artist = Settings._build_delimiter(
            settings_data.filename_artist_separator,
            settings_data.filename_artist_space_before,
            settings_data.filename_artist_space_after,
        )
        filename_album_artist = Settings._build_delimiter(
            settings_data.filename_album_artist_separator,
            settings_data.filename_album_artist_space_before,
            settings_data.filename_album_artist_space_after,
        )

        # All should default to ", " for backward compatibility
        assert metadata_artist == ", "
        assert metadata_album_artist == ", "
        assert filename_artist == ", "
        assert filename_album_artist == ", "

    def test_legacy_field_preservation(self):
        """Test that legacy fields are preserved in ModelSettings for migration."""
        settings_data = ModelSettings()

        # Legacy fields should exist with default values
        assert hasattr(settings_data, "metadata_delimiter_artist")
        assert hasattr(settings_data, "metadata_delimiter_album_artist")
        assert hasattr(settings_data, "filename_delimiter_artist")
        assert hasattr(settings_data, "filename_delimiter_album_artist")

        assert settings_data.metadata_delimiter_artist == ", "
        assert settings_data.metadata_delimiter_album_artist == ", "
        assert settings_data.filename_delimiter_artist == ", "
        assert settings_data.filename_delimiter_album_artist == ", "


class TestWhitelistValidation:
    """Test that only whitelisted separators are accepted."""

    def test_all_whitelisted_separators_valid(self):
        """Test that all enum values are valid separators."""
        valid_separators = [",", ";", "&", "+", "-", "•"]

        for sep_str in valid_separators:
            # Should not raise ValueError
            separator = ArtistSeparator(sep_str)
            assert separator.value == sep_str

    def test_invalid_separator_raises_error(self):
        """Test that invalid separators raise ValueError (including OS-problematic chars)."""
        invalid_separators = ["#", "@", "*", ":", "~", "..", "/", "|", "\\"]

        for invalid_sep in invalid_separators:
            with pytest.raises(ValueError):
                ArtistSeparator(invalid_sep)

    def test_enum_has_correct_count(self):
        """Test that enum contains exactly 6 whitelisted separators."""
        assert len(ArtistSeparator) == 6
        assert {sep.value for sep in ArtistSeparator} == {",", ";", "&", "+", "-", "•"}
