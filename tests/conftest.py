from unittest.mock import Mock

import pytest
from PySide6 import QtCore, QtGui, QtWidgets
from tidalapi import Album, Track, Video
from tidalapi.artist import Artist


@pytest.fixture
def qt_app():
    """Create a QApplication instance for testing Qt widgets."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    yield app
    # Note: don't quit the app as it may be shared across tests


@pytest.fixture
def info_tab_widget(qt_app):
    """Create an InfoTabWidget instance for testing."""
    from tidal_dl_ng.ui.info_tab_widget import InfoTabWidget

    widget = InfoTabWidget()
    yield widget
    # InfoTabWidget inherits from QObject, not QWidget, so it doesn't have close()
    widget.deleteLater()


@pytest.fixture
def mock_track():
    """Create a mock Track object with metadata."""
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
    track.media_metadata_tags = []
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
    """Create a mock Video object."""
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
    """Create a tree view with model for testing hover manager."""
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
        item_obj.setData(mock_track, QtCore.Qt.ItemDataRole.UserRole)
        source_model.appendRow([item_index, item_obj])

    yield tree_view, proxy_model, source_model

    tree_view.close()
    tree_view.deleteLater()
