from PySide6 import QtCore, QtWidgets
from tidalapi import Album, Mix, Playlist, Track, UserPlaylist, Video
from tidalapi.artist import Artist


def get_table_data(
    item: QtWidgets.QTreeWidgetItem, column: int
) -> Track | Video | Album | Artist | Mix | Playlist | UserPlaylist:
    result: Track | Video | Album | Artist = item.data(column, QtCore.Qt.ItemDataRole.UserRole)

    return result


def get_results_media_item(item: QtWidgets.QTreeWidgetItem) -> Track | Video | Album | Artist | Playlist | Mix:
    result: Track | Video | Album | Artist | Playlist | Mix = get_table_data(item, 1)

    return result


def get_user_list_media_item(item: QtWidgets.QTreeWidgetItem) -> Mix | Playlist | UserPlaylist:
    result: Mix | Playlist | UserPlaylist = get_table_data(item, 1)

    return result


def get_queue_download_media(
    item: QtWidgets.QTreeWidgetItem,
) -> Mix | Playlist | UserPlaylist | Track | Video | Album | Artist:
    result: Mix | Playlist | UserPlaylist | Track | Video | Album | Artist = get_table_data(item, 1)

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
