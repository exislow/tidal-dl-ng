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


import contextlib
import math
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from typing import Any

from requests.exceptions import HTTPError
from tidalapi.session import LinkLogin

from tidal_dl_ng import __version__, update_available
from tidal_dl_ng.dialog import DialogLogin, DialogPreferences, DialogVersion
from tidal_dl_ng.dialog_history import DialogHistory
from tidal_dl_ng.helper.gui import (
    FilterHeader,
    HumanProxyModel,
    get_results_media_item,
    get_user_list_media_item,
)
from tidal_dl_ng.helper.hover_manager import HoverManager
from tidal_dl_ng.helper.tidal import (
    extract_contributor_names,
    favorite_function_factory,
    fetch_raw_track_and_album,
    items_results_all,
    name_builder_artist,
    parse_track_and_album_extras,
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
from tidalapi import Album, Mix, Playlist, Quality, Track, Video
from tidalapi.artist import Artist
from tidalapi.session import SearchTypes

from tidal_dl_ng.cache import TrackExtrasCache
from tidal_dl_ng.config import HandlingApp, Settings, Tidal
from tidal_dl_ng.constants import QualityVideo
from tidal_dl_ng.download import Download
from tidal_dl_ng.gui_covers import CoverManager
from tidal_dl_ng.gui_playlist import GuiPlaylistManager
from tidal_dl_ng.gui_queue import GuiQueueManager
from tidal_dl_ng.gui_search import GuiSearchManager
from tidal_dl_ng.history import HistoryService
from tidal_dl_ng.logger import XStream, logger_gui
from tidal_dl_ng.model.gui_data import ProgressBars, ResultItem, StatusbarMessage
from tidal_dl_ng.model.meta import ReleaseLatest
from tidal_dl_ng.ui.info_tab_widget import InfoTabWidget
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
    history_service: HistoryService
    threadpool: QtCore.QThreadPool
    tray: QtWidgets.QSystemTrayIcon
    spinners: dict
    cover_url_current: str = ""
    shutdown: bool = False
    model_tr_results: QtGui.QStandardItemModel = QtGui.QStandardItemModel()
    proxy_tr_results: HumanProxyModel
    info_tab_widget: InfoTabWidget
    hover_manager: HoverManager
    queue_manager: GuiQueueManager
    playlist_manager: GuiPlaylistManager
    search_manager: GuiSearchManager
    s_spinner_start: QtCore.Signal = QtCore.Signal(QtWidgets.QWidget)
    s_spinner_stop: QtCore.Signal = QtCore.Signal()
    s_track_extras_ready: QtCore.Signal = QtCore.Signal(str, object)  # track_id, extras
    s_invoke_callback: QtCore.Signal = QtCore.Signal(str, object)  # track_id, extras - for InfoTabWidget callback
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

    def __init__(self, tidal: Tidal | None = None) -> None:
        """Initialize the main window and all components.

        Args:
            tidal (Tidal | None): Optional Tidal session object.
        """
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("TIDAL Downloader Next Generation!")

        # Initialize settings first
        self.settings = Settings()

        # Initialize managers that depend on settings
        self.queue_manager = GuiQueueManager(self)
        self.playlist_manager = GuiPlaylistManager(self)
        self.search_manager = GuiSearchManager(self)
        self.info_tab_widget = InfoTabWidget(self, self.tabWidget)

        # Logging redirect.
        XStream.stdout().messageWritten.connect(self._log_output)
        # XStream.stderr().messageWritten.connect(self._log_output)

        self.settings = Settings()
        self.history_service = HistoryService()

        # Core components
        self._init_threads()
        self._init_gui()
        self.track_extras_cache = TrackExtrasCache()
        self._pending_extras_workers: dict[str, Worker] = {}
        self._track_extras_callbacks: dict[str, Callable] = {}  # Store callbacks by track_id

        # Managers that have dependencies
        self.cover_manager = CoverManager(self, self.threadpool, self.info_tab_widget)

        # Initialize the rest of the UI
        self.info_tab_widget.set_track_extras_provider(self.get_track_extras)
        self._init_tree_results_model(self.model_tr_results)
        self._init_tree_results(self.tr_results, self.model_tr_results)
        self.playlist_manager.init_ui()
        self.queue_manager.init_ui()
        self._init_progressbar()
        self._populate_quality(self.cb_quality_audio, Quality)
        self._populate_quality(self.cb_quality_video, QualityVideo)
        self._populate_search_types(self.cb_search_type, SearchTypes)
        self.apply_settings(self.settings)
        self._init_menu_actions()
        self._init_signals()

        # Connect signal for invoking track extras callbacks
        self.s_invoke_callback.connect(self._on_invoke_callback)

        self.init_tidal(tidal)

        logger_gui.debug("All setup.")

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Ensure background workers and hover hooks stop before exit."""
        HandlingApp().event_abort.set()
        if hasattr(self, "hover_manager") and self.hover_manager:
            with contextlib.suppress(Exception):
                self.hover_manager.stop()
        self.threadpool.waitForDone(2000)
        super().closeEvent(event)

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
            self.thread_it(self.playlist_manager.tidal_user_lists)

    def _init_threads(self):
        """Initialize thread pool and start background workers."""
        self.threadpool = QtCore.QThreadPool()
        self.thread_it(self.queue_manager.watcher_queue_download)

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

    def get_track_extras(self, track_id: str, callback: Callable[[str, dict | None], None]) -> dict | None:
        """Return cached extras for a track or start async fetch.

        Args:
            track_id: The track ID to fetch extras for.
            callback: Function to call when async fetch completes.

        Returns:
            Cached extras dict if available, None if fetching async.
        """
        cached = self.track_extras_cache.get(track_id)
        if cached is not None:
            return cached

        if track_id in self._pending_extras_workers:
            return None

        # Store the callback for this track_id
        if callback:
            self._track_extras_callbacks[track_id] = callback

        def worker() -> None:
            extras = None
            try:
                track_json, album_json = fetch_raw_track_and_album(self.tidal.session, track_id)
                extras = parse_track_and_album_extras(track_json, album_json)
                extras = self._decorate_extras(extras)
                self.track_extras_cache.set(track_id, extras)
            except Exception:
                extras = None  # Return None on errors
            finally:
                self._pending_extras_workers.pop(track_id, None)
                # Emit signal for any listeners
                self.s_track_extras_ready.emit(track_id, extras)
                # Emit signal to invoke the callback (will be handled by _on_invoke_callback in main thread)
                self.s_invoke_callback.emit(track_id, extras)

        worker_obj = Worker(worker)
        self._pending_extras_workers[track_id] = worker_obj
        self.threadpool.start(worker_obj)
        return None

    @QtCore.Slot(str, object)
    def _on_invoke_callback(self, track_id: str, extras: dict | None) -> None:
        """Invoke the stored callback for a track in the main thread.

        This slot is connected to s_invoke_callback signal and runs in the main GUI thread,
        allowing safe UI updates from the callback.
        """
        callback = self._track_extras_callbacks.pop(track_id, None)
        if callback:
            with contextlib.suppress(Exception):
                callback(track_id, extras)

    def _decorate_extras(self, extras: dict | None) -> dict:
        """Add formatted string fields to extras dict."""
        if not extras:
            return {}
        result = dict(extras)
        result["genres_text"] = ", ".join(result.get("genres", []))
        for role, key in [
            ("producer", "producers_text"),
            ("composer", "composers_text"),
            ("lyricist", "lyricists_text"),
        ]:
            result[key] = extract_contributor_names(result.get("contributors_by_role"), role)
        return result

    def preload_covers_for_playlist(self, items: list) -> None:
        """Preload cover pixmaps for a list of tracks in background."""
        if self.cover_manager:
            self.cover_manager.preload_covers_for_playlist(items)

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
        tree.setColumnWidth(8, skinny_width)  # downloaded?
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        # Connect the contextmenu
        tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        tree.customContextMenuRequested.connect(self.menu_context_tree_results)

        # Initialize hover manager for track preview
        self.hover_manager = HoverManager(
            tree_view=tree,
            proxy_model=self.proxy_tr_results,
            source_model=model,
            debounce_delay_ms=50,
            parent=self,
        )
        # Connect hover signals
        self.hover_manager.s_hover_confirmed.connect(self.on_track_hover_confirmed)
        self.hover_manager.s_hover_left.connect(self.on_track_hover_left)

    def _init_tree_results_model(self, model: QtGui.QStandardItemModel) -> None:
        """Initialize the model for the results tree view.

        Args:
            model (QStandardItemModel): The model to initialize.
        """
        labels_column: list[str] = [
            "#",
            "obj",
            "Artist",
            "Title",
            "Album",
            "Duration",
            "Quality",
            "Date",
            "Downloaded?",
        ]

        model.setColumnCount(len(labels_column))
        model.setRowCount(0)
        model.setHorizontalHeaderLabels(labels_column)

    def on_update_check(self, on_startup: bool = True) -> None:
        """Check for application updates and emit update signals.

        Args:
            on_startup (bool, optional): Whether this is called on startup. Defaults to True.
        """
        is_available, info = update_available()

        if (on_startup and is_available) or not on_startup:
            self.s_update_show.emit(True, is_available, info)

    # The rest of the class remains unchanged
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

        # Add mark/unmark as downloaded for Tracks
        if isinstance(media, Track):
            track_id = str(media.id)
            is_downloaded = self.history_service.is_downloaded(track_id)

            if is_downloaded:
                menu.addAction(
                    "✖️ Mark as Not Downloaded", lambda: self.on_mark_track_as_not_downloaded(track_id, index)
                )
            else:
                menu.addAction("✅ Mark as Downloaded", lambda: self.on_mark_track_as_downloaded(media, index))

        menu.addAction("Copy Share URL", lambda: self.on_copy_url_share(self.tr_results, point))

        menu.exec(self.tr_results.mapToGlobal(point))

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
                    logger_gui.info(
                        f"ðY>' RATE LIMITING: Processed {idx - 1} albums, pausing for {delay_sec} seconds..."
                    )
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
            queue_dl_item = self.queue_manager.media_to_queue_download_model(album)
            if queue_dl_item:
                queue_items.append((queue_dl_item, album))
                logger_gui.debug(f"Prepared: {name_builder_artist(album)} - {album.name}")

        # Add all items to queue
        logger_gui.info(f"Adding {len(queue_items)} albums to queue...")
        for queue_dl_item, album in queue_items:
            self.queue_manager.queue_download_media(queue_dl_item)
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

        # Check download history
        child_downloaded: QtGui.QStandardItem = QtGui.QStandardItem()
        if isinstance(item.obj, Track):
            track_id = str(item.obj.id)
            if self.history_service.is_downloaded(track_id):
                child_downloaded.setText("✅")
                child_downloaded.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

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
            child_downloaded,
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

    def _init_signals(self) -> None:
        """Connect signals to their respective slots."""
        self.pb_download.clicked.connect(lambda: self.thread_it(self.on_download_results))
        self.pb_download_list.clicked.connect(lambda: self.thread_it(self.playlist_manager.on_download_list_media))
        self.l_search.returnPressed.connect(
            lambda: self.search_manager.search_populate_results(self.l_search.text(), self.cb_search_type.currentData())
        )
        self.pb_search.clicked.connect(
            lambda: self.search_manager.search_populate_results(self.l_search.text(), self.cb_search_type.currentData())
        )
        self.cb_quality_audio.currentIndexChanged.connect(self.on_quality_set_audio)
        self.cb_quality_video.currentIndexChanged.connect(self.on_quality_set_video)
        self.s_spinner_start[QtWidgets.QWidget].connect(self.on_spinner_start)
        self.s_spinner_stop.connect(self.on_spinner_stop)
        self.s_item_advance.connect(self.on_progress_item)
        self.s_item_name.connect(self.on_progress_item_name)
        self.s_list_name.connect(self.on_progress_list_name)
        self.s_list_advance.connect(self.on_progress_list)
        self.s_pb_reset.connect(self.on_progress_reset)
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

        # Managers
        self.queue_manager.connect_signals()
        self.playlist_manager.connect_signals()

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

    def on_result_item_clicked(self, index: QtCore.QModelIndex) -> None:
        """Handle the event when a result item is clicked.

        Args:
            index (QtCore.QModelIndex): The index of the clicked item.
        """
        media: Track | Video | Album | Artist = get_results_media_item(
            index, self.proxy_tr_results, self.model_tr_results
        )

        # Update info tab widget with selected media (persists selection)
        self.info_tab_widget.update_on_selection(media)

        # Load cover asynchronously to avoid blocking the GUI
        self.thread_it(self.cover_manager.load_cover, media)

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
            media_items: list[Track | Video | Album] = items_results_all(self.tidal.session, media_list)

        result: list[ResultItem] = self.search_manager.search_result_to_model(media_items)

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
                queue_dl_item = self.queue_manager.media_to_queue_download_model(media)

                if queue_dl_item:
                    self.queue_manager.queue_download_media(queue_dl_item)

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
        DialogPreferences(settings=self.settings, settings_save=self.s_settings_save, parent=self)

    def on_view_history(self) -> None:
        """Open the download history dialog."""
        DialogHistory(history_service=self.history_service, parent=self)

    def on_toggle_duplicate_prevention(self, enabled: bool) -> None:
        """Toggle duplicate download prevention on or off.

        Args:
            enabled (bool): Whether duplicate prevention is enabled.
        """
        self.history_service.update_settings(preventDuplicates=enabled)
        status_msg = "enabled" if enabled else "disabled"
        logger_gui.info(f"Duplicate download prevention {status_msg}")
        self.s_statusbar_message.emit(StatusbarMessage(message=f"Duplicate prevention {status_msg}.", timeout=2500))

    def on_tr_results_expanded(self, index: QtCore.QModelIndex) -> None:
        """Handle the event when a result item group is expanded.

        Args:
            index (QtCore.QModelIndex): The index of the expanded item.
        """
        self.thread_it(self.tr_results_expanded, index)

    def on_track_hover_confirmed(self, media: Track | Video | Album | Mix | Playlist | Artist) -> None:
        """Handle confirmed hover event over a track (after debounce delay)."""
        if not media:
            return

        # Update info tab widget with hover data
        self.info_tab_widget.update_on_hover(media)

        # Load cover using CoverManager (with smart caching)
        if self.cover_manager:
            self.cover_manager.load_cover(media, use_cache_check=True)

    def on_track_hover_left(self) -> None:
        """Handle hover leaving the track list."""
        # Revert to the currently selected media
        with contextlib.suppress(Exception):
            self.info_tab_widget.revert_to_selection()

        # Reload the cover for the selected media if it exists
        if self.info_tab_widget.current_media_selected and self.cover_manager:
            self.cover_manager.load_cover(self.info_tab_widget.current_media_selected, use_cache_check=True)

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
                queue_dl_item = self.queue_manager.media_to_queue_download_model(full_album_object)

                if queue_dl_item:
                    # Add the item to the download queue
                    self.queue_manager.queue_download_media(queue_dl_item)
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
