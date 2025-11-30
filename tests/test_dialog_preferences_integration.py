"""Integration tests for DialogPreferences with the refactored UI."""

from unittest.mock import Mock, patch

import pytest
from PySide6 import QtCore, QtWidgets

from tidal_dl_ng.config import Settings
from tidal_dl_ng.dialog import DialogPreferences


@pytest.fixture
def qapp():
    """Create QApplication instance for tests."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    yield app


@pytest.fixture
def mock_settings():
    """Create a mock Settings object with all required attributes."""
    settings = Mock(spec=Settings)
    settings.data = Mock()

    # Boolean flags
    bool_attrs = [
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
    ]
    for attr in bool_attrs:
        setattr(settings.data, attr, False)

    # String paths
    path_attrs = [
        "download_base_path",
        "format_album",
        "format_playlist",
        "format_mix",
        "format_track",
        "format_video",
        "path_binary_ffmpeg",
    ]
    for attr in path_attrs:
        setattr(settings.data, attr, f"/test/{attr}")

    # Numeric values
    settings.data.album_track_num_pad_min = 2
    settings.data.downloads_concurrent_max = 3

    # Enum values
    settings.data.quality_audio = Mock()
    settings.data.quality_video = Mock()
    settings.data.metadata_cover_dimension = Mock()

    return settings


class TestDialogPreferencesInitialization:
    """Test DialogPreferences initialization with refactored UI."""

    @patch.object(DialogPreferences, "exec")
    @patch.object(DialogPreferences, "gui_populate")
    def test_dialog_initializes_with_ui(self, mock_populate, mock_exec, mock_settings, qapp):
        """Test that DialogPreferences initializes with the new UI."""
        settings_save = QtCore.Signal()
        dialog = DialogPreferences(mock_settings, settings_save)

        assert hasattr(dialog, "ui")
        assert dialog.ui is not None

    @patch.object(DialogPreferences, "exec")
    @patch.object(DialogPreferences, "gui_populate")
    def test_categories_initialized_correctly(self, mock_populate, mock_exec, mock_settings, qapp):
        """Test that categories are initialized correctly."""
        settings_save = QtCore.Signal()
        dialog = DialogPreferences(mock_settings, settings_save)

        # Check categories count
        assert dialog.ui.lw_categories.count() == 4

        # Check categories text
        categories = [dialog.ui.lw_categories.item(i).text() for i in range(4)]
        assert categories == ["Flags", "Quality", "Numbers", "Paths & Formats"]

    @patch.object(DialogPreferences, "exec")
    @patch.object(DialogPreferences, "gui_populate")
    def test_first_category_selected_by_default(self, mock_populate, mock_exec, mock_settings, qapp):
        """Test that the first category is selected on initialization."""
        settings_save = QtCore.Signal()
        dialog = DialogPreferences(mock_settings, settings_save)

        assert dialog.ui.lw_categories.currentRow() == 0
        assert dialog.ui.sw_categories.currentIndex() == 0


class TestDialogPreferencesCategoryNavigation:
    """Test category navigation functionality."""

    @patch.object(DialogPreferences, "exec")
    @patch.object(DialogPreferences, "gui_populate")
    def test_category_change_updates_page(self, mock_populate, mock_exec, mock_settings, qapp):
        """Test that changing category updates the displayed page."""
        settings_save = QtCore.Signal()
        dialog = DialogPreferences(mock_settings, settings_save)

        # Test each category
        for i in range(4):
            dialog.ui.lw_categories.setCurrentRow(i)
            assert dialog.ui.sw_categories.currentIndex() == i

    @patch.object(DialogPreferences, "exec")
    @patch.object(DialogPreferences, "gui_populate")
    def test_on_category_changed_signal_connected(self, mock_populate, mock_exec, mock_settings, qapp):
        """Test that the category change signal is properly connected."""
        settings_save = QtCore.Signal()
        dialog = DialogPreferences(mock_settings, settings_save)

        # Verify the connection by changing category programmatically
        initial_page = dialog.ui.sw_categories.currentIndex()
        dialog.ui.lw_categories.setCurrentRow(2)
        new_page = dialog.ui.sw_categories.currentIndex()

        assert initial_page != new_page
        assert new_page == 2

    @patch.object(DialogPreferences, "exec")
    @patch.object(DialogPreferences, "gui_populate")
    def test_navigate_through_all_categories_sequentially(self, mock_populate, mock_exec, mock_settings, qapp):
        """Test sequential navigation through all categories."""
        settings_save = QtCore.Signal()
        dialog = DialogPreferences(mock_settings, settings_save)

        # Navigate forward
        for i in range(4):
            dialog.ui.lw_categories.setCurrentRow(i)
            assert dialog.ui.sw_categories.currentIndex() == i
            assert dialog.ui.lw_categories.currentRow() == i

        # Navigate backward
        for i in range(3, -1, -1):
            dialog.ui.lw_categories.setCurrentRow(i)
            assert dialog.ui.sw_categories.currentIndex() == i
            assert dialog.ui.lw_categories.currentRow() == i


class TestDialogPreferencesWidgetAccess:
    """Test access to widgets through DialogPreferences."""

    @patch.object(DialogPreferences, "exec")
    @patch.object(DialogPreferences, "gui_populate")
    def test_access_flags_checkboxes(self, mock_populate, mock_exec, mock_settings, qapp):
        """Test that flag checkboxes are accessible."""
        settings_save = QtCore.Signal()
        dialog = DialogPreferences(mock_settings, settings_save)

        checkbox_names = ["cb_video_download", "cb_lyrics_embed", "cb_skip_existing"]

        for name in checkbox_names:
            checkbox = getattr(dialog.ui, name, None)
            assert checkbox is not None
            assert isinstance(checkbox, QtWidgets.QCheckBox)

    @patch.object(DialogPreferences, "exec")
    @patch.object(DialogPreferences, "gui_populate")
    def test_access_quality_combos(self, mock_populate, mock_exec, mock_settings, qapp):
        """Test that quality combo boxes are accessible."""
        settings_save = QtCore.Signal()
        dialog = DialogPreferences(mock_settings, settings_save)

        combo_names = ["c_quality_audio", "c_quality_video", "c_metadata_cover_dimension"]

        for name in combo_names:
            combo = getattr(dialog.ui, name, None)
            assert combo is not None
            assert isinstance(combo, QtWidgets.QComboBox)

    @patch.object(DialogPreferences, "exec")
    @patch.object(DialogPreferences, "gui_populate")
    def test_access_numbers_spinboxes(self, mock_populate, mock_exec, mock_settings, qapp):
        """Test that number spinboxes are accessible."""
        settings_save = QtCore.Signal()
        dialog = DialogPreferences(mock_settings, settings_save)

        spinbox_names = ["sb_album_track_num_pad_min", "sb_downloads_concurrent_max"]

        for name in spinbox_names:
            spinbox = getattr(dialog.ui, name, None)
            assert spinbox is not None
            assert isinstance(spinbox, QtWidgets.QSpinBox)

    @patch.object(DialogPreferences, "exec")
    @patch.object(DialogPreferences, "gui_populate")
    def test_access_path_line_edits(self, mock_populate, mock_exec, mock_settings, qapp):
        """Test that path line edits are accessible."""
        settings_save = QtCore.Signal()
        dialog = DialogPreferences(mock_settings, settings_save)

        line_edit_names = ["le_download_base_path", "le_format_track", "le_path_binary_ffmpeg"]

        for name in line_edit_names:
            line_edit = getattr(dialog.ui, name, None)
            assert line_edit is not None
            assert isinstance(line_edit, QtWidgets.QLineEdit)


class TestDialogPreferencesPageVisibility:
    """Test that pages are correctly shown/hidden based on category selection."""

    @patch.object(DialogPreferences, "exec")
    @patch.object(DialogPreferences, "gui_populate")
    def test_only_current_page_visible(self, mock_populate, mock_exec, mock_settings, qapp):
        """Test that only the current page is visible."""
        settings_save = QtCore.Signal()
        dialog = DialogPreferences(mock_settings, settings_save)

        for i in range(4):
            dialog.ui.lw_categories.setCurrentRow(i)
            current_widget = dialog.ui.sw_categories.currentWidget()

            # Check that the current widget is the expected page
            if i == 0:
                assert current_widget == dialog.ui.page_flags
            elif i == 1:
                assert current_widget == dialog.ui.page_quality
            elif i == 2:
                assert current_widget == dialog.ui.page_numbers
            elif i == 3:
                assert current_widget == dialog.ui.page_paths

    @patch.object(DialogPreferences, "exec")
    @patch.object(DialogPreferences, "gui_populate")
    def test_page_content_accessible_when_selected(self, mock_populate, mock_exec, mock_settings, qapp):
        """Test that page content is accessible when the page is selected."""
        settings_save = QtCore.Signal()
        dialog = DialogPreferences(mock_settings, settings_save)

        # Select Flags page
        dialog.ui.lw_categories.setCurrentRow(0)
        assert dialog.ui.gb_flags.isVisibleTo(dialog.ui.page_flags)

        # Select Quality page
        dialog.ui.lw_categories.setCurrentRow(1)
        assert dialog.ui.gb_choices.isVisibleTo(dialog.ui.page_quality)

        # Select Numbers page
        dialog.ui.lw_categories.setCurrentRow(2)
        assert dialog.ui.gb_numbers.isVisibleTo(dialog.ui.page_numbers)

        # Select Paths page
        dialog.ui.lw_categories.setCurrentRow(3)
        assert dialog.ui.gb_path.isVisibleTo(dialog.ui.page_paths)


class TestDialogPreferencesMethodsStillWork:
    """Test that existing DialogPreferences methods still work with new UI."""

    @patch.object(DialogPreferences, "exec")
    @patch.object(DialogPreferences, "gui_populate")
    def test_init_methods_called(self, mock_populate, mock_exec, mock_settings, qapp):
        """Test that initialization methods are called."""
        settings_save = QtCore.Signal()

        with (
            patch.object(DialogPreferences, "_init_checkboxes") as mock_init_cb,
            patch.object(DialogPreferences, "_init_comboboxes") as mock_init_combo,
            patch.object(DialogPreferences, "_init_line_edit") as mock_init_le,
            patch.object(DialogPreferences, "_init_spin_box") as mock_init_sb,
            patch.object(DialogPreferences, "_init_categories") as mock_init_cat,
        ):

            # Instantiate to trigger init methods; no need to keep a variable
            DialogPreferences(mock_settings, settings_save)

            mock_init_cb.assert_called_once()
            mock_init_combo.assert_called_once()
            mock_init_le.assert_called_once()
            mock_init_sb.assert_called_once()
            mock_init_cat.assert_called_once()

    @patch.object(DialogPreferences, "exec")
    def test_on_category_changed_method_exists(self, mock_exec, mock_settings, qapp):
        """Test that _on_category_changed method exists and is callable."""
        settings_save = QtCore.Signal()

        with patch.object(DialogPreferences, "gui_populate"):
            dialog = DialogPreferences(mock_settings, settings_save)

            assert hasattr(dialog, "_on_category_changed")
            assert callable(dialog._on_category_changed)

            # Test calling it doesn't raise an error
            dialog._on_category_changed(0)
            dialog._on_category_changed(1)
            dialog._on_category_changed(2)
            dialog._on_category_changed(3)
