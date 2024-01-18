import math
import sys
from collections.abc import Callable

from helper.tidal import items_all_results, search_all_results

from tidal_dl_ng.helper.path import get_format_template

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
from tidal_dl_ng.model.gui_data import ProgressBars, ResultSearch
from tidal_dl_ng.ui.main import Ui_MainWindow
from tidal_dl_ng.ui.spinner import QtWaitingSpinner
from tidal_dl_ng.worker import Worker


# TODO: Make more use of Exceptions
# TODO: Add File -> Version
class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    settings: Settings = None
    tidal: Tidal = None
    dl: Download = None
    threadpool: QtCore.QThreadPool = None
    spinner: QtWaitingSpinner = None
    spinner_start: QtCore.Signal = QtCore.Signal(QtWidgets.QWidget)
    spinner_stop: QtCore.Signal = QtCore.Signal()
    pb_item: QtWidgets.QProgressBar = None
    s_item_advance: QtCore.Signal = QtCore.Signal(float)
    s_item_name: QtCore.Signal = QtCore.Signal(str)
    pb_list: QtWidgets.QProgressBar = None
    s_list_advance: QtCore.Signal = QtCore.Signal(float)
    s_pb_reset: QtCore.Signal = QtCore.Signal()
    s_populate_tree_lists: QtCore.Signal = QtCore.Signal(list)

    def __init__(self, tidal: Tidal | None = None):
        super().__init__()
        self.setupUi(self)
        # self.setGeometry(50, 50, 500, 300)
        self.setWindowTitle("TIDAL Downloader Next Gen!")
        # TODO: Fix icons (make them visible).
        # my_pixmap = QtGui.QPixmap("tidal_dl_ng/ui/icon.png")
        my_icon = QtGui.QIcon("tidal_dl_ng/ui/icon.png")
        self.setWindowIcon(my_icon)
        tray = QtWidgets.QSystemTrayIcon()
        tray.setIcon(my_icon)
        tray.setVisible(True)

        # Logging redirect.
        XStream.stdout().messageWritten.connect(self._log_output)
        # XStream.stderr().messageWritten.connect(self._log_output)

        self.settings = Settings()
        self.threadpool = QtCore.QThreadPool()

        # TODO: Show GUI, create a progress bar showing the TIDAL querying progress.
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

            while True:
                result = self.tidal.login(logger_gui.info)

                if result:
                    break

        if result:
            self.dl = Download(self.tidal.session, self.tidal.settings.data.skip_existing)

            self.thread_it(self.tidal_user_lists)

    def _init_progressbar(self):
        self.pb_list = QtWidgets.QProgressBar()
        self.pb_item = QtWidgets.QProgressBar()
        pbs = [self.pb_list, self.pb_item]

        for pb in pbs:
            pb.setRange(0, 100)
            # self.pb_progress.setVisible()
            self.statusbar.addPermanentWidget(pb)

    def progress_reset(self):
        self.pb_list.setValue(0)
        self.pb_item.setValue(0)

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

    # TODO: Refactor to own TIDAL file or so.
    def tidal_user_lists(self):
        # Start loading spinner
        self.spinner_start.emit(self.tr_lists_user)

        user_playlists: [Playlist | UserPlaylist] = self.tidal.session.user.playlist_and_favorite_playlists()
        user_mixes: [Mix] = self.tidal.session.mixes().categories[0].items
        user_all: [Playlist | UserPlaylist | Mix] = user_playlists + user_mixes

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
        self.spinner_stop.emit()

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
        self.thread_it(self.list_items_show, point=point)

    def on_download_list_media(self, point: QtCore.QPoint):
        item = self.tr_lists_user.itemAt(point)
        media = item.data(3, QtCore.Qt.ItemDataRole.UserRole)

        # TODO: Implement disable download button etc.
        self.download(media, self.dl)

    def search_populate_results(self, query: str, type_media: SearchTypes):
        self.tr_results.clear()

        results: [ResultSearch] = self.search(query, [type_media])

        self.populate_tree_results(results)

    def populate_tree_results(self, results: [ResultSearch]):
        self.tr_results.clear()
        count_digits: int = int(math.log10(len(results))) + 1

        for item in results:
            # Format seconds to mm:ss.
            m, s = divmod(item.duration_sec, 60)
            duration: str = f"{m:02d}:{s:02d}"
            # Since sorting happens only by string, we need to pad the index and add 1 (to avoid start at 0)
            index: str = str(item.position + 1).zfill(count_digits)
            child = QtWidgets.QTreeWidgetItem()

            child.setText(0, index)
            child.setText(1, item.artist)
            child.setText(2, item.title)
            child.setText(3, item.album)
            child.setText(4, duration)
            child.setData(5, QtCore.Qt.ItemDataRole.UserRole, item.obj)

            self.tr_results.addTopLevelItem(child)

    def search(self, query: str, types_media: SearchTypes) -> [ResultSearch]:
        result_search: dict[str, [SearchTypes]] = search_all_results(
            session=self.tidal.session, needle=query, types_media=types_media
        )
        result: [ResultSearch] = []

        for _media_type, l_media in result_search.items():
            if isinstance(l_media, list):
                result = result + self.search_result_to_model(l_media)

        return result

    def search_result_to_model(self, items: [*SearchTypes]) -> [ResultSearch]:
        result = []

        for idx, item in enumerate(items):
            if isinstance(item, Track):
                result_item: ResultSearch = ResultSearch(
                    position=idx,
                    artist=", ".join(artist.name for artist in item.artists),
                    title=item.name,
                    album=item.album.name,
                    duration_sec=item.duration,
                    obj=item,
                )

                result.append(result_item)
            elif isinstance(item, Video):
                result_item: ResultSearch = ResultSearch(
                    position=idx,
                    artist=", ".join(artist.name for artist in item.artists),
                    title=item.name,
                    album=item.album.name if item.album else "",
                    duration_sec=item.duration,
                    obj=item,
                )

                result.append(result_item)
            elif isinstance(item, Playlist):
                result_item: ResultSearch = ResultSearch(
                    position=idx,
                    artist=", ".join(artist.name for artist in item.promoted_artists) if item.promoted_artists else "",
                    title=item.name,
                    album="",
                    duration_sec=item.duration,
                    obj=item,
                )

                result.append(result_item)
            elif isinstance(item, Album):
                result_item: ResultSearch = ResultSearch(
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
        self.cb_quality_audio.currentIndexChanged.connect(self.quality_set_audio)
        self.cb_quality_video.currentIndexChanged.connect(self.quality_set_video)
        self.tr_lists_user.itemClicked.connect(self.on_list_items_show)
        self.spinner_start[QtWidgets.QWidget].connect(self.on_spinner_start)
        self.spinner_stop.connect(self.on_spinner_stop)
        self.s_item_advance.connect(self.progress_item)
        self.s_item_name.connect(self.progress_item_name)
        self.s_list_advance.connect(self.progress_list)
        self.s_pb_reset.connect(self.progress_reset)
        self.s_populate_tree_lists.connect(self.on_populate_tree_lists)

    def progress_list(self, value: float):
        self.pb_list.setValue(int(math.ceil(value)))

    def progress_item(self, value: float):
        self.pb_item.setValue(int(math.ceil(value)))

    def progress_item_name(self, value: str):
        self.pb_item.setFormat(f"%p% {value}")

    def progress_list_name(self, value: str):
        self.pb_list.setFormat(f"%p% {value}")

    def quality_set_audio(self, index):
        self.settings.data.quality_audio = Quality(self.cb_quality_audio.itemData(index).value)
        self.settings.save()

        if self.tidal:
            self.tidal.settings_apply()

    def quality_set_video(self, index):
        self.settings.data.quality_video = QualityVideo(self.cb_quality_video.itemData(index).value)
        self.settings.save()

        if self.tidal:
            self.tidal.settings_apply()

    def on_list_items_show(self, item: QtWidgets.QTreeWidgetItem):
        media_list: Album | Playlist = item.data(3, QtCore.Qt.ItemDataRole.UserRole)

        # Only if clicked item is not a top level item.
        if media_list:
            self.list_items_show(media_list)

    def list_items_show(self, media_list: Album | Playlist | None = None, point: QtCore.QPoint | None = None):
        if point:
            item = self.tr_lists_user.itemAt(point)
            media_list = item.data(3, QtCore.Qt.ItemDataRole.UserRole)

        # Get all results
        media_items: [Track | Video] = items_all_results(media_list)
        result: [ResultSearch] = self.search_result_to_model(media_items)

        self.populate_tree_results(result)

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
            for item in items:
                media: Track | Album | Playlist | Video = item.data(5, QtCore.Qt.ItemDataRole.UserRole)

                self.download(media, self.dl)

        self.b_download.setText("Download")
        self.b_download.setEnabled(True)

    def download(self, media: Track | Album | Playlist | Video | Mix, dl: Download) -> bool:
        # TODO: Refactor this. Move this logic to `Download` class and provide a generic interface.
        self.s_pb_reset.emit()
        self.statusbar.showMessage("Download started...")

        data_pb: ProgressBars = ProgressBars(
            item=self.s_item_advance, list_item=self.s_list_advance, item_name=self.s_item_name
        )
        progress: Progress = Progress()
        file_template = get_format_template(media, self.settings)

        if isinstance(media, Track | Video):
            result_download, download_path_file = dl.item(
                media=media,
                path_base=self.settings.data.download_base_path,
                file_template=file_template,
                progress_gui=data_pb,
                progress=progress,
                fn_logger=logger_gui,
            )

            if result_download:
                logger_gui.info(f"Download successful: {download_path_file}")
            else:
                logger_gui.info(f"Download skipped (file exists): {download_path_file}")
        elif isinstance(media, Album | Playlist | Mix):
            progress_name = (
                media.name
                if hasattr(media, "name") and media.name
                else hasattr(media, "title") and media.title if media.title else "List N/A"
            )

            self.progress_list_name(progress_name)

            dl.items(
                path_base=self.settings.data.download_base_path,
                file_template=file_template,
                media=media,
                video_download=self.settings.data.video_download,
                progress_gui=data_pb,
                progress=progress,
                download_delay=self.settings.data.download_delay,
                fn_logger=logger_gui,
            )

        self.statusbar.showMessage("Download finished.", 2000)
        progress.stop()

        # TODO: Refactor to useful return value.
        return True


# TODO: Comment with Google Docstrings.
def gui_activate(tidal: Tidal | None = None):
    qdarktheme.enable_hi_dpi()
    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme()

    window = MainWindow(tidal)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    gui_activate()
