import datetime
import os
import os.path
import shutil
import webbrowser
from enum import StrEnum
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets
from tidalapi import Quality as QualityAudio

from tidal_dl_ng import __version__
from tidal_dl_ng.config import Settings
from tidal_dl_ng.constants import CoverDimensions, QualityVideo
from tidal_dl_ng.model.cfg import HelpSettings
from tidal_dl_ng.model.cfg import Settings as ModelSettings
from tidal_dl_ng.model.meta import ReleaseLatest
from tidal_dl_ng.ui.dialog_login import Ui_DialogLogin
from tidal_dl_ng.ui.dialog_settings import Ui_DialogSettings
from tidal_dl_ng.ui.dialog_version import Ui_DialogVersion


class DialogVersion(QtWidgets.QDialog):
    """Version dialog."""

    ui: Ui_DialogVersion

    def __init__(
        self, parent=None, update_check: bool = False, update_available: bool = False, update_info: ReleaseLatest = None
    ):
        super().__init__(parent)

        # Create an instance of the GUI
        self.ui = Ui_DialogVersion()

        # Run the .setupUi() method to show the GUI
        self.ui.setupUi(self)
        # Set the version.
        self.ui.l_version.setText("v" + __version__)

        if not update_check:
            self.update_info_hide()
            self.error_hide()
        else:
            self.update_info(update_available, update_info)

        # Show
        self.exec()

    def update_info(self, update_available: bool, update_info: ReleaseLatest):
        if not update_available and update_info.version == "v0.0.0":
            self.update_info_hide()
            self.ui.l_error_details.setText(
                "Cannot retrieve update information. Maybe something is wrong with your internet connection."
            )
        else:
            self.error_hide()

            if not update_available:
                self.ui.l_h_version_new.setText("Latest available version:")
                self.changelog_hide()
            else:
                self.ui.l_changelog_details.setText(update_info.release_info)
                self.ui.pb_download.clicked.connect(lambda: webbrowser.open(update_info.url))

            self.ui.l_version_new.setText(update_info.version)

    def error_hide(self):
        self.ui.l_error.setHidden(True)
        self.ui.l_error_details.setHidden(True)

    def update_info_hide(self):
        self.ui.l_h_version_new.setHidden(True)
        self.ui.l_version_new.setHidden(True)
        self.changelog_hide()

    def changelog_hide(self):
        self.ui.l_changelog.setHidden(True)
        self.ui.l_changelog_details.setHidden(True)
        self.ui.pb_download.setHidden(True)


class DialogLogin(QtWidgets.QDialog):
    """Version dialog."""

    ui: Ui_DialogLogin
    url_redirect: str

    def __init__(self, url_login: str, hint: str, expires_in: int, parent=None):
        super().__init__(parent)

        datetime_current: datetime.datetime = datetime.datetime.now()
        datetime_expires: datetime.datetime = datetime_current + datetime.timedelta(0, expires_in)

        # Create an instance of the GUI
        self.ui = Ui_DialogLogin()

        # Run the .setupUi() method to show the GUI
        self.ui.setupUi(self)
        # Set data.
        self.ui.tb_url_login.setText(f'<a href="https://{url_login}">https://{url_login}</a>')
        self.ui.l_hint.setText(hint)
        self.ui.l_expires_date_time.setText(datetime_expires.strftime("%Y-%m-%d %H:%M"))
        # Show
        self.return_code = self.exec()


class DialogPreferences(QtWidgets.QDialog):
    """Preferences dialog (non-blocking, deferred population).

    The macOS Text Services Manager (TSM) can emit CFMessagePortSendRequest failures
    when text widgets (e.g., QLineEdit) are populated before the window is fully
    registered with the window server. To avoid this, heavy UI population is deferred
    until after the dialog is shown via an overridden showEvent using a QTimer.

    All expensive or input-related operations (setting text, pixmaps) are performed
    only once after first show to prevent premature IME/TSM activation.
    """

    ui: Ui_DialogSettings
    settings: Settings
    data: ModelSettings
    s_settings_save: object  # Accept any signal-like object (loosened for runtime SignalInstance)
    help_settings: HelpSettings
    parameters_checkboxes: list[str]
    parameters_combo: list[tuple[str, StrEnum]]
    parameters_line_edit: list[str]
    parameters_spin_box: list[str]
    prefix_checkbox: str = "cb_"
    prefix_label: str = "l_"
    prefix_icon: str = "icon_"
    prefix_line_edit: str = "le_"
    prefix_combo: str = "c_"
    prefix_spin_box: str = "sb_"
    _icon: QtGui.QIcon | None = None
    _populated: bool = False

    def __init__(self, settings: Settings, settings_save: object, parent=None):
        super().__init__(parent)

        self.settings = settings
        self.data = settings.data
        self.s_settings_save = settings_save
        self.help_settings = HelpSettings()

        self._init_checkboxes()
        self._init_comboboxes()
        self._init_line_edit()
        self._init_spin_box()

        # Create an instance of the GUI and perform lightweight UI setup only.
        self.ui = Ui_DialogSettings()
        self.ui.setupUi(self)

        # Non-blocking pattern: caller will invoke .show() / .open(); we do NOT call exec().
        # Heavy population deferred to showEvent.

    # ------------------------------
    # Internal helpers
    # ------------------------------
    def ensure_main_thread(self) -> None:
        """Ensure method runs on the main (GUI) thread."""
        app = QtWidgets.QApplication.instance()
        if app and QtCore.QThread.currentThread() is not app.thread():
            raise RuntimeError

    @property
    def icon(self) -> QtGui.QIcon:
        """Lazy-create and cache the dialog icon."""
        if self._icon is None:
            pixmapi: QtWidgets.QStyle.StandardPixmap = QtWidgets.QStyle.StandardPixmap.SP_MessageBoxQuestion
            self._icon = self.style().standardIcon(pixmapi)
        return self._icon

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        """On first show, defer population to avoid macOS TSM early activation."""
        super().showEvent(event)
        if not self._populated:
            self._populated = True
            # Slight delay on macOS to ensure window server registration.
            delay_ms = 50 if os.name == "posix" and shutil.which("uname") and os.uname().sysname == "Darwin" else 0
            QtCore.QTimer.singleShot(delay_ms, self._deferred_populate)

    def _deferred_populate(self) -> None:
        """Populate widgets after dialog is visible (safe for macOS TSM)."""
        self.ensure_main_thread()
        QtWidgets.QApplication.processEvents()
        self.gui_populate()

    def _init_line_edit(self):
        self.parameters_line_edit = [
            "download_base_path",
            "format_album",
            "format_playlist",
            "format_mix",
            "format_track",
            "format_video",
            "path_binary_ffmpeg",
        ]

    def _init_spin_box(self):
        self.parameters_spin_box = ["album_track_num_pad_min", "downloads_concurrent_max"]

    def _init_comboboxes(self):
        self.parameters_combo = [
            ("quality_audio", QualityAudio),
            ("quality_video", QualityVideo),
            ("metadata_cover_dimension", CoverDimensions),
        ]

    def _init_checkboxes(self):
        self.parameters_checkboxes = [
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

    def gui_populate(self):
        self.populate_checkboxes()
        self.populate_combo()
        self.populate_line_edit()
        self.populate_spin_box()

    def dialog_chose_file(
        self,
        obj_line_edit: QtWidgets.QLineEdit,
        file_mode: QtWidgets.QFileDialog.FileMode = QtWidgets.QFileDialog.FileMode.Directory,
        path_default: str | None = None,
    ) -> None:
        # If a path is set, use it otherwise the users home directory.
        path_settings: str = os.path.expanduser(obj_line_edit.text()) if obj_line_edit.text() else ""
        # Check if obj_line_edit is empty but path_default can be used instead
        if not path_settings and path_default:
            expanded_default = os.path.expanduser(path_default)
            path_settings = expanded_default
        dir_current: str = path_settings if path_settings and os.path.exists(path_settings) else str(Path.home())
        dialog: QtWidgets.QFileDialog = QtWidgets.QFileDialog()

        # Set to directory mode only but show files.
        dialog.setFileMode(file_mode)
        dialog.setViewMode(QtWidgets.QFileDialog.ViewMode.Detail)
        dialog.setOption(QtWidgets.QFileDialog.Option.ShowDirsOnly, False)
        dialog.setOption(QtWidgets.QFileDialog.Option.DontResolveSymlinks, True)

        # There is a bug in the PyQt implementation, which hides files in Directory mode.
        # Thus, we need to use the PyQt dialog instead of the native dialog.
        if os.name == "nt" and file_mode == QtWidgets.QFileDialog.Directory:
            dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)

        dialog.setDirectory(dir_current)

        # Execute dialog and set path if something is chosen.
        if dialog.exec():
            dir_name: str = dialog.selectedFiles()[0]
            path: Path = Path(dir_name)
            obj_line_edit.setText(str(path))

    def populate_line_edit(self):
        for pn in self.parameters_line_edit:
            label_icon: QtWidgets.QLabel = getattr(self.ui, self.prefix_label + self.prefix_icon + pn)
            label: QtWidgets.QLabel = getattr(self.ui, self.prefix_label + pn)
            line_edit: QtWidgets.QLineEdit = getattr(self.ui, self.prefix_line_edit + pn)

            label_icon.setPixmap(QtGui.QPixmap(self.icon.pixmap(QtCore.QSize(16, 16))))
            label_icon.setToolTip(getattr(self.help_settings, pn))
            label.setText(pn)
            # Safe line edit updates (suppress signals/UI updates during bulk setText)
            line_edit.blockSignals(True)
            line_edit.setUpdatesEnabled(False)
            line_edit.setText(str(getattr(self.data, pn)))
            line_edit.setUpdatesEnabled(True)
            line_edit.blockSignals(False)

        # Base Path File Dialog
        self.ui.pb_download_base_path.clicked.connect(lambda x: self.dialog_chose_file(self.ui.le_download_base_path))
        # Defer shutil.which() call to prevent TSM errors during initialization
        self.ui.pb_path_binary_ffmpeg.clicked.connect(
            lambda x: self.dialog_chose_file(
                self.ui.le_path_binary_ffmpeg,
                file_mode=QtWidgets.QFileDialog.FileMode.ExistingFiles,
                path_default=self._get_ffmpeg_path(),
            )
        )

    def populate_combo(self):
        for pn, values in self.parameters_combo:
            label_icon: QtWidgets.QLabel = getattr(self.ui, self.prefix_label + self.prefix_icon + pn)
            label: QtWidgets.QLabel = getattr(self.ui, self.prefix_label + pn)
            combo: QtWidgets.QComboBox = getattr(self.ui, self.prefix_combo + pn)
            setting_current = getattr(self.data, pn)

            label_icon.setPixmap(QtGui.QPixmap(self.icon.pixmap(QtCore.QSize(16, 16))))
            label_icon.setToolTip(getattr(self.help_settings, pn))
            label.setText(pn)

            for index, v in enumerate(list(values)):
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

    def populate_spin_box(self):
        for pn in self.parameters_spin_box:
            label_icon: QtWidgets.QLabel = getattr(self.ui, self.prefix_label + self.prefix_icon + pn)
            label: QtWidgets.QLabel = getattr(self.ui, self.prefix_label + pn)
            spin_box: QtWidgets.QSpinBox = getattr(self.ui, self.prefix_spin_box + pn)

            label_icon.setPixmap(QtGui.QPixmap(self.icon.pixmap(QtCore.QSize(16, 16))))
            label_icon.setToolTip(getattr(self.help_settings, pn))
            label.setText(pn)
            spin_box.setValue(getattr(self.data, pn))

    def accept(self):
        # Get settings.
        self.to_settings()
        self.done(1)

    def _get_ffmpeg_path(self) -> str | None:
        """Get the ffmpeg binary path using shutil.which.

        This method is called only when needed (when button is clicked),
        not during initialization, to prevent TSM errors on macOS.

        Returns:
            str | None: Path to ffmpeg binary or None if not found.
        """
        return shutil.which("ffmpeg")

    def to_settings(self):
        for item in self.parameters_checkboxes:
            setattr(self.settings.data, item, getattr(self.ui, self.prefix_checkbox + item).isChecked())

        for item in self.parameters_line_edit:
            setattr(self.settings.data, item, getattr(self.ui, self.prefix_line_edit + item).text())

        for item in self.parameters_combo:
            setattr(self.settings.data, item[0], getattr(self.ui, self.prefix_combo + item[0]).currentData())

        for item in self.parameters_spin_box:
            setattr(self.settings.data, item, getattr(self.ui, self.prefix_spin_box + item).value())

        self.s_settings_save.emit()
