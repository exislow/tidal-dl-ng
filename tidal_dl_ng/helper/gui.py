import re
from typing import cast

from PySide6 import QtCore, QtGui, QtWidgets
from tidalapi import Album, Mix, Playlist, Track, UserPlaylist, Video
from tidalapi.artist import Artist
from tidalapi.media import Quality

from tidal_dl_ng.constants import QualityVideo


def get_table_data(
    item: QtWidgets.QTreeWidgetItem, column: int
) -> Track | Video | Album | Artist | Mix | Playlist | UserPlaylist:
    result: Track | Video | Album | Artist = item.data(column, QtCore.Qt.ItemDataRole.UserRole)

    return result


def get_table_text(item: QtWidgets.QTreeWidgetItem, column: int) -> str:
    result: str = item.text(column)

    return result


def get_results_media_item(
    index: QtCore.QModelIndex, proxy: QtCore.QSortFilterProxyModel, model: QtGui.QStandardItemModel
) -> Track | Video | Album | Artist | Playlist | Mix:
    # Switch column to "obj" column and map proxy data to our model.
    item: QtGui.QStandardItem = model.itemFromIndex(proxy.mapToSource(index.siblingAtColumn(1)))
    result: Track | Video | Album | Artist = item.data(QtCore.Qt.ItemDataRole.UserRole)

    return result


def get_user_list_media_item(item: QtWidgets.QTreeWidgetItem) -> Mix | Playlist | UserPlaylist:
    result: Mix | Playlist | UserPlaylist = get_table_data(item, 1)

    return result


def get_queue_download_media(
    item: QtWidgets.QTreeWidgetItem,
) -> Mix | Playlist | UserPlaylist | Track | Video | Album | Artist:
    result: Mix | Playlist | UserPlaylist | Track | Video | Album | Artist = get_table_data(item, 1)

    return result


def get_queue_download_quality(
    item: QtWidgets.QTreeWidgetItem,
    column: int,
) -> str:
    result: str = get_table_text(item, column)

    return result


def get_queue_download_quality_audio(
    item: QtWidgets.QTreeWidgetItem,
) -> Quality:
    result: Quality = cast(Quality, get_queue_download_quality(item, 4))

    return result


def get_queue_download_quality_video(
    item: QtWidgets.QTreeWidgetItem,
) -> QualityVideo:
    result: QualityVideo = cast(QualityVideo, get_queue_download_quality(item, 5))

    return result


def set_table_data(
    item: QtWidgets.QTreeWidgetItem, data: Track | Video | Album | Artist | Mix | Playlist | UserPlaylist, column: int
):
    item.setData(column, QtCore.Qt.ItemDataRole.UserRole, data)


def set_results_media(item: QtWidgets.QTreeWidgetItem, media: Track | Video | Album | Artist):
    set_table_data(item, media, 1)


def set_user_list_media(
    item: QtWidgets.QTreeWidgetItem, media: Track | Video | Album | Artist | Mix | Playlist | UserPlaylist
):
    set_table_data(item, media, 1)


def set_queue_download_media(
    item: QtWidgets.QTreeWidgetItem, media: Mix | Playlist | UserPlaylist | Track | Video | Album | Artist
):
    set_table_data(item, media, 1)


class FilterHeader(QtWidgets.QHeaderView):
    filter_activated = QtCore.Signal()

    def __init__(self, parent):
        super().__init__(QtCore.Qt.Horizontal, parent)
        self._editors = []
        self._padding = 4
        self.setCascadingSectionResizes(True)
        self.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.setStretchLastSection(True)
        self.setDefaultAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.setSortIndicatorShown(False)
        self.setSectionsMovable(True)
        self.sectionResized.connect(self.adjust_positions)
        parent.horizontalScrollBar().valueChanged.connect(self.adjust_positions)

    def set_filter_boxes(self, count):
        while self._editors:
            editor = self._editors.pop()
            editor.deleteLater()

        for _ in range(count):
            editor = QtWidgets.QLineEdit(self.parent())
            editor.setPlaceholderText("Filter")
            editor.setClearButtonEnabled(True)
            editor.returnPressed.connect(self.filter_activated.emit)
            self._editors.append(editor)

        self.adjust_positions()

    def sizeHint(self):
        size = super().sizeHint()

        if self._editors:
            height = self._editors[0].sizeHint().height()

            size.setHeight(size.height() + height + self._padding)

        return size

    def updateGeometries(self):
        if self._editors:
            height = self._editors[0].sizeHint().height()

            self.setViewportMargins(0, 0, 0, height + self._padding)
        else:
            self.setViewportMargins(0, 0, 0, 0)

        super().updateGeometries()
        self.adjust_positions()

    def adjust_positions(self):
        for index, editor in enumerate(self._editors):
            height = editor.sizeHint().height()

            editor.move(self.sectionPosition(index) - self.offset() + 2, height + (self._padding // 2))
            editor.resize(self.sectionSize(index), height)

    def filter_text(self, index) -> str:
        if 0 <= index < len(self._editors):
            return self._editors[index].text()

        return ""

    def set_filter_text(self, index, text):
        if 0 <= index < len(self._editors):
            self._editors[index].setText(text)

    def clear_filters(self):
        for editor in self._editors:
            editor.clear()


class HumanProxyModel(QtCore.QSortFilterProxyModel):
    def _human_key(self, key):
        parts = re.split(r"(\d*\.\d+|\d+)", key)

        return tuple((e.swapcase() if i % 2 == 0 else float(e)) for i, e in enumerate(parts))

    def lessThan(self, source_left, source_right):
        data_left = source_left.data()
        data_right = source_right.data()

        if isinstance(data_left, str) and isinstance(data_right, str):
            return self._human_key(data_left) < self._human_key(data_right)

        return super().lessThan(source_left, source_right)

    @property
    def filters(self):
        if not hasattr(self, "_filters"):
            self._filters = []

        return self._filters

    @filters.setter
    def filters(self, filters):
        self._filters = filters

        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QtCore.QModelIndex) -> bool:
        model = self.sourceModel()
        source_index = model.index(source_row, 0, source_parent)
        result: [bool] = []

        # Show top level children
        for child_row in range(model.rowCount(source_index)):
            if self.filterAcceptsRow(child_row, source_index):
                return True

        # Filter for actual needle
        for i, text in self.filters:
            if 0 <= i < self.columnCount():
                ix = self.sourceModel().index(source_row, i, source_parent)
                data = ix.data()

                # Append results to list to enable an AND operator for filtering.
                result.append(bool(re.search(rf"{text}", data, re.MULTILINE | re.IGNORECASE)) if data else False)

        # If no filter set, just set the result to True.
        if not result:
            result.append(True)

        return all(result)
