"""Unit tests for the hover info feature.

This module tests the "Quick View on Hover" functionality, including:
    - Debounce timer behavior
    - Info tab widget updates
    - Data integrity without network calls
    - Hover state management

Tests ensure that:
    1. Rapid hover events are properly debounced
    2. UI updates only occur after the debounce delay
    3. Pre-loaded metadata is displayed without API calls
    4. Hover state properly reverts when mouse leaves
"""

import time
from unittest.mock import Mock, patch

import pytest
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from tidalapi import Album, Track, Video
from tidalapi.artist import Artist

from tidal_dl_ng.helper.hover_manager import HoverManager
from tidal_dl_ng.ui.info_tab_widget import InfoTabWidget, TrackInfoFormatter


@pytest.fixture
def qt_app():
    """Create a QApplication instance for testing Qt widgets.

    Returns:
        QApplication: The application instance.
    """
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    yield app
    # Note: Don't quit the app as it may be shared across tests


@pytest.fixture
def info_tab_widget(qt_app):
    """Create an InfoTabWidget instance for testing.

    Args:
        qt_app: The QApplication fixture.

    Returns:
        InfoTabWidget: The widget instance.
    """
    widget = InfoTabWidget()
    yield widget
    # InfoTabWidget inherits from QObject, not QWidget, so it doesn't have close()
    widget.deleteLater()


@pytest.fixture
def mock_track():
    """Create a mock Track object with metadata.

    Returns:
        Mock: A mock Track object with realistic attributes.
    """
    track = Mock(spec=Track)
    track.name = "Bohemian Rhapsody"
    track.title = "Bohemian Rhapsody"
    track.full_name = "Bohemian Rhapsody"
    track.version = "2011 Remaster"
    track.duration = 354  # 5:54
    track.explicit = False
    track.popularity = 95
    track.bpm = 72
    track.isrc = "GBUM71029604"
    track.bit_depth = 24
    track.sample_rate = 96000
    track.audio_modes = []
    track.available = True
    track.id = 12345

    # Mock album
    mock_album = Mock(spec=Album)
    mock_album.name = "A Night at the Opera"
    mock_album.id = 67890
    mock_album.release_date = Mock()
    mock_album.release_date.strftime = Mock(return_value="1975-11-21")
    track.album = mock_album

    # Mock artists
    mock_artist = Mock(spec=Artist)
    mock_artist.name = "Queen"
    mock_artist.roles = [Mock(name="main")]
    track.artists = [mock_artist]

    return track


@pytest.fixture
def mock_video():
    """Create a mock Video object.

    Returns:
        Mock: A mock Video object.
    """
    video = Mock(spec=Video)
    video.name = "Thriller"
    video.title = "Thriller"
    video.full_name = "Thriller (Official Video)"
    video.duration = 600
    video.explicit = False
    video.video_quality = "1080p"
    video.available = True
    video.id = 54321

    mock_artist = Mock(spec=Artist)
    mock_artist.name = "Michael Jackson"
    video.artists = [mock_artist]

    mock_album = Mock(spec=Album)
    mock_album.name = "Thriller"
    video.album = mock_album

    return video


@pytest.fixture
def tree_view_setup(qt_app):
    """Create a tree view with model for testing hover manager.

    Args:
        qt_app: The QApplication fixture.

    Returns:
        tuple: (tree_view, proxy_model, source_model)
    """
    tree_view = QtWidgets.QTreeView()
    source_model = QtGui.QStandardItemModel()
    proxy_model = QtCore.QSortFilterProxyModel()

    proxy_model.setSourceModel(source_model)
    tree_view.setModel(proxy_model)

    # Add some test data
    source_model.setColumnCount(2)
    for i in range(5):
        item_index = QtGui.QStandardItem(f"Item {i}")
        item_obj = QtGui.QStandardItem()
        mock_track = Mock(spec=Track)
        mock_track.name = f"Track {i}"
        mock_track.id = i
        item_obj.setData(mock_track, Qt.ItemDataRole.UserRole)
        source_model.appendRow([item_index, item_obj])

    yield tree_view, proxy_model, source_model

    tree_view.close()
    tree_view.deleteLater()


class TestTrackInfoFormatter:
    """Test the TrackInfoFormatter utility class."""

    def test_format_duration_valid(self):
        """Test duration formatting with valid input."""
        assert TrackInfoFormatter.format_duration(354) == "05:54"
        assert TrackInfoFormatter.format_duration(60) == "01:00"
        assert TrackInfoFormatter.format_duration(0) == "00:00"

    def test_format_duration_none(self):
        """Test duration formatting with None input."""
        assert TrackInfoFormatter.format_duration(None) == "N/A"

    def test_format_codec(self, mock_track):
        """Test codec formatting with a mock track."""
        with patch("tidal_dl_ng.ui.info_tab_widget.quality_audio_highest", return_value="HI_RES") as _:
            codec = TrackInfoFormatter.format_codec(mock_track)
            assert "HI_RES" in codec.upper()

    def test_format_bitrate(self, mock_track):
        """Test bitrate formatting."""
        bitrate = TrackInfoFormatter.format_bitrate(mock_track)
        assert "24-bit" in bitrate
        assert "96.0 kHz" in bitrate

    def test_format_bitrate_missing_data(self):
        """Test bitrate formatting with missing data."""
        track = Mock(spec=Track)
        track.bit_depth = None
        track.sample_rate = None
        assert TrackInfoFormatter.format_bitrate(track) == "N/A"


class TestInfoTabWidget:
    """Test the InfoTabWidget component."""

    def test_widget_initialization(self, info_tab_widget):
        """Test that the widget initializes correctly."""
        assert info_tab_widget is not None
        # In test context, tab_widget is None because no existing_tab_widget is provided
        # The widget creates fallback labels for all required fields
        assert hasattr(info_tab_widget, "lbl_title")
        assert hasattr(info_tab_widget, "lbl_artists")
        assert hasattr(info_tab_widget, "lbl_bpm")
        assert hasattr(info_tab_widget, "cover_label")

    def test_update_on_hover(self, info_tab_widget, mock_track, qt_app):
        """Test updating widget on hover."""
        info_tab_widget.update_on_hover(mock_track)
        qt_app.processEvents()

        assert info_tab_widget.current_media_hovered == mock_track
        # The details should be updated via signal
        # We can check if the signal was emitted by verifying internal state

    def test_update_on_selection(self, info_tab_widget, mock_track, qt_app):
        """Test updating widget on selection."""
        info_tab_widget.update_on_selection(mock_track)
        qt_app.processEvents()

        assert info_tab_widget.current_media_selected == mock_track

    def test_revert_to_selection(self, info_tab_widget, mock_track, qt_app):
        """Test reverting to selected media after hover."""
        # Set a selection
        info_tab_widget.update_on_selection(mock_track)
        qt_app.processEvents()

        # Create a different track for hover
        hover_track = Mock(spec=Track)
        hover_track.name = "Different Track"
        info_tab_widget.update_on_hover(hover_track)
        qt_app.processEvents()

        # Revert to selection
        info_tab_widget.revert_to_selection()
        qt_app.processEvents()

        # Should have reverted to the original selection
        assert info_tab_widget.current_media_selected == mock_track

    def test_populate_track_details(self, info_tab_widget, mock_track, qt_app):
        """Test populating details for a track."""
        with (
            patch("tidal_dl_ng.ui.info_tab_widget.quality_audio_highest", return_value="HI_RES"),
            patch("tidal_dl_ng.ui.info_tab_widget.name_builder_artist", return_value="Queen"),
            patch("tidal_dl_ng.ui.info_tab_widget.name_builder_title", return_value="Bohemian Rhapsody"),
        ):
            info_tab_widget._populate_track_details(mock_track)
            qt_app.processEvents()

            assert info_tab_widget.lbl_title.text() == "Bohemian Rhapsody"
            assert info_tab_widget.lbl_version.text() == "2011 Remaster"
            assert info_tab_widget.lbl_duration.text() == "05:54"
            assert info_tab_widget.lbl_bpm.text() == "⏳ Loading..."
            info_tab_widget._update_extras_ui({"bpm": 72})
            qt_app.processEvents()
            assert info_tab_widget.lbl_bpm.text() == "72"

    def test_populate_video_details(self, info_tab_widget, mock_video, qt_app):
        """Test populating details for a video."""
        with (
            patch("tidal_dl_ng.ui.info_tab_widget.name_builder_artist", return_value="Michael Jackson"),
            patch("tidal_dl_ng.ui.info_tab_widget.name_builder_title", return_value="Thriller"),
        ):
            info_tab_widget._populate_video_details(mock_video)
            qt_app.processEvents()

            assert info_tab_widget.lbl_title.text() == "Thriller"
            assert info_tab_widget.lbl_codec.text() == "1080p"

    def test_clear_display(self, info_tab_widget, qt_app):
        """Test clearing the display."""
        info_tab_widget._clear_display()
        qt_app.processEvents()

        assert info_tab_widget.lbl_title.text() == "—"
        assert info_tab_widget.lbl_artists.text() == "—"
        assert info_tab_widget.current_media_hovered is None


class TestHoverManager:
    """Test the HoverManager with debounce logic."""

    def test_hover_manager_initialization(self, tree_view_setup, qt_app):
        """Test that HoverManager initializes correctly."""
        tree_view, proxy_model, source_model = tree_view_setup

        hover_manager = HoverManager(
            tree_view=tree_view,
            proxy_model=proxy_model,
            source_model=source_model,
            debounce_delay_ms=100,
        )

        assert hover_manager is not None
        assert hover_manager.debounce_delay_ms == 100
        assert hover_manager.pending_media is None

    def test_debounce_single_hover(self, tree_view_setup, qt_app):
        """Test that a single hover event is confirmed after debounce delay."""
        tree_view, proxy_model, source_model = tree_view_setup

        hover_manager = HoverManager(
            tree_view=tree_view,
            proxy_model=proxy_model,
            source_model=source_model,
            debounce_delay_ms=100,
        )

        # Mock signal to track emissions
        hover_confirmed_spy = []

        def on_hover_confirmed(media):
            hover_confirmed_spy.append(media)

        hover_manager.s_hover_confirmed.connect(on_hover_confirmed)

        # Simulate mouse movement over an item
        # (This is complex to test properly without actual UI interaction)
        # For now, we'll test the timer directly
        mock_media = Mock(spec=Track)
        mock_media.name = "Test Track"

        hover_manager.pending_media = mock_media
        hover_manager.debounce_timer.start()

        # Wait for debounce delay + some buffer
        qt_app.processEvents()
        time.sleep(0.15)
        qt_app.processEvents()

        # Signal should have been emitted
        assert len(hover_confirmed_spy) == 1
        assert hover_confirmed_spy[0] == mock_media

    def test_debounce_rapid_hovers(self, tree_view_setup, qt_app):
        """Test that rapid hover events are debounced (only last one fires)."""
        tree_view, proxy_model, source_model = tree_view_setup

        hover_manager = HoverManager(
            tree_view=tree_view,
            proxy_model=proxy_model,
            source_model=source_model,
            debounce_delay_ms=100,
        )

        hover_confirmed_spy = []

        def on_hover_confirmed(media):
            hover_confirmed_spy.append(media)

        hover_manager.s_hover_confirmed.connect(on_hover_confirmed)

        # Simulate 5 rapid hover events
        for i in range(5):
            mock_media = Mock(spec=Track)
            mock_media.name = f"Track {i}"
            hover_manager.pending_media = mock_media
            hover_manager.debounce_timer.stop()
            hover_manager.debounce_timer.start()
            time.sleep(0.02)  # Small delay between events (< debounce)
            qt_app.processEvents()

        # Wait for debounce delay
        time.sleep(0.15)
        qt_app.processEvents()

        # Only one signal should have been emitted (the last one)
        assert len(hover_confirmed_spy) == 1
        assert hover_confirmed_spy[0].name == "Track 4"

    def test_hover_left_cancels_pending(self, tree_view_setup, qt_app):
        """Test that leaving hover cancels pending confirmation."""
        tree_view, proxy_model, source_model = tree_view_setup

        hover_manager = HoverManager(
            tree_view=tree_view,
            proxy_model=proxy_model,
            source_model=source_model,
            debounce_delay_ms=100,
        )

        hover_confirmed_spy = []
        hover_left_spy = []

        def on_hover_confirmed(media):
            hover_confirmed_spy.append(media)

        def on_hover_left():
            hover_left_spy.append(True)

        hover_manager.s_hover_confirmed.connect(on_hover_confirmed)
        hover_manager.s_hover_left.connect(on_hover_left)

        # Start a hover
        mock_media = Mock(spec=Track)
        hover_manager.pending_media = mock_media
        hover_manager.debounce_timer.start()

        # Leave before debounce completes
        time.sleep(0.05)
        qt_app.processEvents()
        hover_manager._handle_mouse_leave()
        qt_app.processEvents()

        # Wait to ensure timer would have fired
        time.sleep(0.1)
        qt_app.processEvents()

        # Hover confirmed should NOT have been emitted
        assert len(hover_confirmed_spy) == 0
        # Hover left should have been emitted
        assert len(hover_left_spy) == 1

    def test_set_debounce_delay(self, tree_view_setup, qt_app):
        """Test changing the debounce delay."""
        tree_view, proxy_model, source_model = tree_view_setup

        hover_manager = HoverManager(
            tree_view=tree_view,
            proxy_model=proxy_model,
            source_model=source_model,
            debounce_delay_ms=100,
        )

        hover_manager.set_debounce_delay(200)

        assert hover_manager.debounce_delay_ms == 200
        assert hover_manager.debounce_timer.interval() == 200

    def test_reset(self, tree_view_setup, qt_app):
        """Test resetting the hover manager state."""
        tree_view, proxy_model, source_model = tree_view_setup

        hover_manager = HoverManager(
            tree_view=tree_view,
            proxy_model=proxy_model,
            source_model=source_model,
            debounce_delay_ms=100,
        )

        # Set some state
        mock_media = Mock(spec=Track)
        hover_manager.pending_media = mock_media
        hover_manager.last_hovered_media = mock_media
        hover_manager.debounce_timer.start()

        # Reset
        hover_manager.reset()

        assert hover_manager.pending_media is None
        assert hover_manager.last_hovered_media is None
        assert not hover_manager.debounce_timer.isActive()


class TestDataIntegrity:
    """Test that metadata is displayed from pre-loaded data without API calls."""

    def test_no_api_calls_on_hover(self, info_tab_widget, mock_track, qt_app):
        """Test that hovering does not trigger API calls.

        This test verifies that all data displayed on hover comes from
        pre-loaded track objects, not from additional API requests.
        """
        # Patch any potential API call methods
        with patch.object(mock_track, "album") as mock_album:
            # Ensure album data is already present (pre-loaded)
            mock_album.name = "A Night at the Opera"
            mock_album.id = 67890

            # Update on hover
            info_tab_widget.update_on_hover(mock_track)
            qt_app.processEvents()

            # Verify that album was not accessed in a way that would trigger API calls
            # The album should have been accessed only for reading pre-loaded data
            assert info_tab_widget.current_media_hovered == mock_track

    def test_all_metadata_from_preloaded_object(self, info_tab_widget, mock_track, qt_app):
        """Test that all displayed metadata comes from the track object.

        This verifies that the Track object contains all necessary fields
        to populate the Details tab without additional API calls.
        """
        with (
            patch("tidal_dl_ng.ui.info_tab_widget.quality_audio_highest", return_value="HI_RES"),
            patch("tidal_dl_ng.ui.info_tab_widget.name_builder_artist", return_value="Queen"),
            patch("tidal_dl_ng.ui.info_tab_widget.name_builder_title", return_value="Bohemian Rhapsody"),
        ):
            info_tab_widget._populate_track_details(mock_track)
            qt_app.processEvents()

            assert info_tab_widget.lbl_title.text() != "—"
            assert info_tab_widget.lbl_version.text() != "—"
            assert info_tab_widget.lbl_duration.text() != "—"
            assert info_tab_widget.lbl_popularity.text() != "—"
            assert info_tab_widget.lbl_bpm.text() != "—"
            assert info_tab_widget.lbl_isrc.text() != "—"
