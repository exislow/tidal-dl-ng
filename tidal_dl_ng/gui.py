import math
import sys
from collections.abc import Callable

from requests.exceptions import HTTPError

from tidal_dl_ng import __version__
from tidal_dl_ng.dialog import DialogLogin, DialogPreferences, DialogVersion
from tidal_dl_ng.helper.path import get_format_template
from tidal_dl_ng.helper.tidal import items_results_all, search_results_all, user_media_lists

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
from tidalapi.session import SearchTypes

from tidal_dl_ng.config import Settings, Tidal
from tidal_dl_ng.constants import QualityVideo, TidalLists
from tidal_dl_ng.download import Download
from tidal_dl_ng.logger import XStream, logger_gui
from tidal_dl_ng.model.gui_data import ProgressBars, ResultItem, StatusbarMessage
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

    def __init__(self, tidal: Tidal | None = None):
        super().__init__()
        self.setupUi(self)
        # self.setGeometry(50, 50, 500, 300)
        self.setWindowTitle("TIDAL Downloader Next Gen!")

        # Logging redirect.
        XStream.stdout().messageWritten.connect(self._log_output)
        # XStream.stderr().messageWritten.connect(self._log_output)

        self.settings = Settings()
        self.threadpool = QtCore.QThreadPool()

        self._init_tree_results(self.tr_results)
        self._init_tree_lists(self.tr_lists_user)
        self._init_progressbar()
        self._populate_quality(self.cb_quality_audio, Quality)
        self._populate_quality(self.cb_quality_video, QualityVideo)
        self._populate_search_types(self.cb_search_type, SearchTypes)
        self.apply_settings(self.settings)
        self._init_signals()
        self.init_tidal(tidal)

        logger_gui.debug("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())
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

            self.thread_it(self.tidal_user_lists)

    def _init_progressbar(self):
        self.pb_list = QtWidgets.QProgressBar()
        self.pb_item = QtWidgets.QProgressBar()
        pbs = [self.pb_list, self.pb_item]

        for pb in pbs:
            pb.setRange(0, 100)
            # self.pb_progress.setVisible()
            self.statusbar.addPermanentWidget(pb)

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
            if item and item.__name__ != "Artist":
                ui_target.addItem(item.__name__, item)

        self.cb_search_type.setCurrentIndex(1)

    def _init_tree_results(self, tree: QtWidgets.QTableWidget):
        tree.setColumnHidden(5, True)
        tree.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)

    def tidal_user_lists(self):
        # Start loading spinner
        self.s_spinner_start.emit(self.tr_lists_user)
        self.s_pb_reload_status.emit(False)

        user_all: [Playlist | UserPlaylist | Mix] = user_media_lists(self.tidal.session)

        self.s_populate_tree_lists.emit(user_all)

    def on_populate_tree_lists(self, user_lists: [Playlist | UserPlaylist | Mix]):
        self.tr_results.clear()

        twi_playlists: QtWidgets.QTreeWidgetItem = self.tr_lists_user.findItems(
            TidalLists.PLAYLISTS.value, QtCore.Qt.MatchExactly, 0
        )[0]
        twi_mixes: QtWidgets.QTreeWidgetItem = self.tr_lists_user.findItems(
            TidalLists.FAVORITES.value, QtCore.Qt.MatchExactly, 0
        )[0]
        twi_favorites: QtWidgets.QTreeWidgetItem = self.tr_lists_user.findItems(
            TidalLists.MIXES.value, QtCore.Qt.MatchExactly, 0
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
            twi_child.setText(1, info)
            twi_child.setData(3, QtCore.Qt.ItemDataRole.UserRole, item)

        # Stop load spinner
        self.s_spinner_stop.emit()
        self.s_pb_reload_status.emit(True)

    def _init_tree_lists(self, tree: QtWidgets.QTreeWidget):
        # Adjust Tree.
        tree.setColumnWidth(0, 200)
        tree.setColumnWidth(1, 300)
        tree.setColumnHidden(2, True)
        tree.expandAll()

        # Connect the contextmenu
        tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        tree.customContextMenuRequested.connect(self.menu_context_tree_lists)

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

    def on_download_list_media(self, point: QtCore.QPoint):
        self.b_download.setEnabled(False)
        self.b_download.setText("Downloading...")

        item = self.tr_lists_user.itemAt(point)
        media = item.data(3, QtCore.Qt.ItemDataRole.UserRole)

        self.download(media, self.dl)

        self.b_download.setText("Download")
        self.b_download.setEnabled(True)

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

    def populate_tree_result_child(self, item: [Mix | Album | Playlist], index_count_digits: int):
        # Format seconds to mm:ss.
        m, s = divmod(item.duration_sec, 60)
        duration: str = f"{m:02d}:{s:02d}"
        # Since sorting happens only by string, we need to pad the index and add 1 (to avoid start at 0)
        index: str = str(item.position + 1).zfill(index_count_digits)

        # Populate child
        child = QtWidgets.QTreeWidgetItem()
        child.setText(0, index)
        child.setText(1, item.artist)
        child.setText(2, item.title)
        child.setText(3, item.album)
        child.setText(4, duration)
        child.setData(5, QtCore.Qt.ItemDataRole.UserRole, item.obj)

        if isinstance(item.obj, Mix | Playlist | Album):
            # Add empty dummy child, so expansion arrow will appear. This Child will be replaced on expansion.
            child.addChild(QtWidgets.QTreeWidgetItem())

        return child

    def on_tr_results_add_top_level_item(self, widget_item: QtWidgets.QTreeWidgetItem):
        self.tr_results.addTopLevelItem(widget_item)

    def on_settings_save(self):
        self.settings.save()
        self.apply_settings(self.settings)

    def search(self, query: str, types_media: SearchTypes) -> [ResultItem]:
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
            if isinstance(item, Track):
                result_item: ResultItem = ResultItem(
                    position=idx,
                    artist=", ".join(artist.name for artist in item.artists),
                    title=item.name,
                    album=item.album.name,
                    duration_sec=item.duration,
                    obj=item,
                )

                result.append(result_item)
            elif isinstance(item, Video):
                result_item: ResultItem = ResultItem(
                    position=idx,
                    artist=", ".join(artist.name for artist in item.artists),
                    title=item.name,
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
                    artist=", ".join(artist.name for artist in item.artists),
                    title="",
                    album=item.name,
                    duration_sec=item.duration,
                    obj=item,
                )

                result.append(result_item)

        return result

    def _init_signals(self):
        self.b_download.clicked.connect(lambda: self.thread_it(self.on_download_results))
        self.l_search.returnPressed.connect(
            lambda: self.search_populate_results(self.l_search.text(), self.cb_search_type.currentData())
        )
        self.b_search.clicked.connect(
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
        self.pb_reload_user_lists.clicked.connect(lambda x: self.thread_it(self.tidal_user_lists))
        self.s_pb_reload_status.connect(self.button_reload_status)

        # Menubar
        self.a_exit.triggered.connect(sys.exit)
        self.a_version.triggered.connect(self.on_version)
        self.a_preferences.triggered.connect(self.on_preferences)
        self.a_logout.triggered.connect(self.on_logout)

        # Results
        self.tr_results.itemExpanded.connect(self.on_tr_results_expanded)

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
        self.settings.data.quality_audio = Quality(self.cb_quality_audio.itemData(index).value)
        self.settings.save()

        if self.tidal:
            self.tidal.settings_apply()

    def on_quality_set_video(self, index):
        self.settings.data.quality_video = QualityVideo(self.cb_quality_video.itemData(index).value)
        self.settings.save()

        if self.tidal:
            self.tidal.settings_apply()

    def on_list_items_show(self, item: QtWidgets.QTreeWidgetItem):
        media_list: Album | Playlist = item.data(3, QtCore.Qt.ItemDataRole.UserRole)

        # Only if clicked item is not a top level item.
        if media_list:
            self.list_items_show_result(media_list)

    def list_items_show_result(
        self,
        media_list: Album | Playlist | Mix | None = None,
        point: QtCore.QPoint | None = None,
        parent: QtWidgets.QTreeWidgetItem = None,
    ) -> None:
        if point:
            item = self.tr_lists_user.itemAt(point)
            media_list = item.data(3, QtCore.Qt.ItemDataRole.UserRole)

        # Get all results
        media_items: [Track | Video] = items_results_all(media_list)
        result: [ResultItem] = self.search_result_to_model(media_items)

        self.populate_tree_results(result, parent=parent)

    def thread_it(self, fn: Callable, *args, **kwargs):
        # Any other args, kwargs are passed to the run function
        worker = Worker(fn, *args, **kwargs)

        # Execute
        self.threadpool.start(worker)

    def on_download_results(self):
        self.b_download.setEnabled(False)
        self.b_download.setText("Downloading...")

        items: [QtWidgets.QTreeWidgetItem] = self.tr_results.selectedItems()

        if len(items) == 0:
            logger_gui.error("Please select a row first.")
        else:
            items_pos_last = len(items) - 1

            for item in items:
                media: Track | Album | Playlist | Video = item.data(5, QtCore.Qt.ItemDataRole.UserRole)
                # Skip only if Track item, skip option set and the item is not the last in the list.
                download_delay: bool = bool(
                    isinstance(media, Track | Video)
                    and self.settings.data.download_delay
                    and items.index(item) < items_pos_last
                )

                self.download(media, self.dl, delay_track=download_delay)

        self.b_download.setText("Download")
        self.b_download.setEnabled(True)

    def download(self, media: Track | Album | Playlist | Video | Mix, dl: Download, delay_track: bool = False) -> None:
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

    def on_version(self) -> None:
        DialogVersion(self)

    def on_preferences(self) -> None:
        DialogPreferences(settings=self.settings, settings_save=self.s_settings_save, parent=self)

    def on_tr_results_expanded(self, child: QtWidgets.QTreeWidgetItem) -> None:
        child.removeChild(child.child(0))
        media_list: [Mix | Album | Playlist] = child.data(5, QtCore.Qt.ItemDataRole.UserRole)

        self.list_items_show_result(media_list=media_list, parent=child)

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
    qdarktheme.setup_theme()

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

    sys.exit(app.exec())


if __name__ == "__main__":
    gui_activate()
