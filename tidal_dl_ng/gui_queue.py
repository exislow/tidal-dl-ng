# tidal_dl_ng/gui_queue.py

import time
from typing import TYPE_CHECKING

from PySide6 import QtCore, QtGui, QtWidgets
from tidalapi import Album, Artist, Mix, Playlist, Quality, Track, Video

from tidal_dl_ng.config import HandlingApp, Settings
from tidal_dl_ng.constants import QualityVideo, QueueDownloadStatus
from tidal_dl_ng.download import Download
from tidal_dl_ng.helper.gui import (
    get_queue_download_media,
    get_queue_download_quality_audio,
    get_queue_download_quality_video,
    set_queue_download_media,
)
from tidal_dl_ng.helper.path import get_format_template
from tidal_dl_ng.helper.tidal import items_results_all, name_builder_artist, name_builder_title, quality_audio_highest
from tidal_dl_ng.logger import logger_gui
from tidal_dl_ng.model.gui_data import QueueDownloadItem, StatusbarMessage

if TYPE_CHECKING:
    from tidal_dl_ng.gui import MainWindow


class GuiQueueManager:
    """Manages the download queue GUI and logic."""

    def __init__(self, main_window: "MainWindow"):
        """Initialize the queue manager."""
        self.main_window: "MainWindow" = main_window
        self.settings: Settings = main_window.settings

    def init_ui(self):
        """Initialize UI elements related to the queue."""
        self._init_tree_queue(self.main_window.tr_queue_download)
        self.pb_queue_download_run()

    def connect_signals(self):
        """Connect signals for queue-related widgets."""
        self.main_window.pb_queue_download_clear_all.clicked.connect(self.on_queue_download_clear_all)
        self.main_window.pb_queue_download_clear_finished.clicked.connect(self.on_queue_download_clear_finished)
        self.main_window.pb_queue_download_remove.clicked.connect(self.on_queue_download_remove)
        self.main_window.pb_queue_download_toggle.clicked.connect(self.on_pb_queue_download_toggle)
        self.main_window.tr_queue_download.itemClicked.connect(self.on_queue_download_item_clicked)
        self.main_window.tr_queue_download.customContextMenuRequested.connect(self.menu_context_queue_download)
        self.main_window.s_queue_download_item_downloading.connect(self.on_queue_download_item_downloading)
        self.main_window.s_queue_download_item_finished.connect(self.on_queue_download_item_finished)
        self.main_window.s_queue_download_item_failed.connect(self.on_queue_download_item_failed)
        self.main_window.s_queue_download_item_skipped.connect(self.on_queue_download_item_skipped)

    def _init_tree_queue(self, tree: QtWidgets.QTableWidget) -> None:
        """Initialize the download queue table widget."""
        tree.setColumnHidden(1, True)
        tree.setColumnWidth(2, 200)
        header = tree.header()
        if hasattr(header, "setSectionResizeMode"):
            header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

    def menu_context_queue_download(self, point: QtCore.QPoint) -> None:
        """Show context menu for download queue."""
        item = self.main_window.tr_queue_download.itemAt(point)
        if not item:
            return
        menu = QtWidgets.QMenu()
        status = item.text(0)
        if status == QueueDownloadStatus.Waiting:
            menu.addAction("🗑️ Remove from Queue", lambda: self.on_queue_download_remove_item(item))
        if menu.isEmpty():
            return
        menu.exec(self.main_window.tr_queue_download.mapToGlobal(point))

    def on_queue_download_remove_item(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Remove a specific item from the download queue."""
        index = self.main_window.tr_queue_download.indexOfTopLevelItem(item)
        if index >= 0:
            self.main_window.tr_queue_download.takeTopLevelItem(index)
            logger_gui.info("Removed item from download queue")

    def on_queue_download_clear_all(self) -> None:
        """Clear all items from the download queue."""
        self.on_clear_queue_download(
            f"({QueueDownloadStatus.Waiting}|{QueueDownloadStatus.Finished}|{QueueDownloadStatus.Failed}|{QueueDownloadStatus.Skipped})"
        )

    def on_queue_download_clear_finished(self) -> None:
        """Clear finished items from the download queue."""
        self.on_clear_queue_download(f"({QueueDownloadStatus.Finished}|{QueueDownloadStatus.Skipped})")

    def on_clear_queue_download(self, regex: str) -> None:
        """Clear items from the download queue matching the given regex."""
        items = self.main_window.tr_queue_download.findItems(
            regex, QtCore.Qt.MatchFlag.MatchRegularExpression, column=0
        )
        for item in items:
            self.main_window.tr_queue_download.takeTopLevelItem(
                self.main_window.tr_queue_download.indexOfTopLevelItem(item)
            )

    def on_queue_download_remove(self) -> None:
        """Remove selected items from the download queue."""
        items = self.main_window.tr_queue_download.selectedItems()
        if not items:
            logger_gui.error("Please select an item from the queue first.")
        else:
            for item in items:
                status: str = item.text(0)
                if status != QueueDownloadStatus.Downloading:
                    self.main_window.tr_queue_download.takeTopLevelItem(
                        self.main_window.tr_queue_download.indexOfTopLevelItem(item)
                    )
                else:
                    logger_gui.info("Cannot remove a currently downloading item from queue.")

    def on_pb_queue_download_toggle(self) -> None:
        """Toggle download status (pause / resume) accordingly."""
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
        self.main_window.pb_queue_download_toggle.setIcon(icon)
        self.main_window.pb_queue_download_toggle.setStyleSheet("background-color: #e0a800; color: #212529")

    def pb_queue_download_pause(self) -> None:
        """Pause the download queue and update the button state."""
        handling_app: HandlingApp = HandlingApp()
        handling_app.event_run.clear()
        icon = QtGui.QIcon(QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.MediaPlaybackStart))
        self.main_window.pb_queue_download_toggle.setIcon(icon)
        self.main_window.pb_queue_download_toggle.setStyleSheet("background-color: #218838; color: #fff")

    def queue_download_media(self, queue_dl_item: QueueDownloadItem) -> None:
        """Add a media item to the download queue."""
        child = QtWidgets.QTreeWidgetItem()
        child.setText(0, queue_dl_item.status)
        set_queue_download_media(child, queue_dl_item.obj)
        child.setText(2, queue_dl_item.name)
        child.setText(3, queue_dl_item.type_media)
        child.setText(4, str(queue_dl_item.quality_audio))
        child.setText(5, str(queue_dl_item.quality_video))
        self.main_window.tr_queue_download.addTopLevelItem(child)

    def watcher_queue_download(self) -> None:
        """Monitor the download queue and process items as they become available."""
        handling_app: HandlingApp = HandlingApp()
        while not handling_app.event_abort.is_set():
            items = self.main_window.tr_queue_download.findItems(
                QueueDownloadStatus.Waiting, QtCore.Qt.MatchFlag.MatchExactly, column=0
            )
            if items:
                item = items[0]
                media = get_queue_download_media(item)
                quality_audio = get_queue_download_quality_audio(item)
                quality_video = get_queue_download_quality_video(item)
                try:
                    self.main_window.s_queue_download_item_downloading.emit(item)
                    result = self.on_queue_download(media, quality_audio=quality_audio, quality_video=quality_video)
                    if result == QueueDownloadStatus.Finished:
                        self.main_window.s_queue_download_item_finished.emit(item)
                    elif result == QueueDownloadStatus.Skipped:
                        self.main_window.s_queue_download_item_skipped.emit(item)
                except Exception as e:
                    logger_gui.error(e)
                    self.main_window.s_queue_download_item_failed.emit(item)
            else:
                time.sleep(2)

    def on_queue_download_item_downloading(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Update the status of a queue download item to 'Downloading'."""
        self.queue_download_item_status(item, QueueDownloadStatus.Downloading)

    def on_queue_download_item_finished(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Update the status of a queue download item to 'Finished'."""
        self.queue_download_item_status(item, QueueDownloadStatus.Finished)

    def on_queue_download_item_failed(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Update the status of a queue download item to 'Failed'."""
        self.queue_download_item_status(item, QueueDownloadStatus.Failed)

    def on_queue_download_item_skipped(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Update the status of a queue download item to 'Skipped'."""
        self.queue_download_item_status(item, QueueDownloadStatus.Skipped)

    def queue_download_item_status(self, item: QtWidgets.QTreeWidgetItem, status: str) -> None:
        """Set the status text of a queue download item."""
        item.setText(0, status)

    def on_queue_download(
        self,
        media: Track | Album | Playlist | Video | Mix | Artist,
        quality_audio: Quality | None = None,
        quality_video: QualityVideo | None = None,
    ) -> QueueDownloadStatus:
        """Download the specified media item(s) and return the result status."""
        items_media = items_results_all(self.main_window.tidal.session, media) if isinstance(media, Artist) else [media]
        download_delay = bool(isinstance(media, Track | Video) and self.settings.data.download_delay)
        result = QueueDownloadStatus.Failed
        for item_media in items_media:
            result = self.download(
                item_media,
                self.main_window.dl,
                delay_track=download_delay,
                quality_audio=quality_audio,
                quality_video=quality_video,
            )
        return result

    def download(
        self,
        media: Track | Album | Playlist | Video | Mix,
        dl: Download,
        delay_track: bool = False,
        quality_audio: Quality | None = None,
        quality_video: QualityVideo | None = None,
    ) -> QueueDownloadStatus:
        """Download a media item and return the result status."""
        self.main_window.s_pb_reset.emit()
        self.main_window.s_statusbar_message.emit(StatusbarMessage(message="Download started..."))
        file_template = get_format_template(media, self.settings)
        result_dl, path_file = False, None
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
            result_dl, path_file = True, "dummy"
        self.main_window.s_statusbar_message.emit(StatusbarMessage(message="Download finished.", timeout=2000))
        if result_dl and path_file:
            return QueueDownloadStatus.Finished
        if not result_dl and path_file:
            return QueueDownloadStatus.Skipped
        return QueueDownloadStatus.Failed

    def on_queue_download_item_clicked(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Handle the event when a queue download item is clicked."""
        media = get_queue_download_media(item)
        self.main_window.info_tab_widget.update_on_selection(media)
        self.main_window.thread_it(self.main_window.cover_manager.load_cover, media)

    def media_to_queue_download_model(
        self, media: Artist | Track | Video | Album | Playlist | Mix
    ) -> QueueDownloadItem | None:
        """Convert a media object to a QueueDownloadItem for the download queue."""
        if hasattr(media, "available") and media.available is False:
            return None
        explicit = " 🅴" if isinstance(media, Track | Video | Album) and media.explicit else ""
        name = ""
        if isinstance(media, Track | Video):
            name = f"{name_builder_artist(media)} - {name_builder_title(media)}{explicit}"
        elif isinstance(media, Playlist | Artist):
            name = media.name
        elif isinstance(media, Album):
            name = f"{name_builder_artist(media)} - {media.name}{explicit}"
        elif isinstance(media, Mix):
            name = media.title

        quality_audio = self.settings.data.quality_audio
        if isinstance(media, Track | Album):
            quality_highest = quality_audio_highest(media)
            if (
                self.settings.data.quality_audio == quality_highest
                or self.settings.data.quality_audio == Quality.hi_res_lossless
            ):
                quality_audio = quality_highest

        if name:
            return QueueDownloadItem(
                name=name,
                quality_audio=quality_audio,
                quality_video=self.settings.data.quality_video,
                type_media=type(media).__name__,
                status=QueueDownloadStatus.Waiting,
                obj=media,
            )
        return None
