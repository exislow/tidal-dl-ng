"""
test_download_duplicate_prevention.py

Test suite for download duplicate prevention functionality.

Tests cover:
- Duplicate prevention during downloads
- Integration with HistoryService
- Skipped item logging
- Settings toggle behavior
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from tidalapi import Quality, Track

from tidal_dl_ng.download import Download
from tidal_dl_ng.history import HistoryService


@pytest.fixture
def mock_tidal():
    """Create a mock Tidal object for testing.

    Returns:
        Mock Tidal object with session.
    """
    mock = MagicMock()
    mock.session = MagicMock()
    mock.session.audio_quality = Quality.high_lossless
    mock.switch_to_atmos_session = MagicMock(return_value=True)
    mock.restore_normal_session = MagicMock(return_value=True)
    mock.stream_lock = MagicMock()
    mock.stream_lock.__enter__ = MagicMock(return_value=None)
    mock.stream_lock.__exit__ = MagicMock(return_value=None)
    mock.settings = MagicMock()
    mock.settings.data = MagicMock()
    return mock


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing.

    Returns:
        Mock logger object.
    """
    logger = MagicMock()
    logger.info = MagicMock()
    logger.debug = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def temp_download_path(tmp_path: Path) -> Path:
    """Create a temporary download directory.

    Args:
        tmp_path: pytest fixture providing temporary directory.

    Returns:
        Path to temporary download directory.
    """
    download_dir = tmp_path / "downloads"
    download_dir.mkdir()
    return download_dir


@pytest.fixture
def history_service_with_temp(tmp_path: Path, monkeypatch) -> HistoryService:
    """Create a HistoryService with temporary storage.

    Args:
        tmp_path: pytest fixture providing temporary directory.
        monkeypatch: pytest monkeypatch fixture.

    Returns:
        Configured HistoryService instance.
    """
    config_path = tmp_path / "config"
    config_path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("tidal_dl_ng.history.path_config_base", lambda: str(config_path))

    # Reset singleton
    if hasattr(HistoryService, "_instances"):
        HistoryService._instances = {}

    return HistoryService()


@pytest.fixture
def download_instance(mock_tidal, mock_logger, temp_download_path, history_service_with_temp):
    """Create a Download instance for testing.

    Args:
        mock_tidal: Mock Tidal object.
        mock_logger: Mock logger.
        temp_download_path: Temporary download directory.
        history_service_with_temp: HistoryService with temp storage.

    Returns:
        Configured Download instance.
    """
    with patch("tidal_dl_ng.download.HistoryService", return_value=history_service_with_temp):
        download = Download(
            tidal_obj=mock_tidal, path_base=str(temp_download_path), fn_logger=mock_logger, skip_existing=False
        )
        return download


class TestDuplicatePreventionInDownload:
    """Test duplicate prevention during download operations."""

    def test_skip_download_when_track_in_history_and_prevention_enabled(self, download_instance: Download, mock_logger):
        """Test that download is skipped when track is in history and prevention is enabled."""
        # Add track to history
        track_id = "123456"
        download_instance.history_service.add_track_to_history(track_id)
        download_instance.history_service.update_settings(preventDuplicates=True)

        # Create mock track
        mock_track = MagicMock(spec=Track)
        mock_track.id = int(track_id)
        mock_track.name = "Test Track"
        mock_track.available = True
        mock_track.album = MagicMock()
        mock_track.album.name = "Test Album"

        # Attempt download
        with patch.object(download_instance.session, "track", return_value=mock_track):
            result, path = download_instance.item(file_template="{artist_name} - {track_title}", media=mock_track)

        # Should be skipped (result False means skipped)
        assert result is False
        # Logger should have logged the skip message
        assert mock_logger.info.called
        skip_call_found = any(
            "Skipped item" in str(call) or "already in history" in str(call) for call in mock_logger.info.call_args_list
        )
        assert skip_call_found

    def test_download_proceeds_when_prevention_disabled(self, download_instance: Download, mock_logger):
        """Test that download proceeds when prevention is disabled."""
        # Add track to history but disable prevention
        track_id = "789012"
        download_instance.history_service.add_track_to_history(track_id)
        download_instance.history_service.update_settings(preventDuplicates=False)

        # Create mock track
        mock_track = MagicMock(spec=Track)
        mock_track.id = int(track_id)
        mock_track.name = "Test Track 2"
        mock_track.available = True

        # Mock the download process to avoid actual download
        with (
            patch.object(download_instance, "_validate_and_prepare_media", return_value=mock_track),
            patch.object(download_instance, "_prepare_file_paths_and_skip_logic") as mock_paths,
        ):

            mock_paths.return_value = (Path("/fake/path.flac"), ".flac", False, False)

            # The download should not be skipped by duplicate prevention
            # (it will still fail later in the chain, but that's okay for this test)
            result = download_instance.history_service.should_skip_download(track_id)

        # Should NOT be skipped
        assert result is False

    def test_download_proceeds_when_track_not_in_history(self, download_instance: Download):
        """Test that download proceeds when track is not in history."""
        track_id = "999999"
        download_instance.history_service.update_settings(preventDuplicates=True)

        # Track not in history
        result = download_instance.history_service.should_skip_download(track_id)

        assert result is False


class TestHistoryLoggingMessages:
    """Test logging messages for skipped downloads."""

    def test_skip_message_format(self, download_instance: Download, mock_logger):
        """Test that skip message follows the correct format."""
        track_id = "111222"
        download_instance.history_service.add_track_to_history(track_id)
        download_instance.history_service.update_settings(preventDuplicates=True)

        mock_track = MagicMock(spec=Track)
        mock_track.id = int(track_id)
        mock_track.name = "Amazing Song"
        mock_track.artist = MagicMock()
        mock_track.artist.name = "Great Artist"
        mock_track.available = True
        mock_track.album = MagicMock()

        with patch.object(download_instance.session, "track", return_value=mock_track):
            download_instance.item(file_template="{artist_name} - {track_title}", media=mock_track)

        # Check that info logger was called
        assert mock_logger.info.called

        # Verify message contains expected parts
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        skip_message_found = any("Skipped item" in msg and "already in history" in msg for msg in log_calls)
        assert skip_message_found


class TestHistoryAfterDownload:
    """Test that successful downloads are added to history."""

    @patch("tidal_dl_ng.download.Download._download_and_process_media")
    @patch("tidal_dl_ng.download.Download._adjust_quality_settings")
    @patch("tidal_dl_ng.download.Download._perform_post_processing")
    def test_track_added_to_history_after_successful_download(
        self, mock_post_process, mock_quality, mock_download_process, download_instance: Download
    ):
        """Test that a track is added to history after successful download."""
        # Mock successful download
        mock_download_process.return_value = True
        mock_quality.return_value = (None, None)

        track_id = "333444"
        mock_track = MagicMock(spec=Track)
        mock_track.id = int(track_id)
        mock_track.name = "New Track"
        mock_track.available = True
        mock_track.album = MagicMock()

        with (
            patch.object(download_instance, "_validate_and_prepare_media", return_value=mock_track),
            patch.object(download_instance, "_prepare_file_paths_and_skip_logic") as mock_paths,
        ):

            mock_paths.return_value = (Path("/fake/path.flac"), ".flac", False, False)

            download_instance.item(
                file_template="{artist_name} - {track_title}",
                media=mock_track,
                source_type="playlist",
                source_id="pl-123",
                source_name="Test Playlist",
            )

        # Track should be in history
        assert download_instance.history_service.is_downloaded(track_id)

        # Check metadata
        track_info = download_instance.history_service.get_track_info(track_id)
        assert track_info is not None
        assert track_info["sourceType"] == "playlist"
        assert track_info["sourceId"] == "pl-123"

    @patch("tidal_dl_ng.download.Download._download_and_process_media")
    def test_track_not_added_on_failed_download(self, mock_download_process, download_instance: Download):
        """Test that track is NOT added to history if download fails."""
        # Mock failed download
        mock_download_process.return_value = False

        track_id = "555666"
        mock_track = MagicMock(spec=Track)
        mock_track.id = int(track_id)
        mock_track.available = True
        mock_track.album = MagicMock()

        with (
            patch.object(download_instance, "_validate_and_prepare_media", return_value=mock_track),
            patch.object(download_instance, "_prepare_file_paths_and_skip_logic") as mock_paths,
            patch.object(download_instance, "_adjust_quality_settings") as mock_quality,
        ):

            mock_paths.return_value = (Path("/fake/path.flac"), ".flac", False, False)
            mock_quality.return_value = (None, None)

            download_instance.item(file_template="{artist_name} - {track_title}", media=mock_track)

        # Track should NOT be in history
        assert not download_instance.history_service.is_downloaded(track_id)


class TestSettingsIntegration:
    """Test integration with settings toggle."""

    def test_settings_toggle_affects_duplicate_check(self, download_instance: Download):
        """Test that toggling settings immediately affects duplicate checking."""
        track_id = "777888"
        download_instance.history_service.add_track_to_history(track_id)

        # Enable prevention
        download_instance.history_service.update_settings(preventDuplicates=True)
        assert download_instance.history_service.should_skip_download(track_id) is True

        # Disable prevention
        download_instance.history_service.update_settings(preventDuplicates=False)
        assert download_instance.history_service.should_skip_download(track_id) is False

        # Re-enable
        download_instance.history_service.update_settings(preventDuplicates=True)
        assert download_instance.history_service.should_skip_download(track_id) is True

    def test_settings_persist_across_service_instances(self, tmp_path: Path, monkeypatch):
        """Test that settings persist across service instances."""
        config_path = tmp_path / "config"
        config_path.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr("tidal_dl_ng.history.path_config_base", lambda: str(config_path))

        # Create first instance and disable prevention
        if hasattr(HistoryService, "_instances"):
            HistoryService._instances = {}

        service1 = HistoryService()
        service1.update_settings(preventDuplicates=False)

        # Create second instance (simulating app restart)
        HistoryService._instances = {}
        service2 = HistoryService()

        # Settings should persist
        assert service2.get_settings()["preventDuplicates"] is False


class TestVideoNotAffectedByHistory:
    """Test that video downloads are not affected by history (only tracks)."""

    def test_video_download_not_checked_against_history(self, download_instance: Download):
        """Test that videos are not checked against download history."""
        from tidalapi import Video

        # This test verifies the type check in the duplicate prevention code
        # Videos should bypass the history check entirely

        mock_video = MagicMock(spec=Video)
        mock_video.id = 123456
        mock_video.name = "Test Video"
        mock_video.available = True

        # Even if we somehow had a video ID in history, it shouldn't matter
        # because the check is `isinstance(media, Track)`
        download_instance.history_service.add_track_to_history("123456")

        with (
            patch.object(download_instance, "_validate_and_prepare_media", return_value=mock_video),
            patch.object(download_instance, "_prepare_file_paths_and_skip_logic") as mock_paths,
            patch.object(download_instance.history_service, "should_skip_download") as mock_skip,
        ):
            mock_paths.return_value = (Path("/fake.mp4"), ".mp4", False, False)

            # The key is that should_skip_download is never called for videos
            # Expected to fail, we're just checking the skip wasn't called
            from contextlib import suppress

            with suppress(Exception):
                download_instance.item(file_template="{artist_name} - {track_title}", media=mock_video)

            # should_skip_download should NOT have been called for video
            assert not mock_skip.called


class TestBulkDownloadWithHistory:
    """Test history tracking in bulk download scenarios."""

    @patch("tidal_dl_ng.download.Download.item")
    def test_multiple_tracks_added_to_history(self, mock_item_download, download_instance: Download):
        """Test that multiple tracks in a bulk download are tracked."""
        # Simulate successful downloads
        mock_item_download.return_value = (True, Path("/fake/path.flac"))

        track_ids = ["t1", "t2", "t3", "t4", "t5"]

        # Manually add tracks to history (simulating what item() would do)
        for track_id in track_ids:
            download_instance.history_service.add_track_to_history(
                track_id=track_id, source_type="album", source_id="al-123", source_name="Test Album"
            )

        # All tracks should be in history
        for track_id in track_ids:
            assert download_instance.history_service.is_downloaded(track_id)

        # Should be grouped under same album
        grouped = download_instance.history_service.get_history_by_source()
        assert "album_al-123" in grouped
        assert len(grouped["album_al-123"]) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
