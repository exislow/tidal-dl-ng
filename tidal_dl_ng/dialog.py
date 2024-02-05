import os.path
from enum import Enum
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets
from tidalapi import Quality as QualityAudio

from tidal_dl_ng import __version__
from tidal_dl_ng.config import Settings
from tidal_dl_ng.constants import CoverDimensions, QualityVideo, SkipExisting
from tidal_dl_ng.model.cfg import HelpSettings
from tidal_dl_ng.model.cfg import Settings as ModelSettings
from tidal_dl_ng.ui.dialog_login import Ui_DialogLogin
from tidal_dl_ng.ui.dialog_settings import Ui_DialogSettings
from tidal_dl_ng.ui.dialog_version import Ui_DialogVersion


class DialogVersion(QtWidgets.QDialog):
    """Version dialog."""

    ui: Ui_DialogVersion

    def __init__(self, parent=None):
        super().__init__(parent)

        # Create an instance of the GUI
        self.ui = Ui_DialogVersion()

        # Run the .setupUi() method to show the GUI
        self.ui.setupUi(self)
        # Set the version.
        self.ui.l_version.setText("v" + __version__)
        # Show
        self.exec()


class DialogLogin(QtWidgets.QDialog):
    """Version dialog."""

    ui: Ui_DialogLogin
    url_redirect: str
    return_code: int

    def __init__(self, url_login: str, hint: str, parent=None):
        super().__init__(parent)

        # Create an instance of the GUI
        self.ui = Ui_DialogLogin()

        # Run the .setupUi() method to show the GUI
        self.ui.setupUi(self)
        # Set data.
        self.ui.tb_url_login.setText(f'<a href="{url_login}">{url_login}</a>')
        self.ui.l_hint.setText(hint)
        # Show
        self.return_code = self.exec()

        self.url_redirect = self.ui.te_url_redirect.toPlainText()


class DialogPreferences(QtWidgets.QDialog):
    """Preferences dialog."""

    ui: Ui_DialogSettings
    settings: Settings
    data: ModelSettings
    s_settings_save: QtCore.Signal
    icon: QtGui.QIcon
    help_settings: HelpSettings
    parameters_checkboxes: [str]
    parameters_combo: [(str, Enum)]
    parameters_line_edit: [str]
    prefix_checkbox: str = "cb_"
    prefix_label: str = "l_"
    prefix_icon: str = "icon_"
    prefix_line_edit: str = "le_"
    prefix_combo: str = "c_"

    def __init__(self, settings: Settings, settings_save: QtCore.Signal, parent=None):
        super().__init__(parent)

        self.settings = settings
        self.data = settings.data
        self.s_settings_save = settings_save
        self.help_settings = HelpSettings()
        pixmapi: QtWidgets.QStyle.StandardPixmap = QtWidgets.QStyle.SP_MessageBoxQuestion
        self.icon = self.style().standardIcon(pixmapi)

        self.parameters_checkboxes = [
            "lyrics_embed",
            "lyrics_file",
            "video_download",
            "download_delay",
            "video_convert_mp4",
        ]
        self.parameters_combo = [
            ("skip_existing", SkipExisting),
            ("quality_audio", QualityAudio),
            ("quality_video", QualityVideo),
            ("metadata_cover_dimension", CoverDimensions),
        ]
        self.parameters_line_edit = [
            "download_base_path",
            "format_album",
            "format_playlist",
            "format_mix",
            "format_track",
            "format_video",
        ]

        # Create an instance of the GUI
        self.ui = Ui_DialogSettings()

        # Run the .setupUi() method to show the GUI
        self.ui.setupUi(self)
        # Set data.
        self.gui_populate()

        self.exec()

    def gui_populate(self):
        self.populate_checkboxes()
        self.populate_combo()
        self.populate_line_edit()

    def dialog_dir_open(self, obj_line_edit):
        # If a path is set, use it otherwise the users home directory.
        settings_path: str = os.path.expanduser(obj_line_edit.text()) if obj_line_edit.text() else ""
        dir_current = settings_path if settings_path and os.path.exists(settings_path) else str(Path.home())
        dialog = QtWidgets.QFileDialog()

        # Set to directory mode only but show files.
        dialog.setFileMode(QtWidgets.QFileDialog.Directory)
        dialog.setViewMode(QtWidgets.QFileDialog.Detail)
        dialog.setOption(QtWidgets.QFileDialog.ShowDirsOnly, False)
        # There is a bug in the PyQt implementation, which hides files in Directory mode.
        # Thus, we need to use the PyQt dialog instead of the native dialog.
        if os.name == "nt":
            dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
        dialog.setDirectory(dir_current)

        # Execute dialog and set path is something is choosen.
        if dialog.exec():
            dir_name = dialog.selectedFiles()[0]
            path = Path(dir_name)
            obj_line_edit.setText(str(path))

    def populate_line_edit(self):

        for pn in self.parameters_line_edit:
            label_icon: QtWidgets.QLabel = getattr(self.ui, self.prefix_label + self.prefix_icon + pn)
            label: QtWidgets.QLabel = getattr(self.ui, self.prefix_label + pn)
            line_edit: QtWidgets.QLineEdit = getattr(self.ui, self.prefix_line_edit + pn)

            label_icon.setPixmap(QtGui.QPixmap(self.icon.pixmap(QtCore.QSize(16, 16))))
            label_icon.setToolTip(getattr(self.help_settings, pn))
            label.setText(pn)
            line_edit.setText(getattr(self.data, pn))

        # Base Path File Dialog
        self.ui.pb_download_base_path.clicked.connect(lambda x: self.dialog_dir_open(self.ui.le_download_base_path))

    def populate_combo(self):

        for p in self.parameters_combo:
            pn: str = p[0]
            values: Enum = p[1]
            label_icon: QtWidgets.QLabel = getattr(self.ui, self.prefix_label + self.prefix_icon + pn)
            label: QtWidgets.QLabel = getattr(self.ui, self.prefix_label + pn)
            combo: QtWidgets.QComboBox = getattr(self.ui, self.prefix_combo + pn)
            setting_current = getattr(self.data, pn)

            label_icon.setPixmap(QtGui.QPixmap(self.icon.pixmap(QtCore.QSize(16, 16))))
            label_icon.setToolTip(getattr(self.help_settings, pn))
            label.setText(pn)

            for index, v in enumerate(values):
                combo.addItem(v.name, v)

                if v == setting_current:
                    combo.setCurrentIndex(index)

    def populate_checkboxes(self):
        for pn in self.parameters_checkboxes:
            checkbox: QtWidgets.QCheckBox = getattr(self.ui, self.prefix_checkbox + pn)

            checkbox.setText(pn)
            checkbox.setToolTip(getattr(self.help_settings, pn))
            checkbox.setIcon(self.icon)
            checkbox.setChecked(getattr(self.data, pn))

    def accept(self):
        # Get settings. TODO
        self.to_settings()
        self.done(1)

    def to_settings(self):
        for item in self.parameters_checkboxes:
            setattr(self.settings.data, item, getattr(self.ui, self.prefix_checkbox + item).isChecked())

        for item in self.parameters_line_edit:
            setattr(self.settings.data, item, getattr(self.ui, self.prefix_line_edit + item).text())

        for item in self.parameters_combo:
            setattr(self.settings.data, item[0], getattr(self.ui, self.prefix_combo + item[0]).currentData())

        self.s_settings_save.emit()
