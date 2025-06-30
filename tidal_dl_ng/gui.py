# Compilation mode, support OS-specific options
# nuitka-project-if: {OS} in ("Darwin"):
#    nuitka-project: --macos-create-app-bundle
#    nuitka-project: --macos-app-icon=tidal_dl_ng/ui/icon.icns
#    nuitka-project: --macos-signed-app-name=com.exislow.TidalDlNg
#    nuitka-project: --macos-app-mode=gui
# nuitka-project-if: {OS} in ("Linux", "FreeBSD"):
#    nuitka-project: --linux-icon=tidal_dl_ng/ui/icon.png
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
# nuitka-project: --include-data-files={MAIN_DIRECTORY}/ui/icon.*=tidal_dl_ng/ui/
# nuitka-project: --include-data-files={MAIN_DIRECTORY}/ui/default_album_image.png=tidal_dl_ng/ui/default_album_image.png
# nuitka-project: --include-data-files=./pyproject.toml=pyproject.toml
# nuitka-project: --force-stderr-spec="{TEMP}/tidal-dl-ng.err.log"
# nuitka-project: --force-stdout-spec="{TEMP}/tidal-dl-ng.out.log"
# nuitka-project: --company-name=exislow


import math
import sys
import time
from collections.abc import Callable, Sequence

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
    user_media_lists,
)

try:
    import qdarktheme
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError as e:
    print(e)
    print("Qt dependencies missing. Cannot start GUI. Please read the 'README.md' carefully.")
    sys.exit(1)

import coloredlogs.converter
from rich.progress import Progress
from tidalapi import Album, Mix, Playlist, Quality, Track, UserPlaylist, Video
from tidalapi.artist import Artist
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
    s_populate_tree_lists: QtCore.Signal = QtCore.Signal(list)
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

    def __init__(self, tidal: Tidal | None = None):
        super().__init__()
        self.setupUi(self)
        # self.setGeometry(50, 50, 500, 300)
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

    def _init_gui(self):
        self.spinners = {}

    def init_tidal(self, tidal: Tidal = None):
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
                    d_login: DialogLogin = DialogLogin(
                        url_login=link_login.verification_uri_complete,
                        hint=hint,
                        expires_in=link_login.expires_in,
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
        self.threadpool = QtCore.QThreadPool()
        self.thread_it(self.watcher_queue_download)

    def _init_dl(self):
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
            session=self.tidal.session,
            skip_existing=self.tidal.settings.data.skip_existing,
            path_base=self.settings.data.download_base_path,
            fn_logger=logger_gui,
            progress_gui=data_pb,
            progress=progress,
            event_abort=handling_app.event_abort,
            event_run=handling_app.event_run,
        )

    def _init_progressbar(self):
        self.pb_list = QtWidgets.QProgressBar()
        self.pb_item = QtWidgets.QProgressBar()
        pbs = [self.pb_list, self.pb_item]

        for pb in pbs:
            pb.setRange(0, 100)
            # self.pb_progress.setVisible()
            self.statusbar.addPermanentWidget(pb)

    def _init_info(self):
        path_image: str = resource_path("tidal_dl_ng/ui/default_album_image.png")

        self.l_pm_cover.setPixmap(QtGui.QPixmap(path_image))

    def on_progress_reset(self):
        self.pb_list.setValue(0)
        self.pb_item.setValue(0)

    def on_statusbar_message(self, data: StatusbarMessage):
        self.statusbar.showMessage(data.message, data.timeout)

    def _log_output(self, text):
        display_msg = coloredlogs.converter.convert(text)

        cursor: QtGui.QTextCursor = self.te_debug.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertHtml(display_msg)

        self.te_debug.setTextCursor(cursor)
        self.te_debug.ensureCursorVisible()

    def _populate_quality(self, ui_target: QtWidgets.QComboBox, options: type[Quality | QualityVideo]):
        for item in options:
            ui_target.addItem(item.name, item)

    def _populate_search_types(self, ui_target: QtWidgets.QComboBox, options: SearchTypes):
        for item in options:
            if item:
                ui_target.addItem(item.__name__, item)

        self.cb_search_type.setCurrentIndex(2)

    def handle_filter_activated(self):
        header: FilterHeader = self.tr_results.header()
        filters = []

        for i in range(header.count()):
            text: str = header.filter_text(i)

            if text:
                filters.append((i, text))

        proxy_model: HumanProxyModel = self.tr_results.model()
        proxy_model.filters = filters

    def _init_tree_results(self, tree: QtWidgets.QTreeView, model: QtGui.QStandardItemModel) -> None:
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
        tree.setColumnWidth(2, 150)
        tree.setColumnWidth(3, 150)
        tree.setColumnWidth(4, 150)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        # Connect the contextmenu
        tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        tree.customContextMenuRequested.connect(self.menu_context_tree_results)

    def _init_tree_results_model(self, model: QtGui.QStandardItemModel) -> None:
        labels_column: [str] = ["#", "obj", "Artist", "Title", "Album", "Duration", "Quality", "Date"]

        model.setColumnCount(len(labels_column))
        model.setRowCount(0)
        model.setHorizontalHeaderLabels(labels_column)

    def _init_tree_queue(self, tree: QtWidgets.QTableWidget):
        tree.setColumnHidden(1, True)
        tree.setColumnWidth(2, 200)

        header = tree.header()

        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setStretchLastSection(False)

    def tidal_user_lists(self):
        # Start loading spinner
        self.s_spinner_start.emit(self.tr_lists_user)
        self.s_pb_reload_status.emit(False)

        user_all: [Playlist | UserPlaylist | Mix] = user_media_lists(self.tidal.session)

        self.s_populate_tree_lists.emit(user_all)

    def on_populate_tree_lists(self, user_lists: [Playlist | UserPlaylist | Mix]):
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

        # Populate dynamic user lists
        for item in user_lists:
            if isinstance(item, UserPlaylist | Playlist):
                twi_child = QtWidgets.QTreeWidgetItem(twi_playlists)
                name: str = item.name
                description: str = f" {item.description}" if item.description else ""
                info: str = f"({item.num_tracks + item.num_videos} Tracks){description}"
            elif isinstance(item, Mix):
                twi_child = QtWidgets.QTreeWidgetItem(twi_mixes)
                name: str = item.title
                info: str = item.sub_title
            else:
                continue

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

    def _init_tree_lists(self, tree: QtWidgets.QTreeWidget):
        # Adjust Tree.
        tree.setColumnWidth(0, 200)
        tree.setColumnHidden(1, True)
        tree.setColumnWidth(2, 300)
        tree.expandAll()

        # Connect the contextmenu
        tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        tree.customContextMenuRequested.connect(self.menu_context_tree_lists)

    def on_update_check(self, on_startup: bool = True):
        is_available, info = update_available()

        if (on_startup and is_available) or not on_startup:
            self.s_update_show.emit(True, is_available, info)

    def apply_settings(self, settings: Settings):
        l_cb = [
            {"element": self.cb_quality_audio, "setting": settings.data.quality_audio, "default_id": 1},
            {"element": self.cb_quality_video, "setting": settings.data.quality_video, "default_id": 0},
        ]

        for item in l_cb:
            idx = item["element"].findData(item["setting"])

            if idx > -1:
                item["element"].setCurrentIndex(idx)
            else:
                item["element"].setCurrentIndex(item["default_id"])

    def on_spinner_start(self, parent: QtWidgets.QWidget):
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

    def on_spinner_stop(self):
        # Stop all spinners
        for spinner in list(self.spinners.values()):
            spinner.stop()
            spinner.deleteLater()

        self.spinners.clear()

    def menu_context_tree_lists(self, point: QtCore.QPoint):
        # Infos about the node selected.
        index = self.tr_lists_user.indexAt(point)

        # Do not open menu if something went wrong or a parent node is clicked.
        if not index.isValid() or not index.parent().data():
            return

        # We build the menu.
        menu = QtWidgets.QMenu()
        menu.addAction("Download Playlist", lambda: self.thread_download_list_media(point))
        menu.addAction("Copy Share URL", lambda: self.on_copy_url_share(self.tr_lists_user, point))

        menu.exec(self.tr_lists_user.mapToGlobal(point))

    def menu_context_tree_results(self, point: QtCore.QPoint):
        # Infos about the node selected.
        index = self.tr_results.indexAt(point)

        # Do not open menu if something went wrong or a parent node is clicked.
        if not index.isValid():
            return

        # We build the menu.
        menu = QtWidgets.QMenu()
        menu.addAction("Copy Share URL", lambda: self.on_copy_url_share(self.tr_results, point))

        menu.exec(self.tr_results.mapToGlobal(point))

    def thread_download_list_media(self, point: QtCore.QPoint):
        self.thread_it(self.on_download_list_media, point)

    def on_copy_url_share(self, tree_target: QtWidgets.QTreeWidget | QtWidgets.QTreeView, point: QtCore.QPoint = None):
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

    def on_download_list_media(self, point: QtCore.QPoint = None):
        items: [QtWidgets.QTreeWidgetItem]

        if point:
            items = [self.tr_lists_user.itemAt(point)]
        else:
            items = self.tr_lists_user.selectedItems()

            if len(items) == 0:
                logger_gui.error("Please select a mix or playlist first.")

        for item in items:
            media = get_user_list_media_item(item)
            queue_dl_item: QueueDownloadItem | False = self.media_to_queue_download_model(media)

            if queue_dl_item:
                self.queue_download_media(queue_dl_item)

    def search_populate_results(self, query: str, type_media: SearchTypes):
        self.model_tr_results.removeRows(0, self.model_tr_results.rowCount())

        results: [ResultItem] = self.search(query, [type_media])

        self.populate_tree_results(results)

    def populate_tree_results(self, results: [ResultItem], parent: QtGui.QStandardItem = None):
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
        self.model_tr_results.appendRow(item_child)

    def on_settings_save(self):
        self.settings.save()
        self.apply_settings(self.settings)
        self._init_dl()

    def search(self, query: str, types_media: SearchTypes) -> [ResultItem]:
        query = query.strip()

        # If a direct link was searched for, skip search and create the object from the link directly.
        if "http" in query:
            media_type = get_tidal_media_type(query)
            item_id = get_tidal_media_id(query)

            try:
                media = instantiate_media(self.tidal.session, media_type, item_id)
            except:
                logger_gui.error(f"Media not found (ID: {item_id}). Maybe it is not available anymore.")

                media = None

            result_search = {"direct": [media]}
        else:
            result_search: dict[str, [SearchTypes]] = search_results_all(
                session=self.tidal.session, needle=query, types_media=types_media
            )

        result: [ResultItem] = []

        for _media_type, l_media in result_search.items():
            if isinstance(l_media, list):
                result = result + self.search_result_to_model(l_media)

        return result

    def search_result_to_model(self, items: [*SearchTypes]) -> [ResultItem]:
        result = []

        for idx, item in enumerate(items):
            if not item:
                continue

            explicit: str = ""
            # Check if item is available on TIDAL.
            if hasattr(item, "available") and not item.available:
                continue

            if isinstance(item, Track | Video | Album):
                explicit = " 🅴" if item.explicit else ""

            date_user_added: str = item.user_date_added.strftime("%Y-%m-%d_%H:%M") if item.user_date_added else ""
            date_release: str = (
                item.album.release_date.strftime("%Y-%m-%d_%H:%M")
                if hasattr(item, "album") and item.album and item.album.release_date
                else (
                    item.release_date.strftime("%Y-%m-%d_%H:%M")
                    if hasattr(item, "release_date") and item.release_date
                    else ""
                )
            )

            if isinstance(item, Track):
                result_item: ResultItem = ResultItem(
                    position=idx,
                    artist=name_builder_artist(item),
                    title=f"{name_builder_title(item)}{explicit}",
                    album=item.album.name,
                    duration_sec=item.duration,
                    obj=item,
                    quality=quality_audio_highest(item),
                    explicit=bool(item.explicit),
                    date_user_added=date_user_added,
                    date_release=date_release,
                )

                result.append(result_item)
            elif isinstance(item, Video):
                result_item: ResultItem = ResultItem(
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

                result.append(result_item)
            elif isinstance(item, Playlist):
                result_item: ResultItem = ResultItem(
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

                result.append(result_item)
            elif isinstance(item, Album):
                result_item: ResultItem = ResultItem(
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

                result.append(result_item)
            elif isinstance(item, Mix):
                result_item: ResultItem = ResultItem(
                    position=idx,
                    artist=item.sub_title,
                    title=item.title,
                    album="",
                    # TODO: Calculate total duration.
                    duration_sec=-1,
                    obj=item,
                    quality="",
                    explicit=False,
                    date_user_added=date_user_added,
                    date_release=date_release,
                )

                result.append(result_item)
            elif isinstance(item, Artist):
                result_item: ResultItem = ResultItem(
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

                result.append(result_item)

        return result

    def media_to_queue_download_model(
        self, media: Artist | Track | Video | Album | Playlist | Mix
    ) -> QueueDownloadItem | bool:
        result: QueueDownloadItem | False
        name: str = ""
        quality_audio: Quality = self.settings.data.quality_audio
        quality_video: QualityVideo = self.settings.data.quality_video
        explicit: str = ""

        # Check if item is available on TIDAL.
        if hasattr(media, "available") and not media.available:
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

    def _init_signals(self):
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
        self.s_spinner_start[QtWidgets.QWidget].connect(self.on_spinner_start)
        self.s_spinner_stop.connect(self.on_spinner_stop)
        self.s_item_advance.connect(self.on_progress_item)
        self.s_item_name.connect(self.on_progress_item_name)
        self.s_list_name.connect(self.on_progress_list_name)
        self.s_list_advance.connect(self.on_progress_list)
        self.s_pb_reset.connect(self.on_progress_reset)
        self.s_populate_tree_lists.connect(self.on_populate_tree_lists)
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

        # Download Queue
        self.tr_queue_download.itemClicked.connect(self.on_queue_download_item_clicked)
        self.s_queue_download_item_downloading.connect(self.on_queue_download_item_downloading)
        self.s_queue_download_item_finished.connect(self.on_queue_download_item_finished)
        self.s_queue_download_item_failed.connect(self.on_queue_download_item_failed)
        self.s_queue_download_item_skipped.connect(self.on_queue_download_item_skipped)

    def _init_buttons(self):
        self.pb_queue_download_run()

    def on_logout(self):
        result: bool = self.tidal.logout()

        if result:
            sys.exit(0)

    def on_progress_list(self, value: float):
        self.pb_list.setValue(int(math.ceil(value)))

    def on_progress_item(self, value: float):
        self.pb_item.setValue(int(math.ceil(value)))

    def on_progress_item_name(self, value: str):
        self.pb_item.setFormat(f"%p% {value}")

    def on_progress_list_name(self, value: str):
        self.pb_list.setFormat(f"%p% {value}")

    def on_quality_set_audio(self, index):
        self.settings.data.quality_audio = Quality(self.cb_quality_audio.itemData(index))
        self.settings.save()

        if self.tidal:
            self.tidal.settings_apply()

    def on_quality_set_video(self, index):
        self.settings.data.quality_video = QualityVideo(self.cb_quality_video.itemData(index))
        self.settings.save()

        if self.tidal:
            self.tidal.settings_apply()

    def on_list_items_show(self, item: QtWidgets.QTreeWidgetItem):
        self.thread_it(self.list_items_show, item)

    def list_items_show(self, item: QtWidgets.QTreeWidgetItem):
        media_list: Album | Playlist | str = get_user_list_media_item(item)

        # Only if clicked item is not a top level item.
        if media_list:
            # Show spinner while loading list
            self.s_spinner_start.emit(self.tr_results)
            try:
                if isinstance(media_list, str) and media_list.startswith("fav_"):
                    function_list = favorite_function_factory(self.tidal, media_list)
                    self.list_items_show_result(favorite_function=function_list)
                else:
                    self.list_items_show_result(media_list)
                    # Load cover asynchronously to avoid blocking the GUI
                    self.thread_it(self.cover_show, media_list)
            finally:
                self.s_spinner_stop.emit()

    def on_result_item_clicked(self, index: QtCore.QModelIndex) -> None:
        media: Track | Video | Album | Artist = get_results_media_item(
            index, self.proxy_tr_results, self.model_tr_results
        )

        # Load cover asynchronously to avoid blocking the GUI
        self.thread_it(self.cover_show, media)

    def on_queue_download_item_clicked(self, item: QtWidgets.QTreeWidgetItem, column: int) -> None:
        media: Track | Video | Album | Artist | Mix | Playlist = get_queue_download_media(item)

        # Load cover asynchronously to avoid blocking the GUI
        self.thread_it(self.cover_show, media)

    def cover_show(self, media: Album | Playlist | Track | Video | Album | Artist) -> None:
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
        parent: QtGui.QStandardItem = None,
        favorite_function: Callable = None,
    ) -> None:
        if point:
            item = self.tr_lists_user.itemAt(point)
            media_list = get_user_list_media_item(item)

        # Get all results
        if favorite_function or isinstance(media_list, str):
            if isinstance(media_list, str):
                favorite_function = favorite_function_factory(self.tidal, media_list)

            media_items: [Track | Video | Album] = favorite_function()
        else:
            media_items: [Track | Video | Album] = items_results_all(media_list)

        result: [ResultItem] = self.search_result_to_model(media_items)

        self.populate_tree_results(result, parent=parent)

    def thread_it(self, fn: Callable, *args, **kwargs):
        # Any other args, kwargs are passed to the run function
        worker = Worker(fn, *args, **kwargs)

        # Execute
        self.threadpool.start(worker)

    def on_queue_download_clear_all(self):
        self.on_clear_queue_download(
            f"({QueueDownloadStatus.Waiting}|{QueueDownloadStatus.Finished}|{QueueDownloadStatus.Failed})"
        )

    def on_queue_download_clear_finished(self):
        self.on_clear_queue_download(f"[{QueueDownloadStatus.Finished}]")

    def on_clear_queue_download(self, regex: str):
        items: [QtWidgets.QTreeWidgetItem | None] = self.tr_queue_download.findItems(
            regex, QtCore.Qt.MatchFlag.MatchRegularExpression, column=0
        )

        for item in items:
            self.tr_queue_download.takeTopLevelItem(self.tr_queue_download.indexOfTopLevelItem(item))

    def on_queue_download_remove(self):
        items: [QtWidgets.QTreeWidgetItem | None] = self.tr_queue_download.selectedItems()

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

    def pb_queue_download_run(self):
        handling_app: HandlingApp = HandlingApp()

        handling_app.event_run.set()

        icon = QtGui.QIcon(QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.MediaPlaybackStart))
        self.pb_queue_download_toggle.setIcon(icon)
        self.pb_queue_download_toggle.setStyleSheet("background-color: #218838; color: #fff")

    def pb_queue_download_pause(self):
        handling_app: HandlingApp = HandlingApp()

        handling_app.event_run.clear()

        icon = QtGui.QIcon(QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.MediaPlaybackPause))
        self.pb_queue_download_toggle.setIcon(icon)
        self.pb_queue_download_toggle.setStyleSheet("background-color: #e0a800; color: #212529")

    # TODO: Must happen in main thread. Do not thread this.
    def on_download_results(self) -> None:
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
        handling_app: HandlingApp = HandlingApp()

        while not handling_app.event_abort.is_set():
            items: [QtWidgets.QTreeWidgetItem | None] = self.tr_queue_download.findItems(
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
        self.queue_download_item_status(item, QueueDownloadStatus.Downloading)

    def on_queue_download_item_finished(self, item: QtWidgets.QTreeWidgetItem) -> None:
        self.queue_download_item_status(item, QueueDownloadStatus.Finished)

    def on_queue_download_item_failed(self, item: QtWidgets.QTreeWidgetItem) -> None:
        self.queue_download_item_status(item, QueueDownloadStatus.Failed)

    def on_queue_download_item_skipped(self, item: QtWidgets.QTreeWidgetItem) -> None:
        self.queue_download_item_status(item, QueueDownloadStatus.Skipped)

    def queue_download_item_status(self, item: QtWidgets.QTreeWidgetItem, status: str) -> None:
        item.setText(0, status)

    def on_queue_download(
        self,
        media: Track | Album | Playlist | Video | Mix | Artist,
        quality_audio: Quality | None = None,
        quality_video: QualityVideo | None = None,
    ) -> QueueDownloadStatus:
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
        self, update_check: bool = False, update_available: bool = False, update_info: ReleaseLatest = None
    ) -> None:
        DialogVersion(self, update_check, update_available, update_info)

    def on_preferences(self) -> None:
        DialogPreferences(settings=self.settings, settings_save=self.s_settings_save, parent=self)

    def on_tr_results_expanded(self, index: QtCore.QModelIndex) -> None:
        self.thread_it(self.tr_results_expanded, index)

    def tr_results_expanded(self, index: QtCore.QModelIndex) -> None:
        # If the child is a dummy the list_item has not been expanded before
        item: QtGui.QStandardItem = self.model_tr_results.itemFromIndex(self.proxy_tr_results.mapToSource(index))
        load_children: bool = not item.child(0, 0).isEnabled()

        if load_children:
            item.removeRow(0)
            media_list: [Mix | Album | Playlist | Artist] = get_results_media_item(
                index, self.proxy_tr_results, self.model_tr_results
            )

            # Show spinner while loading children
            self.s_spinner_start.emit(self.tr_results)

            try:
                self.list_items_show_result(media_list=media_list, parent=item)
            finally:
                self.s_spinner_stop.emit()

    def button_reload_status(self, status: bool):
        button_text: str = "Reloading..."

        if status:
            button_text = "Reload"

        self.pb_reload_user_lists.setEnabled(status)
        self.pb_reload_user_lists.setText(button_text)

    def closeEvent(self, event):
        self.shutdown = True

        handling_app: HandlingApp = HandlingApp()
        handling_app.event_abort.set()

        event.accept()


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
    pixmap: QtGui.QPixmap = QtGui.QPixmap("tidal_dl_ng/ui/icon.png")
    icon: QtGui.QIcon = QtGui.QIcon(pixmap)

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
