import math
import sys
import time
from collections.abc import Callable

from requests.exceptions import HTTPError

from tidal_dl_ng import __version__, update_available
from tidal_dl_ng.dialog import DialogLogin, DialogPreferences, DialogVersion
from tidal_dl_ng.helper.gui import (
    get_queue_download_media,
    get_results_media_item,
    get_user_list_media_item,
    set_queue_download_media,
    set_results_media,
    set_user_list_media,
)
from tidal_dl_ng.helper.path import get_format_template, resource_path
from tidal_dl_ng.helper.tidal import (
    get_tidal_media_id,
    get_tidal_media_type,
    instantiate_media,
    items_results_all,
    name_builder_artist,
    name_builder_title,
    search_results_all,
    user_media_lists,
)
from tidal_dl_ng.metadata import Metadata

try:
    import qdarktheme
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError as e:
    print(e)
    print("Qt dependencies missing. Cannot start GUI. Please execute: 'pip install pyside6 pyqtdarktheme'")
    sys.exit(1)

import coloredlogs.converter
from rich.progress import Progress
from tidalapi import Album, Mix, Playlist, Quality, Track, UserPlaylist, Video
from tidalapi.artist import Artist
from tidalapi.session import SearchTypes

from tidal_dl_ng.config import Settings, Tidal
from tidal_dl_ng.constants import QualityVideo, QueueDownloadStatus, TidalLists
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
    spinner: QtWaitingSpinner
    cover_url_current: str = ""
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
    s_update_check: QtCore.Signal = QtCore.Signal()
    s_update_show: QtCore.Signal = QtCore.Signal(bool, bool, object)
    s_queue_download_item_downloading: QtCore.Signal = QtCore.Signal(object)
    s_queue_download_item_finished: QtCore.Signal = QtCore.Signal(object)
    s_queue_download_item_failed: QtCore.Signal = QtCore.Signal(object)

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
        self._init_tree_results(self.tr_results)
        self._init_tree_lists(self.tr_lists_user)
        self._init_tree_queue(self.tr_queue_download)
        self._init_info()
        self._init_progressbar()
        self._populate_quality(self.cb_quality_audio, Quality)
        self._populate_quality(self.cb_quality_video, QualityVideo)
        self._populate_search_types(self.cb_search_type, SearchTypes)
        self.apply_settings(self.settings)
        self._init_signals()
        self.init_tidal(tidal)

        logger_gui.debug("All setup.")

    def init_tidal(self, tidal: Tidal = None):
        result: bool = False

        if tidal:
            self.tidal = tidal
            result = True
        else:
            self.tidal = Tidal(self.settings)
            result = self.tidal.login_token()

            if not result:
                hint: str = "Watiting for user input."
                while not result:
                    url_login = self.tidal.session.pkce_login_url()
                    d_login: DialogLogin = DialogLogin(url_login=url_login, hint=hint, parent=self)
                    url_redirect: str = d_login.url_redirect

                    if d_login.return_code == 1:
                        try:
                            token: dict[str, str | int] = self.tidal.session.pkce_get_auth_token(url_redirect)
                            self.tidal.session.process_auth_token(token)
                            self.tidal.login_finalize()

                            result = True
                            logger_gui.info("Login not successful. Have fun!")
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
        self.dl = Download(
            session=self.tidal.session,
            skip_existing=self.tidal.settings.data.skip_existing,
            path_base=self.settings.data.download_base_path,
            fn_logger=logger_gui,
            progress_gui=data_pb,
            progress=progress,
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
        self.statusbar.showMessage(data.message, data.timout)

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

    def _init_tree_results(self, tree: QtWidgets.QTableWidget):
        tree.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)
        tree.setColumnHidden(1, True)
        tree.setColumnWidth(2, 150)
        tree.setColumnWidth(3, 150)
        tree.setColumnWidth(4, 150)

        header = tree.header()

        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)

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
            TidalLists.Favorites, QtCore.Qt.MatchExactly, 0
        )[0]
        twi_favorites: QtWidgets.QTreeWidgetItem = self.tr_lists_user.findItems(
            TidalLists.Mixes, QtCore.Qt.MatchExactly, 0
        )[0]

        # Remove all children if present
        for twi in [twi_playlists, twi_mixes, twi_favorites]:
            for i in reversed(range(twi.childCount())):
                twi.removeChild(twi.child(i))

        for item in user_lists:
            if isinstance(item, UserPlaylist):
                twi_child = QtWidgets.QTreeWidgetItem(twi_playlists)
                name: str = item.name
                info: str = f"({item.num_tracks + item.num_videos} Tracks)"
            elif isinstance(item, Playlist):
                twi_child = QtWidgets.QTreeWidgetItem(twi_mixes)
                name: str = item.name
                info: str = f"({item.num_tracks + item.num_videos} Tracks) {item.description}"
            elif isinstance(item, Mix):
                twi_child = QtWidgets.QTreeWidgetItem(twi_favorites)
                name: str = item.title
                info: str = item.sub_title

            twi_child.setText(0, name)
            set_user_list_media(twi_child, item)
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

    def on_update_check(self):
        is_available, info = update_available()

        if is_available:
            self.s_update_show.emit(True, is_available, info)

    def apply_settings(self, settings: Settings):
        l_cb = [
            {"element": self.cb_quality_audio, "setting": settings.data.quality_audio.name, "default_id": 1},
            {"element": self.cb_quality_video, "setting": settings.data.quality_video.name, "default_id": 0},
        ]

        for item in l_cb:
            idx = item["element"].findText(item["setting"])

            if idx > -1:
                item["element"].setCurrentIndex(idx)
            else:
                item["element"].setCurrentIndex(item["default_id"])

    def on_spinner_start(self, parent: QtWidgets.QWidget):
        self.spinner = QtWaitingSpinner(parent, True, True)
        self.spinner.setColor(QtGui.QColor(255, 255, 255))
        self.spinner.start()

    def on_spinner_stop(self):
        self.spinner.stop()
        self.spinner = None

    def menu_context_tree_lists(self, point):
        # Infos about the node selected.
        index = self.tr_lists_user.indexAt(point)

        # Do not open menu if something went wrong or a parent node is clicked.
        if not index.isValid() or not index.parent().data():
            return

        # We build the menu.
        menu = QtWidgets.QMenu()
        menu.addAction("Download Playlist", lambda: self.thread_download_list_media(point))

        menu.exec(self.tr_lists_user.mapToGlobal(point))

    def thread_download_list_media(self, point):
        self.thread_it(self.on_download_list_media, point)
        self.thread_it(self.list_items_show_result, point=point)

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
        self.tr_results.clear()

        results: [ResultItem] = self.search(query, [type_media])

        self.populate_tree_results(results)

    def populate_tree_results(self, results: [ResultItem], parent: QtWidgets.QTreeWidgetItem = None):
        if not parent:
            self.tr_results.clear()

        # Count how many digits the list length has,
        count_digits: int = int(math.log10(len(results) if results else 1)) + 1

        for item in results:
            child = self.populate_tree_result_child(item=item, index_count_digits=count_digits)

            if parent:
                parent.addChild(child)
            else:
                self.s_tr_results_add_top_level_item.emit(child)

    def populate_tree_result_child(self, item: [Track | Video | Mix | Album | Playlist], index_count_digits: int):
        duration: str = ""

        # TODO: Duration needs to be calculated later to properly fill with zeros.
        if item.duration_sec > -1:
            # Format seconds to mm:ss.
            m, s = divmod(item.duration_sec, 60)
            duration: str = f"{m:02d}:{s:02d}"

        # Since sorting happens only by string, we need to pad the index and add 1 (to avoid start at 0)
        index: str = str(item.position + 1).zfill(index_count_digits)

        # Populate child
        child: QtWidgets.QTreeWidgetItem = QtWidgets.QTreeWidgetItem()
        child.setText(0, index)
        set_results_media(child, item.obj)
        child.setText(2, item.artist)
        child.setText(3, item.title)
        child.setText(4, item.album)
        child.setText(5, duration)

        if isinstance(item.obj, Mix | Playlist | Album | Artist):
            # Add a disabled dummy child, so expansion arrow will appear. This Child will be replaced on expansion.
            child_dummy: QtWidgets.QTreeWidgetItem = QtWidgets.QTreeWidgetItem()

            child_dummy.setDisabled(True)
            child.addChild(child_dummy)

        return child

    def on_tr_results_add_top_level_item(self, widget_item: QtWidgets.QTreeWidgetItem):
        self.tr_results.addTopLevelItem(widget_item)

    def on_settings_save(self):
        self.settings.save()
        self.apply_settings(self.settings)
        self._init_dl()

    def search(self, query: str, types_media: SearchTypes) -> [ResultItem]:
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
            # Check if item is available on TIDAL.
            if hasattr(item, "available") and not item.available:
                continue

            if isinstance(item, Track):
                result_item: ResultItem = ResultItem(
                    position=idx,
                    artist=name_builder_artist(item),
                    title=name_builder_title(item),
                    album=item.album.name,
                    duration_sec=item.duration,
                    obj=item,
                )

                result.append(result_item)
            elif isinstance(item, Video):
                result_item: ResultItem = ResultItem(
                    position=idx,
                    artist=name_builder_artist(item),
                    title=name_builder_title(item),
                    album=item.album.name if item.album else "",
                    duration_sec=item.duration,
                    obj=item,
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
                )

                result.append(result_item)
            elif isinstance(item, Album):
                result_item: ResultItem = ResultItem(
                    position=idx,
                    artist=name_builder_artist(item),
                    title="",
                    album=item.name,
                    duration_sec=item.duration,
                    obj=item,
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
                )

                result.append(result_item)

        return result

    def media_to_queue_download_model(
        self, media: Artist | Track | Video | Album | Playlist | Mix
    ) -> QueueDownloadItem | bool:
        result: QueueDownloadItem | False
        name: str = ""

        # Check if item is available on TIDAL.
        if hasattr(media, "available") and not media.available:
            return False

        if isinstance(media, Track | Video):
            name = f"{name_builder_artist(media)} - {name_builder_title(media)}"
        elif isinstance(media, Playlist | Artist):
            name = media.name
        elif isinstance(media, Album):
            name = f"{name_builder_artist(media)} - {media.name}"
        elif isinstance(media, Mix):
            name = media.title

        if name:
            result = QueueDownloadItem(
                name=name,
                quality="<quality>",
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
        self.a_exit.triggered.connect(sys.exit)
        self.a_version.triggered.connect(self.on_version)
        self.a_preferences.triggered.connect(self.on_preferences)
        self.a_logout.triggered.connect(self.on_logout)
        self.a_updates_check.triggered.connect(self.on_update_check)

        # Results
        self.tr_results.itemExpanded.connect(self.on_tr_results_expanded)
        self.tr_results.itemClicked.connect(self.on_result_item_clicked)

        # Download Queue
        self.tr_queue_download.itemClicked.connect(self.on_queue_download_item_clicked)
        self.s_queue_download_item_downloading.connect(self.on_queue_download_item_downloading)
        self.s_queue_download_item_finished.connect(self.on_queue_download_item_finished)
        self.s_queue_download_item_failed.connect(self.on_queue_download_item_failed)

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
        media_list: Album | Playlist = get_user_list_media_item(item)

        # Only if clicked item is not a top level item.
        if media_list:
            self.list_items_show_result(media_list)
            self.cover_show(media_list)

    def on_result_item_clicked(self, item: QtWidgets.QTreeWidgetItem, column: int) -> None:
        media: Track | Video | Album | Artist = get_results_media_item(item)

        self.cover_show(media)

    def on_queue_download_item_clicked(self, item: QtWidgets.QTreeWidgetItem, column: int) -> None:
        media: Track | Video | Album | Artist | Mix | Playlist = get_queue_download_media(item)

        self.cover_show(media)

    def on_download_item_clicked(self, item: QtWidgets.QTreeWidgetItem, column: int) -> None:
        media: Track | Video | Album | Artist = get_results_media_item(item)

        self.cover_show(media)

    def cover_show(self, media: Album | Playlist | Track | Video | Album | Artist) -> None:
        cover_url: str

        try:
            cover_url = media.album.image()
        except:
            try:
                cover_url = media.image()
            except:
                logger_gui.info(f"No cover available (media ID: {media.id}).")

        if cover_url and self.cover_url_current != cover_url:
            self.cover_url_current = cover_url
            data_cover: bytes = Metadata.cover_data(cover_url)
            pixmap: QtGui.QPixmap = QtGui.QPixmap()
            pixmap.loadFromData(data_cover)
            self.l_pm_cover.setPixmap(pixmap)

    def list_items_show_result(
        self,
        media_list: Album | Playlist | Mix | Artist | None = None,
        point: QtCore.QPoint | None = None,
        parent: QtWidgets.QTreeWidgetItem = None,
    ) -> None:
        if point:
            item = self.tr_lists_user.itemAt(point)
            media_list = get_user_list_media_item(item)

        # Get all results
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

    # TODO: Must happen in main thread. Do not thread this.
    def on_download_results(self) -> None:
        items: [QtWidgets.QTreeWidgetItem | None] = self.tr_results.selectedItems()

        if len(items) == 0:
            logger_gui.error("Please select a row first.")
        else:
            for item in items:
                media: Track | Album | Playlist | Video | Artist = get_results_media_item(item)
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
        child.setText(4, queue_dl_item.quality)
        self.tr_queue_download.addTopLevelItem(child)

    def watcher_queue_download(self) -> None:
        while True:
            items: [QtWidgets.QTreeWidgetItem | None] = self.tr_queue_download.findItems(
                QueueDownloadStatus.Waiting, QtCore.Qt.MatchFlag.MatchExactly, column=0
            )

            if len(items) > 0:
                item: QtWidgets.QTreeWidgetItem = items[0]
                media: Track | Album | Playlist | Video | Mix | Artist = get_queue_download_media(item)

                try:
                    self.s_queue_download_item_downloading.emit(item)
                    self.on_queue_download(media)
                    self.s_queue_download_item_finished.emit(item)
                except:
                    self.s_queue_download_item_failed.emit(item)
            else:
                time.sleep(2)

    def on_queue_download_item_downloading(self, item: QtWidgets.QTreeWidgetItem) -> None:
        self.queue_download_item_status(item, QueueDownloadStatus.Downloading)

    def on_queue_download_item_finished(self, item: QtWidgets.QTreeWidgetItem) -> None:
        self.queue_download_item_status(item, QueueDownloadStatus.Finished)

    def on_queue_download_item_failed(self, item: QtWidgets.QTreeWidgetItem) -> None:
        self.queue_download_item_status(item, QueueDownloadStatus.Failed)

    def queue_download_item_status(self, item: QtWidgets.QTreeWidgetItem, status: str) -> None:
        item.setText(0, status)

    def on_queue_download(self, media: Track | Album | Playlist | Video | Mix | Artist) -> None:
        items_media: [Track | Album | Playlist | Video | Mix | Artist]

        if isinstance(media, Artist):
            items_media: [Album] = items_results_all(media)
        else:
            items_media = [media]

        download_delay: bool = bool(isinstance(media, Track | Video) and self.settings.data.download_delay)

        for item_media in items_media:
            self.download(item_media, self.dl, delay_track=download_delay)

    def download(
        self, media: Track | Album | Playlist | Video | Mix | Artist, dl: Download, delay_track: bool = False
    ) -> None:
        self.s_pb_reset.emit()
        self.s_statusbar_message.emit(StatusbarMessage(message="Download started..."))

        file_template = get_format_template(media, self.settings)

        if isinstance(media, Track | Video):
            dl.item(media=media, file_template=file_template, download_delay=delay_track)
        elif isinstance(media, Album | Playlist | Mix):
            dl.items(
                media=media,
                file_template=file_template,
                video_download=self.settings.data.video_download,
                download_delay=self.settings.data.download_delay,
            )

        self.s_statusbar_message.emit(StatusbarMessage(message="Download finished.", timout=2000))

    def on_version(
        self, update_check: bool = False, update_available: bool = False, update_info: ReleaseLatest = None
    ) -> None:
        DialogVersion(self, update_check, update_available, update_info)

    def on_preferences(self) -> None:
        DialogPreferences(settings=self.settings, settings_save=self.s_settings_save, parent=self)

    def on_tr_results_expanded(self, list_item: QtWidgets.QTreeWidgetItem) -> None:
        # If the child is a dummy the list_item has not been expanded before
        load_children: bool = list_item.child(0).isDisabled()

        if load_children:
            list_item.removeChild(list_item.child(0))
            media_list: [Mix | Album | Playlist | Artist] = list_item.data(1, QtCore.Qt.ItemDataRole.UserRole)

            self.list_items_show_result(media_list=media_list, parent=list_item)

    def button_reload_status(self, status: bool):
        button_text: str = "Reloading..."
        if status:
            button_text = "Reload"

        self.pb_reload_user_lists.setEnabled(status)
        self.pb_reload_user_lists.setText(button_text)


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
    window.s_update_check.emit()

    sys.exit(app.exec())


if __name__ == "__main__":
    gui_activate()
