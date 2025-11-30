"""Tests for the Delimiters category in settings dialog."""

from unittest.mock import Mock, patch

import pytest
from PySide6 import QtWidgets

from tidal_dl_ng.dialog import DialogPreferences
from tidal_dl_ng.ui.dialog_settings import Ui_DialogSettings


@pytest.fixture
def qapp():
    """Create QApplication instance for tests."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    yield app


class TestDelimitersPage:
    """Test the Delimiters page specifically."""

    def test_delimiters_page_exists(self, qapp):
        """Test that the Delimiters page exists."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        assert hasattr(ui, "page_delimiters")
        assert ui.page_delimiters is not None

    def test_delimiters_page_is_fifth(self, qapp):
        """Test that the Delimiters page is at index 4."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        assert ui.sw_categories.widget(4) == ui.page_delimiters

    def test_delimiters_groupbox_exists(self, qapp):
        """Test that the Delimiters GroupBox exists."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        assert hasattr(ui, "gb_delimiters")
        assert ui.gb_delimiters is not None
        assert isinstance(ui.gb_delimiters, QtWidgets.QGroupBox)

    def test_delimiters_page_has_four_line_edits(self, qapp):
        """Test that the Delimiters page has 4 line edits."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        line_edits = ui.page_delimiters.findChildren(QtWidgets.QLineEdit)
        assert len(line_edits) == 4, "Delimiters page should have 4 line edits"

    def test_all_delimiter_line_edits_accessible(self, qapp):
        """Test that all delimiter line edits are accessible."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        line_edit_names = [
            "le_metadata_delimiter_artist",
            "le_metadata_delimiter_album_artist",
            "le_filename_delimiter_artist",
            "le_filename_delimiter_album_artist",
        ]

        for name in line_edit_names:
            line_edit = getattr(ui, name, None)
            assert line_edit is not None, f"LineEdit {name} not found"
            assert isinstance(line_edit, QtWidgets.QLineEdit)

    def test_delimiter_line_edits_have_max_width(self, qapp):
        """Test that delimiter line edits have a maximum width set."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        line_edit_names = [
            "le_metadata_delimiter_artist",
            "le_metadata_delimiter_album_artist",
            "le_filename_delimiter_artist",
            "le_filename_delimiter_album_artist",
        ]

        for name in line_edit_names:
            line_edit = getattr(ui, name)
            # Should have max width of 100px
            assert line_edit.maximumWidth() == 100, f"{name} should have max width of 100px"

    def test_delimiter_labels_exist(self, qapp):
        """Test that labels and icon labels exist for each delimiter."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        label_names = [
            ("l_metadata_delimiter_artist", "l_icon_metadata_delimiter_artist"),
            ("l_metadata_delimiter_album_artist", "l_icon_metadata_delimiter_album_artist"),
            ("l_filename_delimiter_artist", "l_icon_filename_delimiter_artist"),
            ("l_filename_delimiter_album_artist", "l_icon_filename_delimiter_album_artist"),
        ]

        for label_name, icon_label_name in label_names:
            label = getattr(ui, label_name, None)
            icon_label = getattr(ui, icon_label_name, None)

            assert label is not None, f"Label {label_name} not found"
            assert icon_label is not None, f"Icon label {icon_label_name} not found"
            assert isinstance(label, QtWidgets.QLabel)
            assert isinstance(icon_label, QtWidgets.QLabel)


class TestDelimitersIntegration:
    """Test Delimiters integration with DialogPreferences."""

    @pytest.fixture
    def mock_settings(self):
        """Create a mock Settings object with delimiter attributes."""
        settings = Mock()
        settings.data = Mock()

        # Boolean flags
        for attr in [
            "lyrics_embed",
            "lyrics_file",
            "use_primary_album_artist",
            "video_download",
            "download_dolby_atmos",
            "download_delay",
            "video_convert_mp4",
            "extract_flac",
            "metadata_cover_embed",
            "mark_explicit",
            "cover_album_file",
            "skip_existing",
            "symlink_to_track",
            "playlist_create",
        ]:
            setattr(settings.data, attr, False)

        # Paths
        for attr in [
            "download_base_path",
            "format_album",
            "format_playlist",
            "format_mix",
            "format_track",
            "format_video",
            "path_binary_ffmpeg",
        ]:
            setattr(settings.data, attr, f"/test/{attr}")

        # Delimiters
        settings.data.metadata_delimiter_artist = ", "
        settings.data.metadata_delimiter_album_artist = ", "
        settings.data.filename_delimiter_artist = ", "
        settings.data.filename_delimiter_album_artist = ", "

        # Numbers
        settings.data.album_track_num_pad_min = 2
        settings.data.downloads_concurrent_max = 3

        # Enums
        settings.data.quality_audio = Mock()
        settings.data.quality_video = Mock()
        settings.data.metadata_cover_dimension = Mock()

        return settings

    @patch.object(DialogPreferences, "exec")
    def test_delimiters_category_added_to_list(self, mock_exec, mock_settings, qapp):
        """Test that Delimiters category is added to the list."""
        from PySide6.QtCore import Signal as QtSignal

        settings_save = QtSignal()

        with patch.object(DialogPreferences, "gui_populate"):
            dialog = DialogPreferences(mock_settings, settings_save)

            # Should have 5 categories now
            assert dialog.ui.lw_categories.count() == 5
            assert dialog.ui.lw_categories.item(4).text() == "Delimiters"

    @patch.object(DialogPreferences, "exec")
    def test_delimiter_line_edits_in_parameters(self, mock_exec, mock_settings, qapp):
        """Test that delimiter line edits are in parameters_line_edit."""
        from PySide6.QtCore import Signal as QtSignal

        settings_save = QtSignal()

        with patch.object(DialogPreferences, "gui_populate"):
            dialog = DialogPreferences(mock_settings, settings_save)

            # Check that all 4 delimiters are in the list
            assert "metadata_delimiter_artist" in dialog.parameters_line_edit
            assert "metadata_delimiter_album_artist" in dialog.parameters_line_edit
            assert "filename_delimiter_artist" in dialog.parameters_line_edit
            assert "filename_delimiter_album_artist" in dialog.parameters_line_edit

    @patch.object(DialogPreferences, "exec")
    def test_navigate_to_delimiters_page(self, mock_exec, mock_settings, qapp):
        """Test navigation to Delimiters page."""
        from PySide6.QtCore import Signal as QtSignal

        settings_save = QtSignal()

        with patch.object(DialogPreferences, "gui_populate"):
            dialog = DialogPreferences(mock_settings, settings_save)

            # Navigate to Delimiters (index 4)
            dialog.ui.lw_categories.setCurrentRow(4)
            assert dialog.ui.sw_categories.currentIndex() == 4
            assert dialog.ui.sw_categories.currentWidget() == dialog.ui.page_delimiters


class TestDelimitersStructure:
    """Test the structural integrity of the Delimiters page."""

    def test_stacked_widget_has_five_pages(self, qapp):
        """Test that the stacked widget now contains 5 pages."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        assert ui.sw_categories.count() == 5, "Should have 5 pages including Delimiters"

    def test_delimiters_page_has_layout(self, qapp):
        """Test that Delimiters page has a proper layout."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        assert ui.page_delimiters.layout() is not None
        assert isinstance(ui.page_delimiters.layout(), QtWidgets.QVBoxLayout)

    def test_delimiters_page_has_spacer(self, qapp):
        """Test that Delimiters page has a vertical spacer."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        # Check that there's a spacer in the layout
        layout = ui.page_delimiters.layout()
        spacer_found = False
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.spacerItem():
                spacer_found = True
                break

        assert spacer_found, "Delimiters page should have a vertical spacer"
