"""Tests for the refactored settings dialog UI."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PySide6 import QtCore, QtWidgets

from tidal_dl_ng.dialog import DialogPreferences
from tidal_dl_ng.ui.dialog_settings import Ui_DialogSettings


@pytest.fixture
def qapp():
    """Create QApplication instance for tests."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    yield app
    # Cleanup is handled by pytest-qt if available, otherwise by QApplication


class TestUiDialogSettings:
    """Test the generated UI class."""

    def test_ui_setupui_creates_all_widgets(self, qapp):
        """Test that setupUi creates all expected widgets."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        # Check main structural widgets
        assert hasattr(ui, "lw_categories")
        assert hasattr(ui, "sw_categories")
        assert hasattr(ui, "bb_dialog")

        # Check pages exist
        assert hasattr(ui, "page_flags")
        assert hasattr(ui, "page_quality")
        assert hasattr(ui, "page_numbers")
        assert hasattr(ui, "page_paths")

    def test_ui_list_widget_properties(self, qapp):
        """Test that the categories list widget has correct properties."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        assert ui.lw_categories is not None
        assert isinstance(ui.lw_categories, QtWidgets.QListWidget)
        assert ui.lw_categories.minimumWidth() == 150
        assert ui.lw_categories.maximumWidth() == 200

    def test_ui_stacked_widget_has_all_pages(self, qapp):
        """Test that the stacked widget contains all 4 pages."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        assert ui.sw_categories is not None
        assert isinstance(ui.sw_categories, QtWidgets.QStackedWidget)
        assert ui.sw_categories.count() == 4

    def test_ui_flags_page_widgets(self, qapp):
        """Test that the Flags page contains all expected checkboxes."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        # Test flags group box exists
        assert hasattr(ui, "gb_flags")
        assert ui.gb_flags is not None

        # Test all checkboxes exist
        checkboxes = [
            "cb_video_download",
            "cb_video_convert_mp4",
            "cb_lyrics_embed",
            "cb_lyrics_file",
            "cb_download_delay",
            "cb_extract_flac",
            "cb_metadata_cover_embed",
            "cb_cover_album_file",
            "cb_skip_existing",
            "cb_symlink_to_track",
            "cb_playlist_create",
            "cb_mark_explicit",
            "cb_use_primary_album_artist",
            "cb_download_dolby_atmos",
        ]

        for cb_name in checkboxes:
            assert hasattr(ui, cb_name), f"Missing checkbox: {cb_name}"
            checkbox = getattr(ui, cb_name)
            assert isinstance(checkbox, QtWidgets.QCheckBox)

    def test_ui_quality_page_widgets(self, qapp):
        """Test that the Quality page contains all expected combo boxes."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        # Test choices group box exists
        assert hasattr(ui, "gb_choices")
        assert ui.gb_choices is not None

        # Test all combo boxes exist
        combos = [
            "c_quality_audio",
            "c_quality_video",
            "c_metadata_cover_dimension",
        ]

        for combo_name in combos:
            assert hasattr(ui, combo_name), f"Missing combo box: {combo_name}"
            combo = getattr(ui, combo_name)
            assert isinstance(combo, QtWidgets.QComboBox)

    def test_ui_numbers_page_widgets(self, qapp):
        """Test that the Numbers page contains all expected spin boxes."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        # Test numbers group box exists
        assert hasattr(ui, "gb_numbers")
        assert ui.gb_numbers is not None

        # Test all spin boxes exist
        spinboxes = [
            "sb_album_track_num_pad_min",
            "sb_downloads_concurrent_max",
        ]

        for sb_name in spinboxes:
            assert hasattr(ui, sb_name), f"Missing spin box: {sb_name}"
            spinbox = getattr(ui, sb_name)
            assert isinstance(spinbox, QtWidgets.QSpinBox)

    def test_ui_paths_page_widgets(self, qapp):
        """Test that the Paths page contains all expected line edits and buttons."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        # Test path group box exists
        assert hasattr(ui, "gb_path")
        assert ui.gb_path is not None

        # Test all line edits exist
        line_edits = [
            "le_download_base_path",
            "le_format_track",
            "le_format_video",
            "le_format_album",
            "le_format_playlist",
            "le_format_mix",
            "le_path_binary_ffmpeg",
        ]

        for le_name in line_edits:
            assert hasattr(ui, le_name), f"Missing line edit: {le_name}"
            line_edit = getattr(ui, le_name)
            assert isinstance(line_edit, QtWidgets.QLineEdit)

        # Test buttons exist
        assert hasattr(ui, "pb_download_base_path")
        assert hasattr(ui, "pb_path_binary_ffmpeg")

    def test_ui_dialog_button_box(self, qapp):
        """Test that the dialog has OK and Cancel buttons."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        assert ui.bb_dialog is not None
        assert isinstance(ui.bb_dialog, QtWidgets.QDialogButtonBox)
        # Check that standard buttons include OK and Cancel
        buttons = ui.bb_dialog.standardButtons()
        assert QtWidgets.QDialogButtonBox.StandardButton.Ok in buttons
        assert QtWidgets.QDialogButtonBox.StandardButton.Cancel in buttons


class TestDialogPreferencesCategories:
    """Test the DialogPreferences category initialization and navigation."""

    @pytest.fixture
    def mock_settings(self):
        """Create a mock Settings object."""
        settings = Mock()
        settings.data = Mock()

        # Set default values for all parameters
        settings.data.lyrics_embed = False
        settings.data.lyrics_file = False
        settings.data.use_primary_album_artist = False
        settings.data.video_download = False
        settings.data.download_dolby_atmos = False
        settings.data.download_delay = False
        settings.data.video_convert_mp4 = False
        settings.data.extract_flac = False
        settings.data.metadata_cover_embed = False
        settings.data.mark_explicit = False
        settings.data.cover_album_file = False
        settings.data.skip_existing = False
        settings.data.symlink_to_track = False
        settings.data.playlist_create = False

        settings.data.download_base_path = str(Path.home())
        settings.data.format_album = "{artist}/{album}"
        settings.data.format_playlist = "Playlists/{name}"
        settings.data.format_mix = "Mixes/{name}"
        settings.data.format_track = "{title}"
        settings.data.format_video = "{title}"
        settings.data.path_binary_ffmpeg = "ffmpeg"

        settings.data.album_track_num_pad_min = 2
        settings.data.downloads_concurrent_max = 3

        settings.data.quality_audio = Mock()
        settings.data.quality_video = Mock()
        settings.data.metadata_cover_dimension = Mock()

        return settings

    @patch.object(DialogPreferences, "exec")
    def test_init_categories_adds_all_items(self, mock_exec, mock_settings, qapp):
        """Test that _init_categories adds all 4 categories to the list."""
        settings_save = QtCore.Signal()

        with patch.object(DialogPreferences, "gui_populate"):
            dialog = DialogPreferences(mock_settings, settings_save)

            # Check that all categories were added
            assert dialog.ui.lw_categories.count() == 4
            assert dialog.ui.lw_categories.item(0).text() == "Flags"
            assert dialog.ui.lw_categories.item(1).text() == "Quality"
            assert dialog.ui.lw_categories.item(2).text() == "Numbers"
            assert dialog.ui.lw_categories.item(3).text() == "Paths & Formats"

    @patch.object(DialogPreferences, "exec")
    def test_init_categories_sets_first_selected(self, mock_exec, mock_settings, qapp):
        """Test that the first category is selected by default."""
        settings_save = QtCore.Signal()

        with patch.object(DialogPreferences, "gui_populate"):
            dialog = DialogPreferences(mock_settings, settings_save)

            # Check that first item is selected
            assert dialog.ui.lw_categories.currentRow() == 0

    @patch.object(DialogPreferences, "exec")
    def test_category_change_switches_page(self, mock_exec, mock_settings, qapp):
        """Test that changing category switches the stacked widget page."""
        settings_save = QtCore.Signal()

        with patch.object(DialogPreferences, "gui_populate"):
            dialog = DialogPreferences(mock_settings, settings_save)

            # Initially on page 0
            assert dialog.ui.sw_categories.currentIndex() == 0

            # Change to category 1 (Quality)
            dialog.ui.lw_categories.setCurrentRow(1)
            assert dialog.ui.sw_categories.currentIndex() == 1

            # Change to category 2 (Numbers)
            dialog.ui.lw_categories.setCurrentRow(2)
            assert dialog.ui.sw_categories.currentIndex() == 2

            # Change to category 3 (Paths & Formats)
            dialog.ui.lw_categories.setCurrentRow(3)
            assert dialog.ui.sw_categories.currentIndex() == 3

            # Back to category 0 (Flags)
            dialog.ui.lw_categories.setCurrentRow(0)
            assert dialog.ui.sw_categories.currentIndex() == 0

    @patch.object(DialogPreferences, "exec")
    def test_on_category_changed_method(self, mock_exec, mock_settings, qapp):
        """Test that _on_category_changed method works correctly."""
        settings_save = QtCore.Signal()

        with patch.object(DialogPreferences, "gui_populate"):
            dialog = DialogPreferences(mock_settings, settings_save)

            # Test method directly
            dialog._on_category_changed(0)
            assert dialog.ui.sw_categories.currentIndex() == 0

            dialog._on_category_changed(1)
            assert dialog.ui.sw_categories.currentIndex() == 1

            dialog._on_category_changed(2)
            assert dialog.ui.sw_categories.currentIndex() == 2

            dialog._on_category_changed(3)
            assert dialog.ui.sw_categories.currentIndex() == 3


class TestDialogPreferencesIntegration:
    """Integration tests for the complete dialog functionality."""

    @pytest.fixture
    def mock_settings(self):
        """Create a mock Settings object with all required attributes."""
        settings = Mock()
        settings.data = Mock()

        # Set all required attributes
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

        settings.data.album_track_num_pad_min = 2
        settings.data.downloads_concurrent_max = 3

        settings.data.quality_audio = Mock()
        settings.data.quality_video = Mock()
        settings.data.metadata_cover_dimension = Mock()

        return settings

    @patch.object(DialogPreferences, "exec")
    def test_dialog_structure_is_correct(self, mock_exec, mock_settings, qapp):
        """Test that the complete dialog structure is correctly set up."""
        settings_save = QtCore.Signal()

        with patch.object(DialogPreferences, "gui_populate"):
            dialog = DialogPreferences(mock_settings, settings_save)

            # Check dialog has UI
            assert hasattr(dialog, "ui")
            assert isinstance(dialog.ui, Ui_DialogSettings)

            # Check categories list is populated
            assert dialog.ui.lw_categories.count() == 4

            # Check stacked widget has 4 pages
            assert dialog.ui.sw_categories.count() == 4

            # Check all pages are accessible
            for i in range(4):
                page = dialog.ui.sw_categories.widget(i)
                assert page is not None

    @patch.object(DialogPreferences, "exec")
    def test_navigation_between_all_categories(self, mock_exec, mock_settings, qapp):
        """Test that navigation works correctly between all categories."""
        settings_save = QtCore.Signal()

        with patch.object(DialogPreferences, "gui_populate"):
            dialog = DialogPreferences(mock_settings, settings_save)

            # Navigate through all categories
            for i in range(4):
                dialog.ui.lw_categories.setCurrentRow(i)
                assert dialog.ui.sw_categories.currentIndex() == i

                # Check that the correct page is visible
                current_widget = dialog.ui.sw_categories.currentWidget()
                assert current_widget is not None
