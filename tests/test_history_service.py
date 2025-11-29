"""
test_history_service.py

Test suite for the HistoryService class and download history functionality.

Tests cover:
- History service initialization
- Track addition and removal
- Duplicate prevention logic
- Settings management
- JSON persistence and corruption recovery
- Import/Export functionality
- Statistics calculation
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from tidal_dl_ng.history import HistoryService


@pytest.fixture
def temp_history_file(tmp_path: Path) -> Path:
    """Create a temporary directory for history file storage.

    Args:
        tmp_path: pytest fixture providing temporary directory.

    Returns:
        Path to temporary directory.
    """
    return tmp_path


@pytest.fixture
def history_service(temp_history_file: Path, monkeypatch) -> HistoryService:
    """Create a HistoryService instance with a temporary file.

    Args:
        temp_history_file: Temporary directory path.
        monkeypatch: pytest monkeypatch fixture.

    Returns:
        Configured HistoryService instance.
    """
    # Mock the config path to use temp directory
    mock_config_path = temp_history_file / "config"
    mock_config_path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("tidal_dl_ng.history.path_config_base", lambda: str(mock_config_path))

    # Reset singleton instance
    if hasattr(HistoryService, "_instances"):
        HistoryService._instances = {}

    return HistoryService()


class TestHistoryServiceInitialization:
    """Test history service initialization and file creation."""

    def test_service_init_creates_empty_history(self, history_service: HistoryService):
        """Test that initialization creates an empty history."""
        assert history_service.history_data == {}
        assert history_service.settings_data == {"preventDuplicates": True}
        assert history_service.file_path.exists()

    def test_service_init_creates_json_file(self, history_service: HistoryService):
        """Test that JSON file is created with correct structure."""
        with open(history_service.file_path, encoding="utf-8") as f:
            data = json.load(f)

        assert "_schema_version" in data
        assert data["_schema_version"] == 1
        assert "settings" in data
        assert "tracks" in data
        assert data["tracks"] == {}

    def test_service_singleton_pattern(self, history_service: HistoryService):
        """Test that HistoryService follows singleton pattern."""
        service2 = HistoryService()
        assert service2 is history_service


class TestTrackOperations:
    """Test track addition, removal, and queries."""

    def test_add_track_to_history(self, history_service: HistoryService):
        """Test adding a track to history."""
        track_id = "12345678"
        history_service.add_track_to_history(
            track_id=track_id, source_type="playlist", source_id="pl-123", source_name="My Playlist"
        )

        assert track_id in history_service.history_data
        assert history_service.history_data[track_id]["sourceType"] == "playlist"
        assert history_service.history_data[track_id]["sourceId"] == "pl-123"
        assert history_service.history_data[track_id]["sourceName"] == "My Playlist"
        assert "downloadDate" in history_service.history_data[track_id]

    def test_add_track_persists_to_file(self, history_service: HistoryService):
        """Test that adding a track persists to the JSON file."""
        track_id = "87654321"
        history_service.add_track_to_history(track_id=track_id, source_type="album")

        # Reload from file
        with open(history_service.file_path, encoding="utf-8") as f:
            data = json.load(f)

        assert track_id in data["tracks"]

    def test_is_downloaded_returns_true_for_existing_track(self, history_service: HistoryService):
        """Test that is_downloaded returns True for existing tracks."""
        track_id = "11111111"
        history_service.add_track_to_history(track_id=track_id)

        assert history_service.is_downloaded(track_id) is True

    def test_is_downloaded_returns_false_for_missing_track(self, history_service: HistoryService):
        """Test that is_downloaded returns False for missing tracks."""
        assert history_service.is_downloaded("99999999") is False

    def test_remove_track_from_history(self, history_service: HistoryService):
        """Test removing a track from history."""
        track_id = "22222222"
        history_service.add_track_to_history(track_id=track_id)

        result = history_service.remove_track_from_history(track_id)

        assert result is True
        assert track_id not in history_service.history_data

    def test_remove_nonexistent_track_returns_false(self, history_service: HistoryService):
        """Test that removing a nonexistent track returns False."""
        result = history_service.remove_track_from_history("nonexistent")
        assert result is False

    def test_get_track_info_returns_correct_data(self, history_service: HistoryService):
        """Test getting track info returns complete data."""
        track_id = "33333333"
        history_service.add_track_to_history(
            track_id=track_id, source_type="mix", source_id="mx-456", source_name="Dance Mix"
        )

        info = history_service.get_track_info(track_id)

        assert info is not None
        assert info["sourceType"] == "mix"
        assert info["sourceId"] == "mx-456"
        assert info["sourceName"] == "Dance Mix"

    def test_get_track_info_returns_none_for_missing(self, history_service: HistoryService):
        """Test that get_track_info returns None for missing tracks."""
        info = history_service.get_track_info("missing")
        assert info is None


class TestDuplicatePrevention:
    """Test duplicate download prevention logic."""

    def test_should_skip_download_when_enabled_and_downloaded(self, history_service: HistoryService):
        """Test that should_skip_download returns True when prevention is enabled and track exists."""
        track_id = "44444444"
        history_service.add_track_to_history(track_id=track_id)
        history_service.update_settings(preventDuplicates=True)

        assert history_service.should_skip_download(track_id) is True

    def test_should_skip_download_when_disabled_and_downloaded(self, history_service: HistoryService):
        """Test that should_skip_download returns False when prevention is disabled."""
        track_id = "55555555"
        history_service.add_track_to_history(track_id=track_id)
        history_service.update_settings(preventDuplicates=False)

        assert history_service.should_skip_download(track_id) is False

    def test_should_skip_download_when_enabled_and_not_downloaded(self, history_service: HistoryService):
        """Test that should_skip_download returns False for new tracks."""
        history_service.update_settings(preventDuplicates=True)

        assert history_service.should_skip_download("new_track") is False

    def test_prevent_duplicates_default_enabled(self, history_service: HistoryService):
        """Test that duplicate prevention is enabled by default."""
        settings = history_service.get_settings()
        assert settings["preventDuplicates"] is True


class TestSettingsManagement:
    """Test settings management functionality."""

    def test_get_settings_returns_copy(self, history_service: HistoryService):
        """Test that get_settings returns a copy, not the original."""
        settings = history_service.get_settings()
        settings["preventDuplicates"] = False

        # Original should be unchanged
        assert history_service.settings_data["preventDuplicates"] is True

    def test_update_settings_changes_value(self, history_service: HistoryService):
        """Test that update_settings changes the setting value."""
        history_service.update_settings(preventDuplicates=False)

        assert history_service.settings_data["preventDuplicates"] is False

    def test_update_settings_persists_to_file(self, history_service: HistoryService):
        """Test that settings updates are persisted to the file."""
        history_service.update_settings(preventDuplicates=False)

        with open(history_service.file_path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["settings"]["preventDuplicates"] is False

    def test_update_settings_converts_to_bool(self, history_service: HistoryService):
        """Test that update_settings converts values to boolean."""
        history_service.update_settings(preventDuplicates="true")
        assert history_service.settings_data["preventDuplicates"] is True

        history_service.update_settings(preventDuplicates=0)
        assert history_service.settings_data["preventDuplicates"] is False


class TestHistoryBySource:
    """Test source-centric history view."""

    def test_get_history_by_source_groups_correctly(self, history_service: HistoryService):
        """Test that tracks are grouped by source correctly."""
        # Add tracks from same playlist
        history_service.add_track_to_history("t1", "playlist", "pl-1", "Playlist 1")
        history_service.add_track_to_history("t2", "playlist", "pl-1", "Playlist 1")
        # Add track from different source
        history_service.add_track_to_history("t3", "album", "al-1", "Album 1")

        grouped = history_service.get_history_by_source()

        assert "playlist_pl-1" in grouped
        assert len(grouped["playlist_pl-1"]) == 2
        assert "album_al-1" in grouped
        assert len(grouped["album_al-1"]) == 1

    def test_get_history_by_source_manual_tracks(self, history_service: HistoryService):
        """Test that manual tracks are grouped separately."""
        history_service.add_track_to_history("t1", "manual", None, None)
        history_service.add_track_to_history("t2", "manual", None, None)

        grouped = history_service.get_history_by_source()

        assert "manual_manual" in grouped
        assert len(grouped["manual_manual"]) == 2


class TestStatistics:
    """Test statistics calculation."""

    def test_get_statistics_counts_total_tracks(self, history_service: HistoryService):
        """Test that statistics include total track count."""
        history_service.add_track_to_history("t1")
        history_service.add_track_to_history("t2")
        history_service.add_track_to_history("t3")

        stats = history_service.get_statistics()

        assert stats["total_tracks"] == 3

    def test_get_statistics_counts_by_source_type(self, history_service: HistoryService):
        """Test that statistics count tracks by source type."""
        history_service.add_track_to_history("t1", "playlist")
        history_service.add_track_to_history("t2", "playlist")
        history_service.add_track_to_history("t3", "album")
        history_service.add_track_to_history("t4", "mix")

        stats = history_service.get_statistics()

        assert stats["by_source_type"]["playlist"] == 2
        assert stats["by_source_type"]["album"] == 1
        assert stats["by_source_type"]["mix"] == 1

    def test_get_statistics_finds_oldest_newest(self, history_service: HistoryService):
        """Test that statistics include oldest and newest download dates."""
        history_service.add_track_to_history("t1")
        history_service.add_track_to_history("t2")

        stats = history_service.get_statistics()

        assert stats["oldest_download"] is not None
        assert stats["newest_download"] is not None

    def test_get_statistics_empty_history(self, history_service: HistoryService):
        """Test statistics with empty history."""
        stats = history_service.get_statistics()

        assert stats["total_tracks"] == 0
        assert stats["by_source_type"] == {}
        assert stats["oldest_download"] is None
        assert stats["newest_download"] is None


class TestJSONPersistence:
    """Test JSON file persistence and corruption recovery."""

    def test_corrupted_json_creates_backup(self, history_service: HistoryService):
        """Test that corrupted JSON files are backed up."""
        # Write corrupted JSON
        with open(history_service.file_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json }")

        # Force reload
        history_service._load_history()

        # Check backup was created
        backup_files = list(history_service.file_path.parent.glob("*.bak*"))
        assert len(backup_files) > 0

    def test_corrupted_json_starts_fresh(self, history_service: HistoryService):
        """Test that corrupted JSON results in fresh empty history."""
        # Add a track first
        history_service.add_track_to_history("t1")

        # Corrupt the file
        with open(history_service.file_path, "w", encoding="utf-8") as f:
            f.write("corrupted")

        # Force reload
        history_service._load_history()

        # Should have fresh empty history
        assert history_service.history_data == {}

    def test_atomic_write_on_failure(self, history_service: HistoryService):
        """Test that failed writes don't corrupt existing file."""
        from contextlib import suppress

        # Add initial data
        history_service.add_track_to_history("t1")

        # Mock a write failure
        with patch("builtins.open", side_effect=OSError("Disk full")), suppress(OSError):
            history_service.add_track_to_history("t2")

        # Original file should still be intact
        with open(history_service.file_path, encoding="utf-8") as f:
            data = json.load(f)

        assert "t1" in data["tracks"]

    def test_legacy_format_migration(self, history_service: HistoryService):
        """Test that legacy JSON format (without tracks section) is migrated."""
        # Write legacy format (tracks at root level)
        legacy_data = {
            "_schema_version": 1,
            "12345": {
                "sourceType": "playlist",
                "sourceId": "pl-1",
                "sourceName": "Test",
                "downloadDate": datetime.now(UTC).isoformat(),
            },
        }

        with open(history_service.file_path, "w", encoding="utf-8") as f:
            json.dump(legacy_data, f)

        # Force reload
        history_service._load_history()

        # Should have migrated the track
        assert "12345" in history_service.history_data


class TestImportExport:
    """Test import and export functionality."""

    def test_export_history_creates_valid_json(self, history_service: HistoryService, tmp_path: Path):
        """Test that export creates a valid JSON file."""
        history_service.add_track_to_history("t1", "playlist", "pl-1", "Test")

        export_path = tmp_path / "export.json"
        success, message = history_service.export_history(str(export_path))

        assert success is True
        assert export_path.exists()

        with open(export_path, encoding="utf-8") as f:
            data = json.load(f)

        assert "_schema_version" in data
        assert "tracks" in data
        assert "t1" in data["tracks"]

    def test_import_history_merge_mode(self, history_service: HistoryService, tmp_path: Path):
        """Test importing history in merge mode."""
        # Add existing track
        history_service.add_track_to_history("existing", "album")

        # Create import file
        import_data = {
            "tracks": {
                "imported": {
                    "sourceType": "playlist",
                    "sourceId": "pl-1",
                    "sourceName": "Imported",
                    "downloadDate": datetime.now(UTC).isoformat(),
                }
            }
        }

        import_path = tmp_path / "import.json"
        with open(import_path, "w", encoding="utf-8") as f:
            json.dump(import_data, f)

        success, message = history_service.import_history(str(import_path), merge=True)

        assert success is True
        assert "existing" in history_service.history_data
        assert "imported" in history_service.history_data

    def test_import_history_replace_mode(self, history_service: HistoryService, tmp_path: Path):
        """Test importing history in replace mode."""
        # Add existing track
        history_service.add_track_to_history("existing", "album")

        # Create import file
        import_data = {
            "tracks": {
                "imported": {
                    "sourceType": "playlist",
                    "sourceId": "pl-1",
                    "sourceName": "Imported",
                    "downloadDate": datetime.now(UTC).isoformat(),
                }
            }
        }

        import_path = tmp_path / "import.json"
        with open(import_path, "w", encoding="utf-8") as f:
            json.dump(import_data, f)

        success, message = history_service.import_history(str(import_path), merge=False)

        assert success is True
        assert "existing" not in history_service.history_data
        assert "imported" in history_service.history_data

    def test_import_invalid_json_fails(self, history_service: HistoryService, tmp_path: Path):
        """Test that importing invalid JSON fails gracefully."""
        import_path = tmp_path / "invalid.json"
        with open(import_path, "w", encoding="utf-8") as f:
            f.write("{ invalid }")

        success, message = history_service.import_history(str(import_path))

        assert success is False
        assert "Invalid JSON" in message

    def test_import_settings_from_file(self, history_service: HistoryService, tmp_path: Path):
        """Test that settings are imported along with tracks."""
        import_data = {
            "settings": {"preventDuplicates": False},
            "tracks": {"t1": {"sourceType": "manual", "downloadDate": datetime.now(UTC).isoformat()}},
        }

        import_path = tmp_path / "import.json"
        with open(import_path, "w", encoding="utf-8") as f:
            json.dump(import_data, f)

        history_service.import_history(str(import_path))

        assert history_service.settings_data["preventDuplicates"] is False


class TestClearHistory:
    """Test history clearing functionality."""

    def test_clear_history_removes_all_tracks(self, history_service: HistoryService):
        """Test that clear_history removes all tracks."""
        history_service.add_track_to_history("t1")
        history_service.add_track_to_history("t2")
        history_service.add_track_to_history("t3")

        history_service.clear_history()

        assert len(history_service.history_data) == 0

    def test_clear_history_persists_to_file(self, history_service: HistoryService):
        """Test that clearing history persists to the file."""
        history_service.add_track_to_history("t1")
        history_service.clear_history()

        with open(history_service.file_path, encoding="utf-8") as f:
            data = json.load(f)

        assert len(data["tracks"]) == 0


class TestThreadSafety:
    """Test thread safety of history operations."""

    def test_concurrent_track_additions(self, history_service: HistoryService):
        """Test that concurrent track additions are thread-safe."""
        import threading

        def add_tracks(start_id: int):
            for i in range(10):
                history_service.add_track_to_history(f"t{start_id + i}")

        threads = [threading.Thread(target=add_tracks, args=(i * 10,)) for i in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Should have 50 tracks total
        assert len(history_service.history_data) == 50

    def test_concurrent_read_write(self, history_service: HistoryService):
        """Test concurrent read and write operations."""
        import threading

        history_service.add_track_to_history("t1")

        results = []

        def reader():
            for _ in range(100):
                results.append(history_service.is_downloaded("t1"))

        def writer():
            for i in range(10):
                history_service.add_track_to_history(f"new_{i}")

        threads = [threading.Thread(target=reader), threading.Thread(target=writer)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # All reads should have succeeded
        assert all(results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
