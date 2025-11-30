"""Tests for the settings dialog category structure and organization."""

import pytest
from PySide6 import QtCore, QtWidgets

from tidal_dl_ng.ui.dialog_settings import Ui_DialogSettings


@pytest.fixture
def qapp():
    """Create QApplication instance for tests."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    yield app


class TestSettingsDialogStructure:
    """Test the structural integrity of the settings dialog."""

    def test_dialog_has_proper_layout_hierarchy(self, qapp):
        """Test that the dialog has the correct layout hierarchy."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        # Check main layout
        main_layout = dialog.layout()
        assert main_layout is not None
        assert isinstance(main_layout, QtWidgets.QVBoxLayout)

    def test_categories_and_pages_match(self, qapp):
        """Test that the number of pages matches the expected categories."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        # We expect 4 categories/pages
        expected_categories = ["Flags", "Quality", "Numbers", "Paths & Formats"]
        assert ui.sw_categories.count() == len(expected_categories)

    def test_all_pages_have_layouts(self, qapp):
        """Test that all pages in the stacked widget have proper layouts."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        for i in range(ui.sw_categories.count()):
            page = ui.sw_categories.widget(i)
            assert page is not None
            assert page.layout() is not None
            assert isinstance(page.layout(), QtWidgets.QVBoxLayout)

    def test_all_pages_have_group_boxes(self, qapp):
        """Test that all pages contain at least one group box."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        for i in range(ui.sw_categories.count()):
            page = ui.sw_categories.widget(i)
            group_boxes = page.findChildren(QtWidgets.QGroupBox)
            assert len(group_boxes) > 0, f"Page {i} should have at least one group box"


class TestSettingsFlagsPage:
    """Test the Flags page specifically."""

    def test_flags_page_is_first(self, qapp):
        """Test that the Flags page is at index 0."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        assert ui.page_flags is not None
        assert ui.sw_categories.widget(0) == ui.page_flags

    def test_flags_page_has_correct_number_of_checkboxes(self, qapp):
        """Test that the Flags page has the expected number of checkboxes."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        # Count checkboxes in the flags page
        checkboxes = ui.page_flags.findChildren(QtWidgets.QCheckBox)
        assert len(checkboxes) == 14, "Flags page should have 14 checkboxes"

    def test_all_flags_checkboxes_accessible_via_ui(self, qapp):
        """Test that all flag checkboxes are accessible through the ui object."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        checkbox_names = [
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

        for name in checkbox_names:
            checkbox = getattr(ui, name, None)
            assert checkbox is not None, f"Checkbox {name} not found"
            assert isinstance(checkbox, QtWidgets.QCheckBox)


class TestSettingsQualityPage:
    """Test the Quality page specifically."""

    def test_quality_page_is_second(self, qapp):
        """Test that the Quality page is at index 1."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        assert ui.page_quality is not None
        assert ui.sw_categories.widget(1) == ui.page_quality

    def test_quality_page_has_combo_boxes(self, qapp):
        """Test that the Quality page has combo boxes."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        combos = ui.page_quality.findChildren(QtWidgets.QComboBox)
        assert len(combos) == 3, "Quality page should have 3 combo boxes"

    def test_quality_combo_boxes_have_labels(self, qapp):
        """Test that each combo box has associated labels."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        combo_label_pairs = [
            ("c_quality_audio", "l_quality_audio", "l_icon_quality_audio"),
            ("c_quality_video", "l_quality_video", "l_icon_quality_video"),
            ("c_metadata_cover_dimension", "l_metadata_cover_dimension", "l_icon_metadata_cover_dimension"),
        ]

        for combo_name, label_name, icon_label_name in combo_label_pairs:
            combo = getattr(ui, combo_name, None)
            label = getattr(ui, label_name, None)
            icon_label = getattr(ui, icon_label_name, None)

            assert combo is not None, f"ComboBox {combo_name} not found"
            assert label is not None, f"Label {label_name} not found"
            assert icon_label is not None, f"Icon label {icon_label_name} not found"


class TestSettingsNumbersPage:
    """Test the Numbers page specifically."""

    def test_numbers_page_is_third(self, qapp):
        """Test that the Numbers page is at index 2."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        assert ui.page_numbers is not None
        assert ui.sw_categories.widget(2) == ui.page_numbers

    def test_numbers_page_has_spin_boxes(self, qapp):
        """Test that the Numbers page has spin boxes."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        spinboxes = ui.page_numbers.findChildren(QtWidgets.QSpinBox)
        assert len(spinboxes) == 2, "Numbers page should have 2 spin boxes"

    def test_spin_boxes_have_valid_ranges(self, qapp):
        """Test that spin boxes have appropriate min/max values."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        # Test album track num padding
        assert ui.sb_album_track_num_pad_min.maximum() == 4
        assert ui.sb_album_track_num_pad_min.minimum() >= 0

        # Test concurrent downloads
        assert ui.sb_downloads_concurrent_max.minimum() == 1
        assert ui.sb_downloads_concurrent_max.maximum() == 5


class TestSettingsPathsPage:
    """Test the Paths & Formats page specifically."""

    def test_paths_page_is_fourth(self, qapp):
        """Test that the Paths page is at index 3."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        assert ui.page_paths is not None
        assert ui.sw_categories.widget(3) == ui.page_paths

    def test_paths_page_has_line_edits(self, qapp):
        """Test that the Paths page has line edits."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        line_edits = ui.page_paths.findChildren(QtWidgets.QLineEdit)
        assert len(line_edits) == 7, "Paths page should have 7 line edits"

    def test_paths_page_has_browse_buttons(self, qapp):
        """Test that the Paths page has browse buttons."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        buttons = ui.page_paths.findChildren(QtWidgets.QPushButton)
        # Should have at least 2 browse buttons (... buttons)
        assert len(buttons) >= 2, "Paths page should have at least 2 browse buttons"

    def test_path_line_edits_accessible(self, qapp):
        """Test that all path-related line edits are accessible."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        line_edit_names = [
            "le_download_base_path",
            "le_format_track",
            "le_format_video",
            "le_format_album",
            "le_format_playlist",
            "le_format_mix",
            "le_path_binary_ffmpeg",
        ]

        for name in line_edit_names:
            line_edit = getattr(ui, name, None)
            assert line_edit is not None, f"LineEdit {name} not found"
            assert isinstance(line_edit, QtWidgets.QLineEdit)


class TestSettingsDialogButtons:
    """Test the dialog button box."""

    def test_dialog_has_button_box(self, qapp):
        """Test that the dialog has a button box."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        assert ui.bb_dialog is not None
        assert isinstance(ui.bb_dialog, QtWidgets.QDialogButtonBox)

    def test_button_box_has_ok_and_cancel(self, qapp):
        """Test that the button box has OK and Cancel buttons."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        buttons = ui.bb_dialog.standardButtons()
        assert QtWidgets.QDialogButtonBox.StandardButton.Ok in buttons
        assert QtWidgets.QDialogButtonBox.StandardButton.Cancel in buttons

    def test_button_box_orientation(self, qapp):
        """Test that the button box has horizontal orientation."""
        dialog = QtWidgets.QDialog()
        ui = Ui_DialogSettings()
        ui.setupUi(dialog)

        assert ui.bb_dialog.orientation() == QtCore.Qt.Orientation.Horizontal
