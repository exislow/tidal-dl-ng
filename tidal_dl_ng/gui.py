# Compilation mode, support OS-specific options
# nuitka-project-if: {OS} in ("Darwin"):
#    nuitka-project: --macos-create-app-bundle
#    nuitka-project: --macos-app-icon=tidal_dl_ng/ui/icon.icns
#    nuitka-project: --macos-signed-app-name=com.exislow.TidalDlNg
#    nuitka-project: --macos-app-mode=gui
# nuitka-project-if: {OS} in ("Linux", "FreeBSD"):
#    nuitka-project: --linux-icon=tidal_dl_ng/ui/icon512.png
# nuitka-project-if: {OS} in ("Windows"):
#    nuitka-project: --windows-icon-from-ico=tidal_dl_ng/ui/icon.ico
#    nuitka-project: --file-description="TIDAL media downloader next generation."

# Debugging options, controlled via environment variable at compile time.
# nuitka-project-if: {OS} == "Windows" and os.getenv("DEBUG_COMPILATION", "no") == "yes":
#    nuitka-project: --windows-console-mode=hide
# nuitka-project-else:
#    nuitka-project: --windows-console-mode=disable
# nuitka-project-if: os.getenv("DEBUG_COMPILATION", "no") == "yes":
#    nuitka-project: --debug
#    nuitka-project: --debugger
#    nuitka-project: --experimental=allow-c-warnings
#    nuitka-project: --no-debug-immortal-assumptions
#    nuitka-project: --run
# nuitka-project-else:
#    nuitka-project: --assume-yes-for-downloads
# nuitka-project-if: os.getenv("DEPLOYMENT", "no") == "yes":
#    nuitka-project: --deployment

# The PySide6 plugin covers qt-plugins
# nuitka-project: --standalone
# nuitka-project: --output-dir=dist
# nuitka-project: --enable-plugin=pyside6
# nuitka-project: --include-qt-plugins=qml
# nuitka-project: --noinclude-dlls=libQt6Charts*
# nuitka-project: --noinclude-dlls=libQt6Quick3D*
# nuitka-project: --noinclude-dlls=libQt6Sensors*
# nuitka-project: --noinclude-dlls=libQt6Test*
# nuitka-project: --noinclude-dlls=libQt6WebEngine*
# nuitka-project: --include-data-files={MAIN_DIRECTORY}/ui/icon*=tidal_dl_ng/ui/
# nuitka-project: --include-data-files={MAIN_DIRECTORY}/ui/default_album_image.png=tidal_dl_ng/ui/default_album_image.png
# nuitka-project: --include-data-files=./pyproject.toml=pyproject.toml
# nuitka-project: --force-stderr-spec="{TEMP}/tidal-dl-ng.err.log"
# nuitka-project: --force-stdout-spec="{TEMP}/tidal-dl-ng.out.log"
# nuitka-project: --company-name=exislow


import math
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from typing import Any

from requests.exceptions import HTTPError
from tidalapi.session import LinkLogin

from tidal_dl_ng import __version__, update_available
from tidal_dl_ng.dialog import DialogLogin, DialogPreferences, DialogVersion
from tidal_dl_ng.helper.gui import (
    FilterHeader,
    HumanProxyModel,
    get_queue_download_media,
    get_queue_download_quality_audio,
    get_queue_download_quality_video,
    get_results_media_item,
    get_user_list_media_item,
    set_queue_download_media,
    set_user_list_media,
)
from tidal_dl_ng.helper.path import get_format_template, resource_path
from tidal_dl_ng.helper.tidal import (
    favorite_function_factory,
    get_tidal_media_id,
    get_tidal_media_type,
    instantiate_media,
    items_results_all,
    name_builder_artist,
    name_builder_title,
    quality_audio_highest,
    search_results_all,
    url_ending_clean,
    user_media_lists,
)

try:
    import qdarktheme
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError as e:
    print(e)
    print("Qt dependencies missing. Cannot start GUI. Please read the 'README.md' carefully.")
    sys.exit(1)


from ansi2html import Ansi2HTMLConverter
from rich.progress import Progress
from tidalapi import Album, Mix, Playlist, Quality, Track, UserPlaylist, Video
from tidalapi.artist import Artist
from tidalapi.media import AudioMode
from tidalapi.playlist import Folder
from tidalapi.session import SearchTypes

from tidal_dl_ng.config import HandlingApp, Settings, Tidal
from tidal_dl_ng.constants import FAVORITES, QualityVideo, QueueDownloadStatus, TidalLists
from tidal_dl_ng.download import Download
from tidal_dl_ng.logger import XStream, logger_gui
from tidal_dl_ng.model.gui_data import ProgressBars, QueueDownloadItem, ResultItem, StatusbarMessage
from tidal_dl_ng.model.meta import ReleaseLatest
from tidal_dl_ng.ui.main import Ui_MainWindow
from tidal_dl_ng.ui.spinner import QtWaitingSpinner
from tidal_dl_ng.worker import Worker


# TODO: Make more use of Exceptions
class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    """Main application window for TIDAL Downloader Next Generation.

    Handles GUI setup, user interactions, and download logic.
    """

    settings: Settings
    tidal: Tidal
    dl: Download
    threadpool: QtCore.QThreadPool
    tray: QtWidgets.QSystemTrayIcon
    spinners: dict
    cover_url_current: str = ""
    shutdown: bool = False
    model_tr_results: QtGui.QStandardItemModel = QtGui.QStandardItemModel()
    proxy_tr_results: HumanProxyModel
    s_spinner_start: QtCore.Signal = QtCore.Signal(QtWidgets.QWidget)
    s_spinner_stop: QtCore.Signal = QtCore.Signal()
    pb_item: QtWidgets.QProgressBar
    s_item_advance: QtCore.Signal = QtCore.Signal(float)
    s_item_name: QtCore.Signal = QtCore.Signal(str)
    s_list_name: QtCore.Signal = QtCore.Signal(str)
    pb_list: QtWidgets.QProgressBar
    s_list_advance: QtCore.Signal = QtCore.Signal(float)
    s_pb_reset: QtCore.Signal = QtCore.Signal()
    s_populate_tree_lists: QtCore.Signal = QtCore.Signal(dict)
    s_populate_folder_children: QtCore.Signal = QtCore.Signal(object, list, list)
    s_statusbar_message: QtCore.Signal = QtCore.Signal(object)
    s_tr_results_add_top_level_item: QtCore.Signal = QtCore.Signal(object)
    s_settings_save: QtCore.Signal = QtCore.Signal()
    s_pb_reload_status: QtCore.Signal = QtCore.Signal(bool)
    s_update_check: QtCore.Signal = QtCore.Signal(bool)
    s_update_show: QtCore.Signal = QtCore.Signal(bool, bool, object)
    s_queue_download_item_downloading: QtCore.Signal = QtCore.Signal(object)
    s_queue_download_item_finished: QtCore.Signal = QtCore.Signal(object)
    s_queue_download_item_failed: QtCore.Signal = QtCore.Signal(object)
    s_queue_download_item_skipped: QtCore.Signal = QtCore.Signal(object)
    converter_ansi_html: Ansi2HTMLConverter
    dialog_preferences: DialogPreferences | None = None

    def __init__(self, tidal: Tidal | None = None) -> None:
        """Initialize the main window and all components.

        Args:
            tidal (Tidal | None): Optional Tidal session object.
        """
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("TIDAL Downloader Next Generation!")

        # Logging redirect.
        XStream.stdout().messageWritten.connect(self._log_output)
        # XStream.stderr().messageWritten.connect(self._log_output)

        self.settings = Settings()

        self._init_threads()
        self._init_gui()
        self._init_tree_results_model(self.model_tr_results)
        self._init_tree_results(self.tr_results, self.model_tr_results)
        self._init_tree_lists(self.tr_lists_user)
        self._init_tree_queue(self.tr_queue_download)
        self._init_info()
        self._init_progressbar()
        self._populate_quality(self.cb_quality_audio, Quality)
        self._populate_quality(self.cb_quality_video, QualityVideo)
        self._populate_search_types(self.cb_search_type, SearchTypes)
        self.apply_settings(self.settings)
        self._init_signals()
        self._init_buttons()
        self.init_tidal(tidal)

        logger_gui.debug("All setup.")

    def _init_gui(self) -> None:
        """Initialize GUI-specific variables and state."""
        self.setGeometry(
            self.settings.data.window_x,
            self.settings.data.window_y,
            self.settings.data.window_w,
            self.settings.data.window_h,
        )
        self.spinners: dict[QtWidgets.QWidget, QtWaitingSpinner] = {}
        self.converter_ansi_html: Ansi2HTMLConverter = Ansi2HTMLConverter()

    def init_tidal(self, tidal: Tidal | None = None):
        """Initialize Tidal session and handle login flow.

        Args:
            tidal (Tidal, optional): Existing Tidal session. Defaults to None.
        """
        result: bool = False

        if tidal:
            self.tidal = tidal
            result = True
        else:
            self.tidal = Tidal(self.settings)
            result = self.tidal.login_token()

            if not result:
                hint: str = "After you have finished the TIDAL login via web browser click the 'OK' button."

                while not result:
                    link_login: LinkLogin = self.tidal.session.get_link_login()
                    expires_in = int(link_login.expires_in) if hasattr(link_login, "expires_in") else 0
                    d_login: DialogLogin = DialogLogin(
                        url_login=link_login.verification_uri_complete,
                        hint=hint,
                        expires_in=expires_in,
                        parent=self,
                    )

                    if d_login.return_code == 1:
                        try:
                            self.tidal.session.process_link_login(link_login, until_expiry=False)
                            self.tidal.login_finalize()

                            result = True
                            logger_gui.info("Login successful. Have fun!")
                        except (HTTPError, Exception):
                            hint = "Something was wrong with your redirect url. Please try again!"
                            logger_gui.warning("Login not successful. Try again...")
                    else:
                        # If user has pressed cancel.
                        sys.exit(1)

        if result:
            self._init_dl()
            self.thread_it(self.tidal_user_lists)

    def _init_threads(self):
        """Initialize thread pool and start background workers."""
        self.threadpool = QtCore.QThreadPool()
        self.thread_it(self.watcher_queue_download)

    def _init_dl(self):
        """Initialize Download object and related progress bars."""
        # Init `Download` object.
        data_pb: ProgressBars = ProgressBars(
            item=self.s_item_advance,
            list_item=self.s_list_advance,
            item_name=self.s_item_name,
            list_name=self.s_list_name,
        )
        progress: Progress = Progress()
        handling_app: HandlingApp = HandlingApp()
        self.dl = Download(
            tidal_obj=self.tidal,
            skip_existing=self.tidal.settings.data.skip_existing,
            path_base=self.settings.data.download_base_path,
            fn_logger=logger_gui,
            progress_gui=data_pb,
            progress=progress,
            event_abort=handling_app.event_abort,
            event_run=handling_app.event_run,
        )

    def _init_progressbar(self):
        """Initialize and add progress bars to the status bar."""
        self.pb_list = QtWidgets.QProgressBar()
        self.pb_item = QtWidgets.QProgressBar()
        pbs = [self.pb_list, self.pb_item]

        for pb in pbs:
            pb.setRange(0, 100)
            # self.pb_progress.setVisible()
            self.statusbar.addPermanentWidget(pb)

    def _init_info(self):
        """Set default album cover image in the GUI."""
        path_image: str = resource_path("tidal_dl_ng/ui/default_album_image.png")

        self.l_pm_cover.setPixmap(QtGui.QPixmap(path_image))

    def on_progress_reset(self):
        """Reset progress bars to zero."""
        self.pb_list.setValue(0)
        self.pb_item.setValue(0)

    def on_statusbar_message(self, data: StatusbarMessage):
        """Show a message in the status bar.

        Args:
            data (StatusbarMessage): Message and timeout.
        """
        self.statusbar.showMessage(data.message, data.timeout)

    def _log_output(self, text: str) -> None:
        """Redirect log output to the debug text area.

        Args:
            text (str): Log message.
        """
        cursor: QtGui.QTextCursor = self.te_debug.textCursor()
        html = self.converter_ansi_html.convert(text)

        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertHtml(html)
        self.te_debug.setTextCursor(cursor)
        self.te_debug.ensureCursorVisible()

    def _populate_quality(self, ui_target: QtWidgets.QComboBox, options: Iterable[Any]) -> None:
        """Populate a combo box with quality options.

        Args:
            ui_target (QComboBox): Target combo box.
            options (Iterable): Enum of quality options.
        """
        for item in options:
            ui_target.addItem(item.name, item)

    def _populate_search_types(self, ui_target: QtWidgets.QComboBox, options: Iterable[Any]) -> None:
        """Populate a combo box with search type options.

        Args:
            ui_target (QComboBox): Target combo box.
            options (Iterable): Enum of search types.
        """
        for item in options:
            if item:
                ui_target.addItem(item.__name__, item)

        self.cb_search_type.setCurrentIndex(2)

    def handle_filter_activated(self) -> None:
        """Handle activation of filter headers in the results tree."""
        header = self.tr_results.header()
        filters: list[tuple[int, str]] = []
        for i in range(header.count()):
            text: str = header.filter_text(i)

            if text:
                filters.append((i, text))

        proxy_model: HumanProxyModel = self.tr_results.model()
        proxy_model.filters = filters

    def _init_tree_results(self, tree: QtWidgets.QTreeView, model: QtGui.QStandardItemModel) -> None:
        """Initialize the results tree view and its model.

        Args:
            tree (QTreeView): The tree view widget.
            model (QStandardItemModel): The model for the tree.
        """
        header: FilterHeader = FilterHeader(tree)
        self.proxy_tr_results: HumanProxyModel = HumanProxyModel(self)

        tree.setHeader(header)
        tree.setModel(model)
        self.proxy_tr_results.setSourceModel(model)
        tree.setModel(self.proxy_tr_results)
        header.set_filter_boxes(model.columnCount())
        header.filter_activated.connect(self.handle_filter_activated)
        ## Styling
        tree.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)
        tree.setColumnHidden(1, True)
        normal_width = max(150, (self.width() * 0.13))  # 12% for normal fields
        narrow_width = max(90, (self.width() * 0.06))  # 6% for shorter fields
        skinny_width = max(60, (self.width() * 0.03))  # 3% for very short fields
        tree.setColumnWidth(2, normal_width)  # artist
        tree.setColumnWidth(3, normal_width)  # title
        tree.setColumnWidth(4, normal_width)  # album
        tree.setColumnWidth(5, skinny_width)  # duration
        tree.setColumnWidth(6, narrow_width)  # quality
        tree.setColumnWidth(7, narrow_width)  # date
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        # Connect the contextmenu
        tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        tree.customContextMenuRequested.connect(self.menu_context_tree_results)

    def _init_tree_results_model(self, model: QtGui.QStandardItemModel) -> None:
        """Initialize the model for the results tree view.

        Args:
            model (QStandardItemModel): The model to initialize.
        """
        labels_column: list[str] = ["#", "obj", "Artist", "Title", "Album", "Duration", "Quality", "Date"]

        model.setColumnCount(len(labels_column))
        model.setRowCount(0)
        model.setHorizontalHeaderLabels(labels_column)

    def _init_tree_queue(self, tree: QtWidgets.QTableWidget) -> None:
        """Initialize the download queue table widget.

        Args:
            tree (QTableWidget): The table widget.
        """
        tree.setColumnHidden(1, True)
        tree.setColumnWidth(2, 200)

        header = tree.header()

        if hasattr(header, "setSectionResizeMode"):
            header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        tree.customContextMenuRequested.connect(self.menu_context_queue_download)

    def tidal_user_lists(self) -> None:
        """Fetch and emit user playlists, mixes, and favorites from Tidal."""
        # Start loading spinner
        self.s_spinner_start.emit(self.tr_lists_user)
        self.s_pb_reload_status.emit(False)

        user_all: dict[str, list] = user_media_lists(self.tidal.session)

        self.s_populate_tree_lists.emit(user_all)

    def on_populate_tree_lists(self, user_lists: dict[str, list]) -> None:
        """Populate the user lists tree with playlists, mixes, and favorites.

        Args:
            user_lists (dict[str, list]): Dictionary with 'playlists' (Folder/Playlist) and 'mixes' lists.
        """
        twi_playlists: QtWidgets.QTreeWidgetItem = self.tr_lists_user.findItems(
            TidalLists.Playlists, QtCore.Qt.MatchExactly, 0
        )[0]
        twi_mixes: QtWidgets.QTreeWidgetItem = self.tr_lists_user.findItems(
            TidalLists.Mixes, QtCore.Qt.MatchExactly, 0
        )[0]
        twi_favorites: QtWidgets.QTreeWidgetItem = self.tr_lists_user.findItems(
            TidalLists.Favorites, QtCore.Qt.MatchExactly, 0
        )[0]

        # Remove all children if present
        for twi in [twi_playlists, twi_mixes]:
            for i in reversed(range(twi.childCount())):
                twi.removeChild(twi.child(i))

        # Populate playlists (including folders)
        for item in user_lists.get("playlists", []):
            if isinstance(item, Folder):
                twi_child = QtWidgets.QTreeWidgetItem(twi_playlists)
                name: str = f"📁 {item.name}"
                info: str = f"({item.total_number_of_items} items)" if item.total_number_of_items else ""
                twi_child.setText(0, name)
                set_user_list_media(twi_child, item)
                twi_child.setText(2, info)

                # Add disabled dummy child to show expansion arrow
                dummy_child = QtWidgets.QTreeWidgetItem(twi_child)
                dummy_child.setDisabled(True)
            elif isinstance(item, UserPlaylist | Playlist):
                twi_child = QtWidgets.QTreeWidgetItem(twi_playlists)
                name: str = item.name if getattr(item, "name", None) is not None else ""
                description: str = f" {item.description}" if item.description else ""
                info: str = f"({item.num_tracks + item.num_videos} Tracks){description}"
                twi_child.setText(0, name)
                set_user_list_media(twi_child, item)
                twi_child.setText(2, info)

        # Populate mixes
        for item in user_lists.get("mixes", []):
            if isinstance(item, Mix):
                twi_child = QtWidgets.QTreeWidgetItem(twi_mixes)
                name: str = item.title
                info: str = item.sub_title
                twi_child.setText(0, name)
                set_user_list_media(twi_child, item)
                twi_child.setText(2, info)

        # Remove all children from favorites to avoid duplication
        for i in reversed(range(twi_favorites.childCount())):
            twi_favorites.removeChild(twi_favorites.child(i))

        # Populate static favorites
        for key, favorite in FAVORITES.items():
            twi_child = QtWidgets.QTreeWidgetItem(twi_favorites)
            name: str = favorite["name"]
            info: str = ""

            twi_child.setText(0, name)
            set_user_list_media(twi_child, key)
            twi_child.setText(2, info)

        # Stop load spinner
        self.s_spinner_stop.emit()
        self.s_pb_reload_status.emit(True)

    def _init_tree_lists(self, tree: QtWidgets.QTreeWidget) -> None:
        """Initialize the user lists tree widget.

        Args:
            tree (QTreeWidget): The tree widget.
        """
        # Adjust Tree.
        tree.setColumnWidth(0, 200)
        tree.setColumnHidden(1, True)
        tree.setColumnWidth(2, 300)
        tree.expandAll()

        # Connect the contextmenu
        tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        tree.customContextMenuRequested.connect(self.menu_context_tree_lists)

    def on_update_check(self, on_startup: bool = True) -> None:
        """Check for application updates and emit update signals.

        Args:
            on_startup (bool, optional): Whether this is called on startup. Defaults to True.
        """
        is_available, info = update_available()

        if (on_startup and is_available) or not on_startup:
            self.s_update_show.emit(True, is_available, info)

    def apply_settings(self, settings: Settings) -> None:
        """Apply user settings to the GUI.

        Args:
            settings (Settings): The settings object.
        """
        quality_audio = getattr(getattr(settings, "data", None), "quality_audio", 1)
        quality_video = getattr(getattr(settings, "data", None), "quality_video", 0)
        elements = [
            {"element": self.cb_quality_audio, "setting": quality_audio, "default_id": 1},
            {"element": self.cb_quality_video, "setting": quality_video, "default_id": 0},
        ]

        for item in elements:
            idx = item["element"].findData(item["setting"])

            if idx > -1:
                item["element"].setCurrentIndex(idx)
            else:
                item["element"].setCurrentIndex(item["default_id"])

    def on_spinner_start(self, parent: QtWidgets.QWidget) -> None:
        """Start a loading spinner on the given parent widget.

        Args:
            parent (QWidget): The parent widget.
        """
        # Stop any existing spinner for this parent
        if parent in self.spinners:
            spinner = self.spinners[parent]

            spinner.stop()
            spinner.deleteLater()
            del self.spinners[parent]

        # Create and start a new spinner for this parent
        spinner = QtWaitingSpinner(parent, True, True)

        spinner.setColor(QtGui.QColor(255, 255, 255))
        spinner.start()

        self.spinners[parent] = spinner

    def on_spinner_stop(self) -> None:
        """Stop all active loading spinners."""
        # Stop all spinners
        for spinner in list(self.spinners.values()):
            spinner.stop()
            spinner.deleteLater()

        self.spinners.clear()

    def menu_context_tree_lists(self, point: QtCore.QPoint) -> None:
        """Show context menu for user lists tree.

        Args:
            point (QPoint): The point where the menu is requested.
        """
        # Infos about the node selected.
        index = self.tr_lists_user.indexAt(point)

        # Do not open menu if something went wrong or a parent node is clicked.
        if not index.isValid() or not index.parent().data():
            return

        # Get the media item to determine type
        item = self.tr_lists_user.itemAt(point)
        media = get_user_list_media_item(item)

        # We build the menu.
        menu = QtWidgets.QMenu()

        if isinstance(media, Folder):
            # Folder-specific menu items
            menu.addAction(
                "Download All Playlists in Folder", lambda: self.thread_it(self.on_download_folder_playlists, point)
            )
            menu.addAction(
                "Download All Albums from Folder", lambda: self.thread_it(self.on_download_folder_albums, point)
            )
        elif isinstance(media, str):
            # Favorites items (stored as string keys like "fav_tracks", "fav_albums")
            menu.addAction("Download All Items", lambda: self.thread_it(self.on_download_favorites, point))
            menu.addAction(
                "Download All Albums from Items", lambda: self.thread_it(self.on_download_albums_from_favorites, point)
            )
        else:
            # Playlist/Mix menu items (existing)
            menu.addAction("Download Playlist", lambda: self.thread_download_list_media(point))
            menu.addAction(
                "Download All Albums in Playlist",
                lambda: self.thread_it(self.on_download_all_albums_from_playlist, point),
            )
            menu.addAction("Copy Share URL", lambda: self.on_copy_url_share(self.tr_lists_user, point))

        menu.exec(self.tr_lists_user.mapToGlobal(point))

    def menu_context_tree_results(self, point: QtCore.QPoint) -> None:
        """Show context menu for results tree.

        Args:
            point (QPoint): The point where the menu is requested.
        """
        # Infos about the node selected.
        index = self.tr_results.indexAt(point)

        # Do not open menu if something went wrong or a parent node is clicked.
        if not index.isValid():
            return

        # Get the media item at this point
        media = get_results_media_item(index, self.proxy_tr_results, self.model_tr_results)

        # We build the menu.
        menu = QtWidgets.QMenu()

        # Add "Download Full Album" option if it's a track or video with an album
        if isinstance(media, Track | Video) and hasattr(media, "album") and media.album:
            menu.addAction("Download Full Album", lambda: self.thread_download_album_from_track(point))

        menu.addAction("Copy Share URL", lambda: self.on_copy_url_share(self.tr_results, point))

        menu.exec(self.tr_results.mapToGlobal(point))

    def menu_context_queue_download(self, point: QtCore.QPoint) -> None:
        """Show context menu for download queue.

        Args:
            point (QPoint): The point where the menu is requested.
        """
        # Get the item at this point
        item = self.tr_queue_download.itemAt(point)

        if not item:
            return

        # Build the menu
        menu = QtWidgets.QMenu()

        # Show remove option for waiting items
        status = item.text(0)
        if status == QueueDownloadStatus.Waiting:
            menu.addAction("🗑️ Remove from Queue", lambda: self.on_queue_download_remove_item(item))

        if menu.isEmpty():
            return

        menu.exec(self.tr_queue_download.mapToGlobal(point))

    def on_queue_download_remove_item(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Remove a specific item from the download queue.

        Args:
            item (QTreeWidgetItem): The item to remove.
        """
        index = self.tr_queue_download.indexOfTopLevelItem(item)
        if index >= 0:
            self.tr_queue_download.takeTopLevelItem(index)
            logger_gui.info("Removed item from download queue")

    def thread_download_list_media(self, point: QtCore.QPoint) -> None:
        """Start download of a list media item in a thread.

        Args:
            point (QPoint): The point in the tree.
        """
        self.thread_it(self.on_download_list_media, point)

    def on_download_all_albums_from_playlist(self, point: QtCore.QPoint) -> None:
        """Download all unique albums from tracks in a playlist.

        Args:
            point (QPoint): The point in the tree where the playlist was right-clicked.
        """
        try:
            # Get and validate the playlist
            item = self.tr_lists_user.itemAt(point)
            media_list = get_user_list_media_item(item)

            if not isinstance(media_list, Playlist | UserPlaylist | Mix):
                logger_gui.error("Please select a playlist or mix.")
                return

            # Get all items from the playlist
            logger_gui.info(f"Fetching all tracks from: {media_list.name}")
            media_items = items_results_all(media_list)

            # Extract unique album IDs from tracks
            album_ids = self._extract_album_ids_from_tracks(media_items)

            if not album_ids:
                logger_gui.warning("No albums found in this playlist.")
                return

            logger_gui.info(f"Found {len(album_ids)} unique albums. Loading with rate limiting...")

            # Load albums with rate limiting
            albums_dict = self._load_albums_with_rate_limiting(album_ids)

            if not albums_dict:
                logger_gui.error("Failed to load any albums from playlist.")
                return

            # Prepare and queue albums
            self._queue_loaded_albums(albums_dict)

            # Show confirmation
            message = f"Added {len(albums_dict)} albums to download queue"
            self.s_statusbar_message.emit(StatusbarMessage(message=message, timeout=3000))
            logger_gui.info(message)

        except Exception as e:
            error_msg = f"Error downloading albums from playlist: {e!s}"
            logger_gui.error(error_msg)
            self.s_statusbar_message.emit(StatusbarMessage(message=error_msg, timeout=3000))

    def _extract_album_ids_from_tracks(self, media_items: list) -> dict[int, Album]:
        """Extract unique album IDs from a list of media items.

        Args:
            media_items (list): List of media items (tracks/videos) from a playlist.

        Returns:
            dict[int, Album]: Dictionary mapping album IDs to album stub objects.
        """
        album_ids = {}

        for media_item in media_items:
            if not isinstance(media_item, Track | Video):
                continue

            if not hasattr(media_item, "album") or not media_item.album:
                continue

            try:
                # Access album.id carefully as it might trigger API calls
                album_id = media_item.album.id
                if album_id:
                    album_ids[album_id] = media_item.album
            except Exception as e:
                logger_gui.debug(f"Skipping track with unavailable album: {e!s}")
                continue

        return album_ids

    def _load_albums_with_rate_limiting(self, album_ids: dict[int, Album]) -> dict[int, Album]:
        """Load full album objects with rate limiting to prevent API throttling.

        Args:
            album_ids (dict[int, Album]): Dictionary of album IDs to album stubs.

        Returns:
            dict[int, Album]: Dictionary of successfully loaded full album objects.
        """
        albums_dict = {}
        batch_size = self.settings.data.api_rate_limit_batch_size
        delay_sec = self.settings.data.api_rate_limit_delay_sec

        for idx, album_id in enumerate(album_ids.keys(), start=1):
            try:
                # Add delay every N albums to avoid rate limiting
                if idx > 1 and (idx - 1) % batch_size == 0:
                    logger_gui.info(f"🛑 RATE LIMITING: Processed {idx - 1} albums, pausing for {delay_sec} seconds...")
                    time.sleep(delay_sec)

                # Check session validity before making API calls
                if not self.tidal.session.check_login():
                    logger_gui.error("Session expired. Please restart the application and login again.")
                    return albums_dict

                # Reload full album object
                album = self.tidal.session.album(album_id)
                albums_dict[album.id] = album
                logger_gui.debug(f"Loaded album {idx}/{len(album_ids)}: {name_builder_artist(album)} - {album.name}")

            except Exception as e:
                if not self._handle_album_load_error(e, album_id):
                    return albums_dict
                continue

        logger_gui.info(f"Successfully loaded {len(albums_dict)} albums.")
        return albums_dict

    def _handle_album_load_error(self, error: Exception, album_id: int) -> bool:
        """Handle errors that occur when loading an album.

        Args:
            error (Exception): The exception that was raised.
            album_id (int): The ID of the album that failed to load.

        Returns:
            bool: True if processing should continue, False if it should stop.
        """
        # Check for OAuth/authentication errors using Tidal class method
        if self.tidal.is_authentication_error(error):
            error_msg = str(error)
            logger_gui.error(f"Authentication error: {error_msg}")
            logger_gui.error("Your session has expired. Please restart the application and login again.")
            self.s_statusbar_message.emit(
                StatusbarMessage(message="Session expired - please restart and login", timeout=5000)
            )
            return False

        logger_gui.warning(f"Failed to load album {album_id}: {error!s}")
        logger_gui.info(
            "Note: Some albums may be unavailable due to region restrictions or removal from TIDAL. This is normal."
        )
        return True

    def _queue_loaded_albums(self, albums_dict: dict[int, Album]) -> None:
        """Prepare and add loaded albums to the download queue.

        Args:
            albums_dict (dict[int, Album]): Dictionary of successfully loaded albums.
        """
        logger_gui.info(f"Preparing queue items for {len(albums_dict)} albums...")

        queue_items = []
        for album in albums_dict.values():
            queue_dl_item = self.media_to_queue_download_model(album)
            if queue_dl_item:
                queue_items.append((queue_dl_item, album))
                logger_gui.debug(f"Prepared: {name_builder_artist(album)} - {album.name}")

        # Add all items to queue
        logger_gui.info(f"Adding {len(queue_items)} albums to queue...")
        for queue_dl_item, album in queue_items:
            self.queue_download_media(queue_dl_item)
            logger_gui.info(f"Added: {name_builder_artist(album)} - {album.name}")

    def on_copy_url_share(
        self, tree_target: QtWidgets.QTreeWidget | QtWidgets.QTreeView, point: QtCore.QPoint = None
    ) -> None:
        """Copy the share URL of a media item to the clipboard.

        Args:
            tree_target (QTreeWidget | QTreeView): The tree widget.
            point (QPoint, optional): The point in the tree. Defaults to None.
        """
        if isinstance(tree_target, QtWidgets.QTreeWidget):

            item: QtWidgets.QTreeWidgetItem = tree_target.itemAt(point)
            media: Album | Artist | Mix | Playlist = get_user_list_media_item(item)
        else:
            index: QtCore.QModelIndex = tree_target.indexAt(point)
            media: Track | Video | Album | Artist | Mix | Playlist = get_results_media_item(
                index, self.proxy_tr_results, self.model_tr_results
            )

        clipboard = QtWidgets.QApplication.clipboard()
        url_share = media.share_url if hasattr(media, "share_url") else "No share URL available."

        clipboard.clear()
        clipboard.setText(url_share)

    def on_download_list_media(self, point: QtCore.QPoint | None = None) -> None:
        """Download all media items in a selected list.

        Args:
            point (QPoint | None, optional): The point in the tree. Defaults to None.
        """
        items: list[QtWidgets.QTreeWidgetItem] = []

        if point:
            items = [self.tr_lists_user.itemAt(point)]
        else:
            items = self.tr_lists_user.selectedItems()

            if len(items) == 0:
                logger_gui.error("Please select a mix or playlist first.")

        for item in items:
            media = get_user_list_media_item(item)
            queue_dl_item: QueueDownloadItem | None = self.media_to_queue_download_model(media)

            if queue_dl_item:
                self.queue_download_media(queue_dl_item)

    def on_download_folder_playlists(self, point: QtCore.QPoint) -> None:
        """Download all playlists in a folder.

        Args:
            point (QPoint): The point in the tree where the folder was right-clicked.
        """
        try:
            # Get and validate the folder
            item = self.tr_lists_user.itemAt(point)
            media = get_user_list_media_item(item)

            if not isinstance(media, Folder):
                logger_gui.error("Please select a folder.")
                return

            # Fetch all playlists in the folder
            logger_gui.info(f"Fetching playlists from folder: {media.name}")
            playlists = self._get_folder_playlists(media)

            if not playlists:
                logger_gui.info(f"No playlists found in folder: {media.name}")
                return

            # Queue each playlist for download
            logger_gui.info(f"Queueing {len(playlists)} playlists from folder: {media.name}")

            for playlist in playlists:
                queue_dl_item: QueueDownloadItem | None = self.media_to_queue_download_model(playlist)

                if queue_dl_item:
                    self.queue_download_media(queue_dl_item)

            logger_gui.info(f"✅ Successfully queued {len(playlists)} playlists from folder: {media.name}")

        except Exception as e:
            logger_gui.exception(f"Error downloading playlists from folder: {e}")
            logger_gui.error("Failed to download playlists from folder. See log for details.")

    def on_download_folder_albums(self, point: QtCore.QPoint) -> None:
        """Download all unique albums from all playlists in a folder.

        Args:
            point (QPoint): The point in the tree where the folder was right-clicked.
        """
        try:
            # Get and validate the folder
            item = self.tr_lists_user.itemAt(point)
            media = get_user_list_media_item(item)

            if not isinstance(media, Folder):
                logger_gui.error("Please select a folder.")
                return

            # Fetch all playlists in the folder
            logger_gui.info(f"Fetching playlists from folder: {media.name}")
            playlists = self._get_folder_playlists(media)

            if not playlists:
                logger_gui.info(f"No playlists found in folder: {media.name}")
                return

            logger_gui.info(f"Found {len(playlists)} playlists in folder: {media.name}")

            # Collect all tracks from all playlists
            all_tracks: list[Track] = []

            for playlist in playlists:
                try:
                    tracks = self._get_playlist_tracks(playlist)
                    all_tracks.extend(tracks)
                    logger_gui.debug(f"Collected {len(tracks)} tracks from playlist: {playlist.name}")
                except Exception as e:
                    logger_gui.error(f"Error getting tracks from playlist '{playlist.name}': {e}")
                    continue

            if not all_tracks:
                logger_gui.info(f"No tracks found in folder playlists: {media.name}")
                return

            logger_gui.info(f"Collected {len(all_tracks)} total tracks from all playlists")

            # Extract unique album IDs
            album_ids = self._extract_album_ids_from_tracks(all_tracks)
            logger_gui.info(f"Found {len(album_ids)} unique albums across all playlists in folder: {media.name}")

            if not album_ids:
                logger_gui.info("No albums found to download.")
                return

            # Load full album objects with rate limiting
            albums_dict = self._load_albums_with_rate_limiting(album_ids)

            if not albums_dict:
                logger_gui.error("Failed to load any albums.")
                return

            # Queue the albums for download
            self._queue_loaded_albums(albums_dict)

            logger_gui.info(f"✅ Successfully queued {len(albums_dict)} unique albums from folder: {media.name}")

        except Exception as e:
            logger_gui.exception(f"Error downloading albums from folder: {e}")
            logger_gui.error("Failed to download albums from folder. See log for details.")

    def on_download_favorites(self, point: QtCore.QPoint) -> None:
        """Download all items from a Favorites category.

        Args:
            point (QPoint): The point in the tree where the favorites item was right-clicked.
        """
        try:
            # Get and validate the favorites item
            item = self.tr_lists_user.itemAt(point)
            media = get_user_list_media_item(item)

            if not isinstance(media, str):
                logger_gui.error("Please select a favorites category.")
                return

            # Get the favorites category name for logging
            favorite_name = FAVORITES.get(media, {}).get("name", media)
            logger_gui.info(f"Fetching all items from favorites: {favorite_name}")

            # Use the factory to get the appropriate favorites function
            favorite_function = favorite_function_factory(self.tidal, media)

            # Fetch all items from this favorites category
            media_items = favorite_function()

            if not media_items:
                logger_gui.info(f"No items found in favorites: {favorite_name}")
                return

            logger_gui.info(f"Found {len(media_items)} items in favorites: {favorite_name}")

            # Queue each item for download
            queued_count = 0

            for media_item in media_items:
                queue_dl_item: QueueDownloadItem | None = self.media_to_queue_download_model(media_item)

                if queue_dl_item:
                    self.queue_download_media(queue_dl_item)
                    queued_count += 1

            logger_gui.info(f"✅ Successfully queued {queued_count} items from favorites: {favorite_name}")

        except Exception as e:
            logger_gui.exception(f"Error downloading favorites: {e}")
            logger_gui.error("Failed to download favorites. See log for details.")

    def _download_albums_from_favorites_albums(self, media_items: list, favorite_name: str) -> None:
        """Download albums from favorite albums list.

        Args:
            media_items (list): List of favorite albums.
            favorite_name (str): Name of the favorites category for logging.
        """
        logger_gui.info(f"Queueing {len(media_items)} albums from favorites: {favorite_name}")
        albums_dict = {album.id: album for album in media_items if isinstance(album, Album) and album.id}
        self._queue_loaded_albums(albums_dict)
        logger_gui.info(f"✅ Successfully queued {len(albums_dict)} albums from favorites: {favorite_name}")

    def _download_albums_from_favorites_artists(self, media_items: list, favorite_name: str) -> None:
        """Download albums from favorite artists list.

        Args:
            media_items (list): List of favorite artists.
            favorite_name (str): Name of the favorites category for logging.
        """
        logger_gui.info(f"Fetching albums from {len(media_items)} artists...")
        all_albums = {}

        for artist in media_items:
            if isinstance(artist, Artist):
                try:
                    artist_albums = items_results_all(artist)
                    for album in artist_albums:
                        if isinstance(album, Album) and album.id:
                            all_albums[album.id] = album
                    logger_gui.debug(f"Found {len(artist_albums)} albums from artist: {artist.name}")
                except Exception as e:
                    logger_gui.error(f"Error getting albums from artist '{artist.name}': {e}")
                    continue

        if not all_albums:
            logger_gui.info("No albums found from favorite artists.")
            return

        logger_gui.info(f"Found {len(all_albums)} unique albums from favorite artists")
        self._queue_loaded_albums(all_albums)
        logger_gui.info(f"✅ Successfully queued {len(all_albums)} albums from favorites: {favorite_name}")

    def _download_albums_from_favorites_tracks(self, media_items: list, favorite_name: str) -> None:
        """Download albums from favorite tracks/videos/mixes list.

        Args:
            media_items (list): List of favorite tracks/videos/mixes.
            favorite_name (str): Name of the favorites category for logging.
        """
        logger_gui.info("Extracting albums from tracks...")
        album_ids = self._extract_album_ids_from_tracks(media_items)

        if not album_ids:
            logger_gui.info(f"No albums found in favorites: {favorite_name}")
            return

        logger_gui.info(f"Found {len(album_ids)} unique albums. Loading with rate limiting...")

        # Load full album objects with rate limiting
        albums_dict = self._load_albums_with_rate_limiting(album_ids)

        if not albums_dict:
            logger_gui.error("Failed to load any albums from favorites.")
            return

        # Queue the albums for download
        self._queue_loaded_albums(albums_dict)
        logger_gui.info(f"✅ Successfully queued {len(albums_dict)} unique albums from favorites: {favorite_name}")

    def on_download_albums_from_favorites(self, point: QtCore.QPoint) -> None:
        """Download all unique albums from items in a Favorites category.

        Args:
            point (QPoint): The point in the tree where the favorites item was right-clicked.
        """
        try:
            # Get and validate the favorites item
            item = self.tr_lists_user.itemAt(point)
            media = get_user_list_media_item(item)

            if not isinstance(media, str):
                logger_gui.error("Please select a favorites category.")
                return

            # Get the favorites category name for logging
            favorite_name = FAVORITES.get(media, {}).get("name", media)
            logger_gui.info(f"Fetching all items from favorites: {favorite_name}")

            # Use the factory to get the appropriate favorites function
            favorite_function = favorite_function_factory(self.tidal, media)

            # Fetch all items from this favorites category
            media_items = favorite_function()

            if not media_items:
                logger_gui.info(f"No items found in favorites: {favorite_name}")
                return

            logger_gui.info(f"Found {len(media_items)} items in favorites: {favorite_name}")

            # Delegate to appropriate handler based on favorites type
            if media == "fav_albums":
                self._download_albums_from_favorites_albums(media_items, favorite_name)
            elif media == "fav_artists":
                self._download_albums_from_favorites_artists(media_items, favorite_name)
            else:
                self._download_albums_from_favorites_tracks(media_items, favorite_name)

        except Exception as e:
            logger_gui.exception(f"Error downloading albums from favorites: {e}")
            logger_gui.error("Failed to download albums from favorites. See log for details.")

    def search_populate_results(self, query: str, type_media: Any) -> None:
        """Populate the results tree with search results.

        Args:
            query (str): The search query.
            type_media (SearchTypes): The type of media to search for.
        """
        results: list[ResultItem] = self.search(query, [type_media])

        self.populate_tree_results(results)

    def populate_tree_results(self, results: list[ResultItem], parent: QtGui.QStandardItem | None = None) -> None:
        """Populate the results tree with ResultItem objects.

        Args:
            results (list[ResultItem]): The results to display.
            parent (QStandardItem, optional): Parent item for nested results. Defaults to None.
        """
        if not parent:
            self.model_tr_results.removeRows(0, self.model_tr_results.rowCount())

        # Count how many digits the list length has,
        count_digits: int = int(math.log10(len(results) if results else 1)) + 1

        for item in results:
            child: tuple = self.populate_tree_result_child(item=item, index_count_digits=count_digits)

            if parent:
                parent.appendRow(child)
            else:
                self.s_tr_results_add_top_level_item.emit(child)

    def populate_tree_result_child(self, item: ResultItem, index_count_digits: int) -> Sequence[QtGui.QStandardItem]:
        """Create a row of QStandardItems for a ResultItem.

        Args:
            item (ResultItem): The result item.
            index_count_digits (int): Number of digits for index formatting.

        Returns:
            Sequence[QStandardItem]: The row of items.
        """
        duration: str = ""

        # TODO: Duration needs to be calculated later to properly fill with zeros.
        if item.duration_sec > -1:
            # Format seconds to mm:ss.
            m, s = divmod(item.duration_sec, 60)
            duration: str = f"{m:02d}:{s:02d}"

        # Since sorting happens only by string, we need to pad the index and add 1 (to avoid start at 0)
        index: str = str(item.position + 1).zfill(index_count_digits)

        # Populate child
        child_index: QtGui.QStandardItem = QtGui.QStandardItem(index)
        # TODO: Move to own method
        child_obj: QtGui.QStandardItem = QtGui.QStandardItem()

        child_obj.setData(item.obj, QtCore.Qt.ItemDataRole.UserRole)
        # set_results_media(child, item.obj)

        child_artist: QtGui.QStandardItem = QtGui.QStandardItem(item.artist)
        child_title: QtGui.QStandardItem = QtGui.QStandardItem(item.title)
        child_album: QtGui.QStandardItem = QtGui.QStandardItem(item.album)
        child_duration: QtGui.QStandardItem = QtGui.QStandardItem(duration)
        child_quality: QtGui.QStandardItem = QtGui.QStandardItem(item.quality)
        child_date: QtGui.QStandardItem = QtGui.QStandardItem(
            item.date_user_added if item.date_user_added != "" else item.date_release
        )

        if isinstance(item.obj, Mix | Playlist | Album | Artist):
            # Add a disabled dummy child, so expansion arrow will appear. This Child will be replaced on expansion.
            child_dummy: QtGui.QStandardItem = QtGui.QStandardItem()

            child_dummy.setEnabled(False)
            child_index.appendRow(child_dummy)

        return (
            child_index,
            child_obj,
            child_artist,
            child_title,
            child_album,
            child_duration,
            child_quality,
            child_date,
        )

    def on_tr_results_add_top_level_item(self, item_child: Sequence[QtGui.QStandardItem]):
        """Add a top-level item to the results tree model.

        Args:
            item_child (Sequence[QStandardItem]): The row to add.
        """
        self.model_tr_results.appendRow(item_child)

    def on_settings_save(self) -> None:
        """Save settings and re-apply them to the GUI."""
        self.settings.save()
        self.apply_settings(self.settings)
        self._init_dl()

    def search(self, query: str, types_media: list[Any]) -> list[ResultItem]:
        """Perform a search and return a list of ResultItems.

        Args:
            query (str): The search query.
            types_media (list[Any]): The types of media to search for.

        Returns:
            list[ResultItem]: The search results.
        """
        query_clean: str = query.strip()

        # If a direct link was searched for, skip search and create the object from the link directly.
        if "http" in query_clean:
            query_clean: str = url_ending_clean(query_clean)
            media_type = get_tidal_media_type(query_clean)
            item_id = get_tidal_media_id(query_clean)

            try:
                media = instantiate_media(self.tidal.session, media_type, item_id)
            except Exception:
                logger_gui.error(f"Media not found (ID: {item_id}). Maybe it is not available anymore.")

                media = None

            result_search = {"direct": [media]}
        else:
            result_search: dict[str, list[SearchTypes]] = search_results_all(
                session=self.tidal.session, needle=query_clean, types_media=types_media
            )

        result: list[ResultItem] = []

        for _media_type, l_media in result_search.items():
            if isinstance(l_media, list):
                result = result + self.search_result_to_model(l_media)

        return result

    def search_result_to_model(self, items: list[SearchTypes]) -> list[ResultItem]:
        """Convert search results to ResultItem models.

        Args:
            items (list[SearchTypes]): List of search result items.

        Returns:
            list[ResultItem]: List of ResultItem models.
        """
        result: list[ResultItem] = []

        for idx, item in enumerate(items):
            result_item = self._to_result_item(idx, item)

            if result_item is not None:
                result.append(result_item)

        return result

    def _to_result_item(self, idx: int, item) -> ResultItem | None:
        """Helper to convert a single item to ResultItem, or None if not valid.

        Args:
            idx (int): Index of the item.
            item: The item to convert.

        Returns:
            ResultItem | None: The converted ResultItem or None if not valid.
        """
        if not item or (hasattr(item, "available") and not item.available):
            return None

        # Prepare common data
        explicit = " 🅴" if isinstance(item, Track | Video | Album) and item.explicit else ""
        date_user_added = (
            item.user_date_added.strftime("%Y-%m-%d_%H:%M") if getattr(item, "user_date_added", None) else ""
        )
        date_release = self._get_date_release(item)

        # Map item types to their conversion methods
        type_handlers = {
            Track: lambda: self._result_item_from_track(idx, item, explicit, date_user_added, date_release),
            Video: lambda: self._result_item_from_video(idx, item, explicit, date_user_added, date_release),
            Playlist: lambda: self._result_item_from_playlist(idx, item, date_user_added, date_release),
            Album: lambda: self._result_item_from_album(idx, item, explicit, date_user_added, date_release),
            Mix: lambda: self._result_item_from_mix(idx, item, date_user_added, date_release),
            Artist: lambda: self._result_item_from_artist(idx, item, date_user_added, date_release),
            Folder: lambda: self._result_item_from_folder(idx, item, date_user_added),
        }

        # Find and execute the appropriate handler
        for item_type, handler in type_handlers.items():
            if isinstance(item, item_type):
                return handler()

        return None

    def _get_date_release(self, item) -> str:
        """Get the release date string for an item.

        Args:
            item: The item to extract the release date from.

        Returns:
            str: The formatted release date or empty string.
        """
        if hasattr(item, "album") and item.album and getattr(item.album, "release_date", None):
            return item.album.release_date.strftime("%Y-%m-%d_%H:%M")

        if hasattr(item, "release_date") and item.release_date:
            return item.release_date.strftime("%Y-%m-%d_%H:%M")

        return ""

    def _result_item_from_track(
        self, idx: int, item, explicit: str, date_user_added: str, date_release: str
    ) -> ResultItem:
        """Create a ResultItem from a Track.

        Args:
            idx (int): Index of the item.
            item: The Track item.
            explicit (str): Explicit tag.
            date_user_added (str): Date user added.
            date_release (str): Release date.

        Returns:
            ResultItem: The constructed ResultItem.
        """

        final_quality = quality_audio_highest(item)
        if hasattr(item, "audio_modes") and AudioMode.dolby_atmos.value in item.audio_modes:
            final_quality = f"{final_quality} / Dolby Atmos"

        return ResultItem(
            position=idx,
            artist=name_builder_artist(item),
            title=f"{name_builder_title(item)}{explicit}",
            album=item.album.name,
            duration_sec=item.duration,
            obj=item,
            quality=final_quality,
            explicit=bool(item.explicit),
            date_user_added=date_user_added,
            date_release=date_release,
        )

    def _result_item_from_video(
        self, idx: int, item, explicit: str, date_user_added: str, date_release: str
    ) -> ResultItem:
        """Create a ResultItem from a Video.

        Args:
            idx (int): Index of the item.
            item: The Video item.
            explicit (str): Explicit tag.
            date_user_added (str): Date user added.
            date_release (str): Release date.

        Returns:
            ResultItem: The constructed ResultItem.
        """
        return ResultItem(
            position=idx,
            artist=name_builder_artist(item),
            title=f"{name_builder_title(item)}{explicit}",
            album=item.album.name if item.album else "",
            duration_sec=item.duration,
            obj=item,
            quality=item.video_quality,
            explicit=bool(item.explicit),
            date_user_added=date_user_added,
            date_release=date_release,
        )

    def _result_item_from_playlist(self, idx: int, item, date_user_added: str, date_release: str) -> ResultItem:
        """Create a ResultItem from a Playlist.

        Args:
            idx (int): Index of the item.
            item: The Playlist item.
            date_user_added (str): Date user added.
            date_release (str): Release date.

        Returns:
            ResultItem: The constructed ResultItem.
        """
        return ResultItem(
            position=idx,
            artist=", ".join(artist.name for artist in item.promoted_artists) if item.promoted_artists else "",
            title=item.name,
            album="",
            duration_sec=item.duration,
            obj=item,
            quality="",
            explicit=False,
            date_user_added=date_user_added,
            date_release=date_release,
        )

    def _result_item_from_album(
        self, idx: int, item, explicit: str, date_user_added: str, date_release: str
    ) -> ResultItem:
        """Create a ResultItem from an Album.

        Args:
            idx (int): Index of the item.
            item: The Album item.
            explicit (str): Explicit tag.
            date_user_added (str): Date user added.
            date_release (str): Release date.

        Returns:
            ResultItem: The constructed ResultItem.
        """
        return ResultItem(
            position=idx,
            artist=name_builder_artist(item),
            title="",
            album=f"{item.name}{explicit}",
            duration_sec=item.duration,
            obj=item,
            quality=quality_audio_highest(item),
            explicit=bool(item.explicit),
            date_user_added=date_user_added,
            date_release=date_release,
        )

    def _result_item_from_mix(self, idx: int, item, date_user_added: str, date_release: str) -> ResultItem:
        """Create a ResultItem from a Mix.

        Args:
            idx (int): Index of the item.
            item: The Mix item.
            date_user_added (str): Date user added.
            date_release (str): Release date.

        Returns:
            ResultItem: The constructed ResultItem.
        """
        return ResultItem(
            position=idx,
            artist=item.sub_title,
            title=item.title,
            album="",
            duration_sec=-1,  # TODO: Calculate total duration.
            obj=item,
            quality="",
            explicit=False,
            date_user_added=date_user_added,
            date_release=date_release,
        )

    def _result_item_from_artist(self, idx: int, item, date_user_added: str, date_release: str) -> ResultItem:
        """Create a ResultItem from an Artist.

        Args:
            idx (int): Index of the item.
            item: The Artist item.
            date_user_added (str): Date user added.
            date_release (str): Release date.

        Returns:
            ResultItem: The constructed ResultItem.
        """
        return ResultItem(
            position=idx,
            artist=item.name,
            title="",
            album="",
            duration_sec=-1,
            obj=item,
            quality="",
            explicit=False,
            date_user_added=date_user_added,
            date_release=date_release,
        )

    def _result_item_from_folder(self, idx: int, item: Folder, date_user_added: str) -> ResultItem:
        """Create a ResultItem from a Folder.

        Args:
            idx (int): Index of the item.
            item (Folder): The Folder item.
            date_user_added (str): Date user added.

        Returns:
            ResultItem: The constructed ResultItem.
        """
        total_items: int = item.total_number_of_items if hasattr(item, "total_number_of_items") else 0
        return ResultItem(
            position=idx,
            artist="",
            title=f"📁 {item.name} ({total_items} items)",
            album="",
            duration_sec=-1,
            obj=item,
            quality="",
            explicit=False,
            date_user_added=date_user_added,
            date_release="",
        )

    def media_to_queue_download_model(
        self, media: Artist | Track | Video | Album | Playlist | Mix
    ) -> QueueDownloadItem | bool:
        """Convert a media object to a QueueDownloadItem for the download queue.

        Args:
            media (Artist | Track | Video | Album | Playlist | Mix): The media object.

        Returns:
            QueueDownloadItem | bool: The queue item or False if not available.
        """
        result: QueueDownloadItem | False
        name: str = ""
        quality_audio: Quality = self.settings.data.quality_audio
        quality_video: QualityVideo = self.settings.data.quality_video
        explicit: str = ""

        # Check if item is available on TIDAL.
        # Note: Some albums have available=None, which should be treated as available
        if hasattr(media, "available") and media.available is False:
            return False

        # Set "Explicit" tag
        if isinstance(media, Track | Video | Album):
            explicit = " 🅴" if media.explicit else ""

        # Build name and set quality
        if isinstance(media, Track | Video):
            name = f"{name_builder_artist(media)} - {name_builder_title(media)}{explicit}"
        elif isinstance(media, Playlist | Artist):
            name = media.name
        elif isinstance(media, Album):
            name = f"{name_builder_artist(media)} - {media.name}{explicit}"
        elif isinstance(media, Mix):
            name = media.title

        # Determine actual quality.
        if isinstance(media, Track | Album):
            quality_highest: Quality = quality_audio_highest(media)

            if (
                self.settings.data.quality_audio == quality_highest
                or self.settings.data.quality_audio == Quality.hi_res_lossless
            ):
                quality_audio = quality_highest

        if name:
            result = QueueDownloadItem(
                name=name,
                quality_audio=quality_audio,
                quality_video=quality_video,
                type_media=type(media).__name__,
                status=QueueDownloadStatus.Waiting,
                obj=media,
            )
        else:
            result = False

        return result

    def _init_signals(self) -> None:
        """Connect signals to their respective slots."""
        self.pb_download.clicked.connect(lambda: self.thread_it(self.on_download_results))
        self.pb_download_list.clicked.connect(lambda: self.thread_it(self.on_download_list_media))
        self.pb_reload_user_lists.clicked.connect(lambda: self.thread_it(self.tidal_user_lists))
        self.pb_queue_download_clear_all.clicked.connect(self.on_queue_download_clear_all)
        self.pb_queue_download_clear_finished.clicked.connect(self.on_queue_download_clear_finished)
        self.pb_queue_download_remove.clicked.connect(self.on_queue_download_remove)
        self.pb_queue_download_toggle.clicked.connect(self.on_pb_queue_download_toggle)
        self.l_search.returnPressed.connect(
            lambda: self.search_populate_results(self.l_search.text(), self.cb_search_type.currentData())
        )
        self.pb_search.clicked.connect(
            lambda: self.search_populate_results(self.l_search.text(), self.cb_search_type.currentData())
        )
        self.cb_quality_audio.currentIndexChanged.connect(self.on_quality_set_audio)
        self.cb_quality_video.currentIndexChanged.connect(self.on_quality_set_video)
        self.tr_lists_user.itemClicked.connect(self.on_list_items_show)
        self.tr_lists_user.itemExpanded.connect(self.on_tr_lists_user_expanded)
        self.s_spinner_start[QtWidgets.QWidget].connect(self.on_spinner_start)
        self.s_spinner_stop.connect(self.on_spinner_stop)
        self.s_item_advance.connect(self.on_progress_item)
        self.s_item_name.connect(self.on_progress_item_name)
        self.s_list_name.connect(self.on_progress_list_name)
        self.s_list_advance.connect(self.on_progress_list)
        self.s_pb_reset.connect(self.on_progress_reset)
        self.s_populate_tree_lists.connect(self.on_populate_tree_lists)
        self.s_populate_folder_children.connect(self.on_populate_folder_children)
        self.s_statusbar_message.connect(self.on_statusbar_message)
        self.s_tr_results_add_top_level_item.connect(self.on_tr_results_add_top_level_item)
        self.s_settings_save.connect(self.on_settings_save)
        self.s_pb_reload_status.connect(self.button_reload_status)
        self.s_update_check.connect(lambda: self.thread_it(self.on_update_check))
        self.s_update_show.connect(self.on_version)

        # Menubar
        self.a_exit.triggered.connect(self.close)
        self.a_version.triggered.connect(self.on_version)
        self.a_preferences.triggered.connect(self.on_preferences)
        self.a_logout.triggered.connect(self.on_logout)
        self.a_updates_check.triggered.connect(lambda: self.on_update_check(False))

        # Results
        self.tr_results.expanded.connect(self.on_tr_results_expanded)
        self.tr_results.clicked.connect(self.on_result_item_clicked)
        self.tr_results.doubleClicked.connect(lambda: self.thread_it(self.on_download_results))

        # Download Queue
        self.tr_queue_download.itemClicked.connect(self.on_queue_download_item_clicked)
        self.s_queue_download_item_downloading.connect(self.on_queue_download_item_downloading)
        self.s_queue_download_item_finished.connect(self.on_queue_download_item_finished)
        self.s_queue_download_item_failed.connect(self.on_queue_download_item_failed)
        self.s_queue_download_item_skipped.connect(self.on_queue_download_item_skipped)

    def _init_buttons(self) -> None:
        """Initialize the state of the download buttons."""
        self.pb_queue_download_run()

    def on_logout(self) -> None:
        """Log out from TIDAL and close the application."""
        result: bool = self.tidal.logout()

        if result:
            sys.exit(0)

    def on_progress_list(self, value: float) -> None:
        """Update the progress of the list progress bar.

        Args:
            value (float): The progress value as a percentage.
        """
        self.pb_list.setValue(int(math.ceil(value)))

    def on_progress_item(self, value: float) -> None:
        """Update the progress of the item progress bar.

        Args:
            value (float): The progress value as a percentage.
        """
        self.pb_item.setValue(int(math.ceil(value)))

    def on_progress_item_name(self, value: str) -> None:
        """Set the format of the item progress bar.

        Args:
            value (str): The item name.
        """
        self.pb_item.setFormat(f"%p% {value}")

    def on_progress_list_name(self, value: str) -> None:
        """Set the format of the list progress bar.

        Args:
            value (str): The list name.
        """
        self.pb_list.setFormat(f"%p% {value}")

    def on_quality_set_audio(self, index: int) -> None:
        """Set the audio quality for downloads.

        Args:
            index: The index of the selected quality in the combo box.
        """
        quality_data = self.cb_quality_audio.itemData(index)

        self.settings.data.quality_audio = Quality(quality_data)
        self.settings.save()

        if self.tidal:
            self.tidal.settings_apply()

    def on_quality_set_video(self, index: int) -> None:
        """Set the video quality for downloads.

        Args:
            index: The index of the selected quality in the combo box.
        """
        self.settings.data.quality_video = QualityVideo(self.cb_quality_video.itemData(index))
        self.settings.save()

        if self.tidal:
            self.tidal.settings_apply()

    def on_tr_lists_user_expanded(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Handle expansion of folders in the user lists tree.

        Args:
            item (QTreeWidgetItem): The expanded tree item.
        """
        # Check if it's a first-time expansion (has disabled dummy child)
        if item.childCount() > 0 and item.child(0).isDisabled():
            # Run in thread to avoid blocking UI
            self.thread_it(self.tr_lists_user_load_folder_children, item)

    def tr_lists_user_load_folder_children(self, parent_item: QtWidgets.QTreeWidgetItem) -> None:
        """Load and display children of a folder in the user lists tree.

        Args:
            parent_item (QTreeWidgetItem): The parent folder item.
        """
        folder: Folder | None = get_user_list_media_item(parent_item)

        if not isinstance(folder, Folder):
            return

        # Show spinner while loading
        self.s_spinner_start.emit(self.tr_lists_user)

        try:
            # Fetch folder contents
            folders, playlists = self._fetch_folder_contents(folder)

            # Emit signal to populate in main thread
            self.s_populate_folder_children.emit(parent_item, folders, playlists)

        finally:
            self.s_spinner_stop.emit()

    def on_populate_folder_children(
        self, parent_item: QtWidgets.QTreeWidgetItem, folders: list[Folder], playlists: list[Playlist]
    ) -> None:
        """Populate folder children in the main thread (signal handler).

        Args:
            parent_item (QTreeWidgetItem): The parent folder item.
            folders (list[Folder]): List of sub-folders.
            playlists (list[Playlist]): List of playlists.
        """
        # Remove dummy child
        parent_item.takeChild(0)

        # Add sub-folders as children
        for sub_folder in folders:
            twi_child = QtWidgets.QTreeWidgetItem(parent_item)
            twi_child.setText(0, f"📁 {sub_folder.name}")
            set_user_list_media(twi_child, sub_folder)
            info = f"({sub_folder.total_number_of_items} items)" if sub_folder.total_number_of_items else ""
            twi_child.setText(2, info)

            # Add dummy child for potential sub-folders
            dummy = QtWidgets.QTreeWidgetItem(twi_child)
            dummy.setDisabled(True)

        # Add playlists as children
        for playlist in playlists:
            twi_child = QtWidgets.QTreeWidgetItem(parent_item)
            name = playlist.name if playlist.name else ""
            twi_child.setText(0, name)
            set_user_list_media(twi_child, playlist)
            info = f"({playlist.num_tracks + playlist.num_videos} Tracks)"
            if playlist.description:
                info += f" {playlist.description}"
            twi_child.setText(2, info)

    def _fetch_folder_contents(self, folder: Folder) -> tuple[list[Folder], list[Playlist]]:
        """Fetch contents (sub-folders and playlists) of a folder.

        Args:
            folder (Folder): The folder to fetch contents for.

        Returns:
            tuple[list[Folder], list[Playlist]]: Sub-folders and playlists within the folder.
        """
        folder_id = folder.id if folder.id else "root"

        # Fetch sub-folders with manual pagination
        offset = 0
        limit = 50
        folders = []

        while True:
            batch = self.tidal.session.user.favorites.playlist_folders(
                limit=limit, offset=offset, parent_folder_id=folder_id
            )
            if not batch:
                break
            folders.extend(batch)
            if len(batch) < limit:
                break
            offset += limit

        # Fetch playlists in this folder using folder.items() method
        offset = 0
        playlists = []

        while True:
            batch = folder.items(offset=offset, limit=limit)
            if not batch:
                break
            playlists.extend(batch)
            if len(batch) < limit:
                break
            offset += limit

        return folders, playlists

    def _get_folder_playlists(self, folder: Folder) -> list[Playlist]:
        """Fetch all playlists from a folder.

        Args:
            folder (Folder): The folder to fetch playlists from.

        Returns:
            list[Playlist]: List of playlists in the folder.
        """
        # Use existing method to fetch folder contents
        # Since folders can't contain folders, we ignore the folders return value
        _, playlists = self._fetch_folder_contents(folder)

        logger_gui.debug(f"Found {len(playlists)} playlists in folder: {folder.name}")

        return playlists

    def _get_playlist_tracks(self, playlist: Playlist | UserPlaylist | Mix) -> list[Track]:
        """Fetch all tracks from a playlist.

        Args:
            playlist (Playlist | UserPlaylist | Mix): The playlist to fetch tracks from.

        Returns:
            list[Track]: List of tracks in the playlist.
        """
        playlist_name = getattr(playlist, "name", "unknown")
        logger_gui.debug(f"Fetching tracks from playlist: {playlist_name}")
        media_items = items_results_all(playlist)

        # Filter for Track objects only (items_results_all may return Videos too)
        tracks = [item for item in media_items if isinstance(item, Track)]

        logger_gui.debug(f"Found {len(tracks)} tracks in playlist: {playlist_name}")

        return tracks

    def on_list_items_show(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Show the items in the selected playlist or mix.

        Args:
            item (QtWidgets.QTreeWidgetItem): The selected tree widget item.
        """
        self.thread_it(self.list_items_show, item)

    def list_items_show(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Fetch and display the items in a playlist, mix, or folder.

        Args:
            item (QtWidgets.QTreeWidgetItem): The tree widget item representing a playlist, mix, or folder.
        """
        media_list: Album | Playlist | Folder | str = get_user_list_media_item(item)

        # Only if clicked item is not a top level item.
        if media_list:
            # Show spinner while loading list
            self.s_spinner_start.emit(self.tr_results)
            try:
                if isinstance(media_list, Folder):
                    # Show folder contents
                    self._show_folder_contents(media_list)
                elif isinstance(media_list, str) and media_list.startswith("fav_"):
                    function_list = favorite_function_factory(self.tidal, media_list)
                    self.list_items_show_result(favorite_function=function_list)
                else:
                    self.list_items_show_result(media_list)
                    # Load cover asynchronously to avoid blocking the GUI
                    self.thread_it(self.cover_show, media_list)
            finally:
                self.s_spinner_stop.emit()

    def _show_folder_contents(self, folder: Folder) -> None:
        """Display folder contents (nested playlists/folders) in results pane.

        Args:
            folder (Folder): The folder to display contents for.
        """
        # Fetch folder contents using the shared helper method
        folders, playlists = self._fetch_folder_contents(folder)

        # Combine folders and playlists
        items = folders + playlists

        # Convert to ResultItems and display
        result = self.search_result_to_model(items)
        self.populate_tree_results(result)

    def on_result_item_clicked(self, index: QtCore.QModelIndex) -> None:
        """Handle the event when a result item is clicked.

        Args:
            index (QtCore.QModelIndex): The index of the clicked item.
        """
        media: Track | Video | Album | Artist = get_results_media_item(
            index, self.proxy_tr_results, self.model_tr_results
        )

        # Load cover asynchronously to avoid blocking the GUI
        self.thread_it(self.cover_show, media)

    def on_queue_download_item_clicked(self, item: QtWidgets.QTreeWidgetItem, column: int) -> None:
        """Handle the event when a queue download item is clicked.

        Args:
            item (QtWidgets.QTreeWidgetItem): The clicked tree widget item.
            column (int): The column index of the clicked item.
        """
        media: Track | Video | Album | Artist | Mix | Playlist = get_queue_download_media(item)

        # Load cover asynchronously to avoid blocking the GUI
        self.thread_it(self.cover_show, media)

    def cover_show(self, media: Album | Playlist | Track | Video | Album | Artist) -> None:
        """Show the cover image of the selected media item.

        Args:
            media (Album | Playlist | Track | Video | Album | Artist): The media item.
        """
        cover_url: str = ""
        # Show spinner in the cover label itself
        parent_widget = self.l_pm_cover

        # Show spinner while loading
        self.s_spinner_start.emit(parent_widget)

        try:
            try:
                cover_url = media.album.image()
            except Exception:
                # Only call image() if it exists
                if hasattr(media, "image") and callable(getattr(media, "image", None)):
                    try:
                        cover_url = media.image()
                    except Exception:
                        logger_gui.info(f"No cover available (media ID: {getattr(media, 'id', 'unknown')}).")
                else:
                    cover_url = None

                    logger_gui.info(f"No cover available (media ID: {getattr(media, 'id', 'unknown')}).")

            if cover_url and self.cover_url_current != cover_url:
                self.cover_url_current = cover_url
                data_cover: bytes = Download.cover_data(cover_url)
                pixmap: QtGui.QPixmap = QtGui.QPixmap()
                pixmap.loadFromData(data_cover)
                self.l_pm_cover.setPixmap(pixmap)
            elif not cover_url:
                path_image: str = resource_path("tidal_dl_ng/ui/default_album_image.png")
                self.l_pm_cover.setPixmap(QtGui.QPixmap(path_image))
        finally:
            self.s_spinner_stop.emit()

    def list_items_show_result(
        self,
        media_list: Album | Playlist | Mix | Artist | None = None,
        point: QtCore.QPoint | None = None,
        parent: QtGui.QStandardItem | None = None,
        favorite_function: Callable | None = None,
    ) -> None:
        """Populate the results tree with the items of a media list.

        Args:
            media_list (Album | Playlist | Mix | Artist | None, optional): The media list to show. Defaults to None.
            point (QPoint | None, optional): The point in the tree. Defaults to None.
            parent (QStandardItem | None, optional): Parent item for nested results. Defaults to None.
            favorite_function (Callable | None, optional): Function to fetch favorite items. Defaults to None.
        """
        if point:
            item = self.tr_lists_user.itemAt(point)
            media_list = get_user_list_media_item(item)

        # Get all results
        if favorite_function or isinstance(media_list, str):
            if isinstance(media_list, str):
                favorite_function = favorite_function_factory(self.tidal, media_list)

            media_items: list[Track | Video | Album] = favorite_function()
        else:
            media_items: list[Track | Video | Album] = items_results_all(media_list)

        result: list[ResultItem] = self.search_result_to_model(media_items)

        self.populate_tree_results(result, parent=parent)

    def thread_it(self, fn: Callable, *args, **kwargs) -> None:
        """Run a function in a separate thread.

        Args:
            fn (Callable): The function to run.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.
        """
        # Any other args, kwargs are passed to the run function
        worker = Worker(fn, *args, **kwargs)

        # Execute
        self.threadpool.start(worker)

    def on_queue_download_clear_all(self) -> None:
        """Clear all items from the download queue."""
        self.on_clear_queue_download(
            f"({QueueDownloadStatus.Waiting}|{QueueDownloadStatus.Finished}|{QueueDownloadStatus.Failed})"
        )

    def on_queue_download_clear_finished(self) -> None:
        """Clear finished items from the download queue."""
        self.on_clear_queue_download(f"[{QueueDownloadStatus.Finished}]")

    def on_clear_queue_download(self, regex: str) -> None:
        """Clear items from the download queue matching the given regex.

        Args:
            regex (str): Regular expression to match items.
        """
        items: list[QtWidgets.QTreeWidgetItem | None] = self.tr_queue_download.findItems(
            regex, QtCore.Qt.MatchFlag.MatchRegularExpression, column=0
        )

        for item in items:
            self.tr_queue_download.takeTopLevelItem(self.tr_queue_download.indexOfTopLevelItem(item))

    def on_queue_download_remove(self) -> None:
        """Remove selected items from the download queue."""
        items: list[QtWidgets.QTreeWidgetItem | None] = self.tr_queue_download.selectedItems()

        if len(items) == 0:
            logger_gui.error("Please select an item from the queue first.")
        else:
            for item in items:
                status: str = item.text(0)

                if status != QueueDownloadStatus.Downloading:
                    self.tr_queue_download.takeTopLevelItem(self.tr_queue_download.indexOfTopLevelItem(item))
                else:
                    logger_gui.info("Cannot remove a currently downloading item from queue.")

    def on_pb_queue_download_toggle(self) -> None:
        """Toggle download status (pause / resume) accordingly.

        :return: None
        """
        handling_app: HandlingApp = HandlingApp()

        if handling_app.event_run.is_set():
            self.pb_queue_download_pause()
        else:
            self.pb_queue_download_run()

    def pb_queue_download_run(self) -> None:
        """Start the download queue and update the button state."""
        handling_app: HandlingApp = HandlingApp()

        handling_app.event_run.set()

        icon = QtGui.QIcon(QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.MediaPlaybackPause))
        self.pb_queue_download_toggle.setIcon(icon)
        self.pb_queue_download_toggle.setStyleSheet("background-color: #e0a800; color: #212529")

    def pb_queue_download_pause(self) -> None:
        """Pause the download queue and update the button state."""
        handling_app: HandlingApp = HandlingApp()

        handling_app.event_run.clear()

        icon = QtGui.QIcon(QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.MediaPlaybackStart))
        self.pb_queue_download_toggle.setIcon(icon)
        self.pb_queue_download_toggle.setStyleSheet("background-color: #218838; color: #fff")

    # TODO: Must happen in main thread. Do not thread this.
    def on_download_results(self) -> None:
        """Download the selected results in the results tree."""
        items: [HumanProxyModel | None] = self.tr_results.selectionModel().selectedRows()

        if len(items) == 0:
            logger_gui.error("Please select a row first.")
        else:
            for item in items:
                media: Track | Album | Playlist | Video | Artist = get_results_media_item(
                    item, self.proxy_tr_results, self.model_tr_results
                )
                queue_dl_item: QueueDownloadItem = self.media_to_queue_download_model(media)

                if queue_dl_item:
                    self.queue_download_media(queue_dl_item)

    def queue_download_media(self, queue_dl_item: QueueDownloadItem) -> None:
        """Add a media item to the download queue.

        Args:
            queue_dl_item (QueueDownloadItem): The item to add to the queue.
        """
        # Populate child
        child: QtWidgets.QTreeWidgetItem = QtWidgets.QTreeWidgetItem()

        child.setText(0, queue_dl_item.status)
        set_queue_download_media(child, queue_dl_item.obj)
        child.setText(2, queue_dl_item.name)
        child.setText(3, queue_dl_item.type_media)
        child.setText(4, queue_dl_item.quality_audio)
        child.setText(5, queue_dl_item.quality_video)
        self.tr_queue_download.addTopLevelItem(child)

    def watcher_queue_download(self) -> None:
        """Monitor the download queue and process items as they become available."""
        handling_app: HandlingApp = HandlingApp()

        while not handling_app.event_abort.is_set():
            items: list[QtWidgets.QTreeWidgetItem | None] = self.tr_queue_download.findItems(
                QueueDownloadStatus.Waiting, QtCore.Qt.MatchFlag.MatchExactly, column=0
            )

            if len(items) > 0:
                result: QueueDownloadStatus
                item: QtWidgets.QTreeWidgetItem = items[0]
                media: Track | Album | Playlist | Video | Mix | Artist = get_queue_download_media(item)
                quality_audio: Quality = get_queue_download_quality_audio(item)
                quality_video: QualityVideo = get_queue_download_quality_video(item)

                try:
                    self.s_queue_download_item_downloading.emit(item)
                    result = self.on_queue_download(media, quality_audio=quality_audio, quality_video=quality_video)

                    if result == QueueDownloadStatus.Finished:
                        self.s_queue_download_item_finished.emit(item)
                    elif result == QueueDownloadStatus.Skipped:
                        self.s_queue_download_item_skipped.emit(item)
                except Exception as e:
                    logger_gui.error(e)
                    self.s_queue_download_item_failed.emit(item)
            else:
                time.sleep(2)

    def on_queue_download_item_downloading(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Update the status of a queue download item to 'Downloading'.

        Args:
            item (QtWidgets.QTreeWidgetItem): The item to update.
        """
        self.queue_download_item_status(item, QueueDownloadStatus.Downloading)

    def on_queue_download_item_finished(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Update the status of a queue download item to 'Finished'.

        Args:
            item (QtWidgets.QTreeWidgetItem): The item to update.
        """
        self.queue_download_item_status(item, QueueDownloadStatus.Finished)

    def on_queue_download_item_failed(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Update the status of a queue download item to 'Failed'.

        Args:
            item (QtWidgets.QTreeWidgetItem): The item to update.
        """
        self.queue_download_item_status(item, QueueDownloadStatus.Failed)

    def on_queue_download_item_skipped(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Update the status of a queue download item to 'Skipped'.

        Args:
            item (QtWidgets.QTreeWidgetItem): The item to update.
        """
        self.queue_download_item_status(item, QueueDownloadStatus.Skipped)

    def queue_download_item_status(self, item: QtWidgets.QTreeWidgetItem, status: str) -> None:
        """Set the status text of a queue download item.

        Args:
            item (QtWidgets.QTreeWidgetItem): The item to update.
            status (str): The status text.
        """
        item.setText(0, status)

    def on_queue_download(
        self,
        media: Track | Album | Playlist | Video | Mix | Artist,
        quality_audio: Quality | None = None,
        quality_video: QualityVideo | None = None,
    ) -> QueueDownloadStatus:
        """Download the specified media item(s) and return the result status.

        Args:
            media (Track | Album | Playlist | Video | Mix | Artist): The media item(s) to download.
            quality_audio (Quality | None, optional): Desired audio quality. Defaults to None.
            quality_video (QualityVideo | None, optional): Desired video quality. Defaults to None.

        Returns:
            QueueDownloadStatus: The status of the download operation.
        """
        result: QueueDownloadStatus
        items_media: [Track | Album | Playlist | Video | Mix | Artist]

        if isinstance(media, Artist):
            items_media: [Album] = items_results_all(media)
        else:
            items_media = [media]

        download_delay: bool = bool(isinstance(media, Track | Video) and self.settings.data.download_delay)

        for item_media in items_media:
            result = self.download(
                item_media,
                self.dl,
                delay_track=download_delay,
                quality_audio=quality_audio,
                quality_video=quality_video,
            )

        return result

    def download(
        self,
        media: Track | Album | Playlist | Video | Mix | Artist,
        dl: Download,
        delay_track: bool = False,
        quality_audio: Quality | None = None,
        quality_video: QualityVideo | None = None,
    ) -> QueueDownloadStatus:
        """Download a media item and return the result status.

        Args:
            media (Track | Album | Playlist | Video | Mix | Artist): The media item to download.
            dl (Download): The Download object to use.
            delay_track (bool, optional): Whether to apply download delay. Defaults to False.
            quality_audio (Quality | None, optional): Desired audio quality. Defaults to None.
            quality_video (QualityVideo | None, optional): Desired video quality. Defaults to None.

        Returns:
            QueueDownloadStatus: The status of the download operation.
        """
        result_dl: bool
        path_file: str
        result: QueueDownloadStatus
        self.s_pb_reset.emit()
        self.s_statusbar_message.emit(StatusbarMessage(message="Download started..."))

        file_template = get_format_template(media, self.settings)

        if isinstance(media, Track | Video):
            result_dl, path_file = dl.item(
                media=media,
                file_template=file_template,
                download_delay=delay_track,
                quality_audio=quality_audio,
                quality_video=quality_video,
            )
        elif isinstance(media, Album | Playlist | Mix):
            dl.items(
                media=media,
                file_template=file_template,
                video_download=self.settings.data.video_download,
                download_delay=self.settings.data.download_delay,
                quality_audio=quality_audio,
                quality_video=quality_video,
            )

            # Dummy values
            result_dl = True
            path_file = "dummy"

        self.s_statusbar_message.emit(StatusbarMessage(message="Download finished.", timeout=2000))

        if result_dl and path_file:
            result = QueueDownloadStatus.Finished
        elif not result_dl and path_file:
            result = QueueDownloadStatus.Skipped
        else:
            result = QueueDownloadStatus.Failed

        return result

    def on_version(
        self, update_check: bool = False, update_available: bool = False, update_info: ReleaseLatest | None = None
    ) -> None:
        """Show the version information dialog.

        Args:
            update_check (bool, optional): Whether to check for updates. Defaults to False.
            update_available (bool, optional): Whether an update is available. Defaults to False.
            update_info (ReleaseLatest | None, optional): Information about the latest release. Defaults to None.
        """
        DialogVersion(self, update_check, update_available, update_info)

    def on_preferences(self) -> None:
        """Open the preferences dialog."""
        # Prevent multiple instances. Reuse existing dialog if still visible.
        if self.dialog_preferences and self.dialog_preferences.isVisible():
            # Bring existing dialog to front.
            self.dialog_preferences.raise_()
            self.dialog_preferences.activateWindow()
            return

        # Clear stale reference if dialog was closed.
        if self.dialog_preferences and not self.dialog_preferences.isVisible():
            self.dialog_preferences = None

        # Create new non-blocking preferences dialog.
        dlg = DialogPreferences(settings=self.settings, settings_save=self.s_settings_save, parent=self)
        dlg.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)

        # Disable action while dialog open.
        self.a_preferences.setEnabled(False)

        def _on_destroyed():
            self.dialog_preferences = None
            self.a_preferences.setEnabled(True)

        dlg.destroyed.connect(_on_destroyed)
        self.dialog_preferences = dlg
        dlg.show()

    def on_tr_results_expanded(self, index: QtCore.QModelIndex) -> None:
        """Handle the event when a result item group is expanded.

        Args:
            index (QtCore.QModelIndex): The index of the expanded item.
        """
        self.thread_it(self.tr_results_expanded, index)

    def tr_results_expanded(self, index: QtCore.QModelIndex) -> None:
        """Load and display the children of an expanded result item.

        Args:
            index (QtCore.QModelIndex): The index of the expanded item.
        """
        # If the child is a dummy the list_item has not been expanded before
        item: QtGui.QStandardItem = self.model_tr_results.itemFromIndex(self.proxy_tr_results.mapToSource(index))
        load_children: bool = not item.child(0, 0).isEnabled()

        if load_children:
            item.removeRow(0)
            media_list: list[Mix | Album | Playlist | Artist] = get_results_media_item(
                index, self.proxy_tr_results, self.model_tr_results
            )

            # Show spinner while loading children
            self.s_spinner_start.emit(self.tr_results)

            try:
                self.list_items_show_result(media_list=media_list, parent=item)
            finally:
                self.s_spinner_stop.emit()

    def button_reload_status(self, status: bool) -> None:
        """Update the reload button's state and text.

        Args:
            status (bool): The new status.
        """
        button_text: str = "Reloading..."

        if status:
            button_text = "Reload"

        self.pb_reload_user_lists.setEnabled(status)
        self.pb_reload_user_lists.setText(button_text)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Handle the close event of the main window.

        Args:
            event (QtGui.QCloseEvent): The close event.
        """
        # Save the main window size and position
        self.settings.data.window_x = self.x()
        self.settings.data.window_y = self.y()
        self.settings.data.window_w = self.width()
        self.settings.data.window_h = self.height()
        self.settings.save()

        self.shutdown = True

        handling_app: HandlingApp = HandlingApp()
        handling_app.event_abort.set()

        event.accept()

    def thread_download_album_from_track(self, point: QtCore.QPoint) -> None:
        """Starts the download of the full album from a selected track in a new thread.

        Args:
            point (QPoint): The point in the tree where the user clicked.
        """
        self.thread_it(self.on_download_album_from_track, point)

    def on_download_album_from_track(self, point: QtCore.QPoint) -> None:
        """Adds the album associated with a selected track to the download queue.

        This method retrieves the album from a track selected in the results tree and attempts to add it to the download queue. If the album cannot be retrieved or an error occurs, a warning or error is logged.

        Args:
            point (QtCore.QPoint): The point in the results tree where the user clicked.
        """
        index: QtCore.QModelIndex = self.tr_results.indexAt(point)
        media_track: Track = get_results_media_item(index, self.proxy_tr_results, self.model_tr_results)

        # Ensure we have a track and an album object with an ID
        if isinstance(media_track, Track) and media_track.album and media_track.album.id:
            try:
                # Use the album ID from the track to fetch the FULL album object from TIDAL
                full_album_object = self.tidal.session.album(media_track.album.id)

                # Convert the full album object into a queue item
                queue_dl_item: QueueDownloadItem | None = self.media_to_queue_download_model(full_album_object)

                if queue_dl_item:
                    # Add the item to the download queue
                    self.queue_download_media(queue_dl_item)
                else:
                    logger_gui.warning(f"Failed to create a queue item for album ID: {full_album_object.id}")
            except Exception as e:
                logger_gui.error(f"Could not fetch the full album from TIDAL. Error: {e}")
        else:
            logger_gui.warning("Could not retrieve album information from the selected track.")


# TODO: Comment with Google Docstrings.
def gui_activate(tidal: Tidal | None = None):
    # Set dark theme and create QT app.
    qdarktheme.enable_hi_dpi()

    app = QtWidgets.QApplication(sys.argv)

    # Fix for Windows: Tooltips have bright font color
    # https://github.com/5yutan5/PyQtDarkTheme/issues/239
    # qdarktheme.setup_theme()
    qdarktheme.setup_theme(additional_qss="QToolTip { border: 0px; }")

    # Create icon object and apply it to app window.
    icon: QtGui.QIcon = QtGui.QIcon()

    icon.addFile("tidal_dl_ng/ui/icon16.png", QtCore.QSize(16, 16))
    icon.addFile("tidal_dl_ng/ui/icon32.png", QtCore.QSize(32, 32))
    icon.addFile("tidal_dl_ng/ui/icon48.png", QtCore.QSize(48, 48))
    icon.addFile("tidal_dl_ng/ui/icon64.png", QtCore.QSize(64, 64))
    icon.addFile("tidal_dl_ng/ui/icon256.png", QtCore.QSize(256, 256))
    icon.addFile("tidal_dl_ng/ui/icon512.png", QtCore.QSize(512, 512))
    app.setWindowIcon(icon)

    # This bit gets the taskbar icon working properly in Windows
    if sys.platform.startswith("win"):
        import ctypes

        # Make sure Pyinstaller icons are still grouped
        if not sys.argv[0].endswith(".exe"):
            # Arbitrary string
            my_app_id: str = "exislow.tidal.dl-ng." + __version__
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(my_app_id)

    window = MainWindow(tidal=tidal)

    window.show()
    # Check for updates
    window.s_update_check.emit(True)

    sys.exit(app.exec())


if __name__ == "__main__":
    gui_activate()
