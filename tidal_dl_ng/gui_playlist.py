# tidal_dl_ng/gui_playlist.py

from typing import TYPE_CHECKING

from PySide6 import QtCore, QtWidgets
from tidalapi import Album, Mix, Playlist, UserPlaylist
from tidalapi.playlist import Folder

from tidal_dl_ng.constants import FAVORITES, TidalLists
from tidal_dl_ng.helper.gui import get_user_list_media_item, set_user_list_media
from tidal_dl_ng.helper.tidal import (
    favorite_function_factory,
    items_results_all,
    user_media_lists,
)
from tidal_dl_ng.logger import logger_gui
from tidal_dl_ng.model.gui_data import StatusbarMessage

if TYPE_CHECKING:
    from tidal_dl_ng.gui import MainWindow


class GuiPlaylistManager:
    """Manages the playlist, mixes, and favorites GUI and logic."""

    def __init__(self, main_window: "MainWindow"):
        """Initialize the playlist manager."""
        self.main_window: "MainWindow" = main_window
        self.settings = main_window.settings

    def init_ui(self):
        """Initialize UI elements related to playlists."""
        self._init_tree_lists(self.main_window.tr_lists_user)

    def connect_signals(self):
        """Connect signals for playlist-related widgets."""
        self.main_window.pb_reload_user_lists.clicked.connect(lambda: self.main_window.thread_it(self.tidal_user_lists))
        self.main_window.tr_lists_user.itemClicked.connect(self.on_list_items_show)
        self.main_window.tr_lists_user.itemExpanded.connect(self.on_tr_lists_user_expanded)
        self.main_window.tr_lists_user.customContextMenuRequested.connect(self.menu_context_tree_lists)
        self.main_window.s_populate_tree_lists.connect(self.on_populate_tree_lists)
        self.main_window.s_populate_folder_children.connect(self.on_populate_folder_children)

    def _init_tree_lists(self, tree: QtWidgets.QTreeWidget) -> None:
        """Initialize the user lists tree widget."""
        tree.setColumnWidth(0, 200)
        tree.setColumnHidden(1, True)
        tree.setColumnWidth(2, 300)
        tree.expandAll()
        tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

    def tidal_user_lists(self) -> None:
        """Fetch and emit user playlists, mixes, and favorites from Tidal."""
        self.main_window.s_spinner_start.emit(self.main_window.tr_lists_user)
        self.main_window.s_pb_reload_status.emit(False)
        user_all = user_media_lists(self.main_window.tidal.session)
        self.main_window.s_populate_tree_lists.emit(user_all)

    def on_populate_tree_lists(self, user_lists: dict[str, list]) -> None:
        """Populate the user lists tree with playlists, mixes, and favorites."""
        twi_playlists = self.main_window.tr_lists_user.findItems(TidalLists.Playlists, QtCore.Qt.MatchExactly, 0)[0]
        twi_mixes = self.main_window.tr_lists_user.findItems(TidalLists.Mixes, QtCore.Qt.MatchExactly, 0)[0]
        twi_favorites = self.main_window.tr_lists_user.findItems(TidalLists.Favorites, QtCore.Qt.MatchExactly, 0)[0]

        for twi in [twi_playlists, twi_mixes, twi_favorites]:
            for i in reversed(range(twi.childCount())):
                twi.removeChild(twi.child(i))

        for item in user_lists.get("playlists", []):
            if isinstance(item, Folder):
                twi_child = QtWidgets.QTreeWidgetItem(twi_playlists)
                twi_child.setText(0, f"📁 {item.name}")
                set_user_list_media(twi_child, item)
                info = f"({item.total_number_of_items} items)" if item.total_number_of_items else ""
                twi_child.setText(2, info)
                dummy_child = QtWidgets.QTreeWidgetItem(twi_child)
                dummy_child.setDisabled(True)
            elif isinstance(item, UserPlaylist | Playlist):
                twi_child = QtWidgets.QTreeWidgetItem(twi_playlists)
                name = item.name or ""
                description = f" {item.description}" if item.description else ""
                info = f"({item.num_tracks + item.num_videos} Tracks){description}"
                twi_child.setText(0, name)
                set_user_list_media(twi_child, item)
                twi_child.setText(2, info)

        for item in user_lists.get("mixes", []):
            if isinstance(item, Mix):
                twi_child = QtWidgets.QTreeWidgetItem(twi_mixes)
                twi_child.setText(0, item.title)
                set_user_list_media(twi_child, item)
                twi_child.setText(2, item.sub_title)

        for key, favorite in FAVORITES.items():
            twi_child = QtWidgets.QTreeWidgetItem(twi_favorites)
            twi_child.setText(0, favorite["name"])
            set_user_list_media(twi_child, key)

        self.main_window.s_spinner_stop.emit()
        self.main_window.s_pb_reload_status.emit(True)

    def menu_context_tree_lists(self, point: QtCore.QPoint) -> None:
        """Show context menu for user lists tree."""
        index = self.main_window.tr_lists_user.indexAt(point)
        if not index.isValid() or not index.parent().data():
            return
        item = self.main_window.tr_lists_user.itemAt(point)
        media = get_user_list_media_item(item)
        menu = QtWidgets.QMenu()
        if isinstance(media, Folder):
            menu.addAction(
                "Download All Playlists in Folder",
                lambda: self.main_window.thread_it(self.on_download_folder_playlists, point),
            )
            menu.addAction(
                "Download All Albums from Folder",
                lambda: self.main_window.thread_it(self.on_download_folder_albums, point),
            )
        elif isinstance(media, str):
            menu.addAction("Download All Items", lambda: self.main_window.thread_it(self.on_download_favorites, point))
            menu.addAction(
                "Download All Albums from Items",
                lambda: self.main_window.thread_it(self.on_download_albums_from_favorites, point),
            )
        else:
            menu.addAction("Download Playlist", lambda: self.main_window.thread_it(self.on_download_list_media, point))
            menu.addAction(
                "Download All Albums in Playlist",
                lambda: self.main_window.thread_it(self.on_download_all_albums_from_playlist, point),
            )
            menu.addAction(
                "Copy Share URL", lambda: self.main_window.on_copy_url_share(self.main_window.tr_lists_user, point)
            )
        menu.exec_(self.main_window.tr_lists_user.mapToGlobal(point))

    def on_download_list_media(self, point: QtCore.QPoint | None = None) -> None:
        """Download all media items in a selected list."""
        items = (
            [self.main_window.tr_lists_user.itemAt(point)] if point else self.main_window.tr_lists_user.selectedItems()
        )
        if not items:
            logger_gui.error("Please select a mix or playlist first.")
            return
        for item in items:
            media = get_user_list_media_item(item)
            queue_dl_item = self.main_window.queue_manager.media_to_queue_download_model(media)
            if queue_dl_item:
                self.main_window.queue_manager.queue_download_media(queue_dl_item)

    def on_download_folder_playlists(self, point: QtCore.QPoint) -> None:
        """Download all playlists in a folder."""
        item = self.main_window.tr_lists_user.itemAt(point)
        media = get_user_list_media_item(item)
        if not isinstance(media, Folder):
            logger_gui.error("Please select a folder.")
            return
        logger_gui.info(f"Fetching playlists from folder: {media.name}")
        playlists = self._get_folder_playlists(media)
        if not playlists:
            logger_gui.info(f"No playlists found in folder: {media.name}")
            return
        logger_gui.info(f"Queueing {len(playlists)} playlists from folder: {media.name}")
        for playlist in playlists:
            queue_dl_item = self.main_window.queue_manager.media_to_queue_download_model(playlist)
            if queue_dl_item:
                self.main_window.queue_manager.queue_download_media(queue_dl_item)
        logger_gui.info(f"✅ Successfully queued {len(playlists)} playlists from folder: {media.name}")

    def on_download_folder_albums(self, point: QtCore.QPoint) -> None:
        """Download all unique albums from all playlists in a folder."""
        item = self.main_window.tr_lists_user.itemAt(point)
        media = get_user_list_media_item(item)
        if not isinstance(media, Folder):
            logger_gui.error("Please select a folder.")
            return
        playlists = self._get_folder_playlists(media)
        if not playlists:
            return
        all_tracks = []
        for playlist in playlists:
            try:
                tracks = self._get_playlist_tracks(playlist)
                all_tracks.extend(tracks)
            except Exception as e:
                logger_gui.error(f"Error getting tracks from playlist '{playlist.name}': {e}")
        if not all_tracks:
            return
        album_ids = self.main_window._extract_album_ids_from_tracks(all_tracks)
        if not album_ids:
            return
        albums_dict = self.main_window._load_albums_with_rate_limiting(album_ids)
        if not albums_dict:
            return
        self.main_window._queue_loaded_albums(albums_dict)

    def on_download_favorites(self, point: QtCore.QPoint) -> None:
        """Download all items from a Favorites category."""
        item = self.main_window.tr_lists_user.itemAt(point)
        media_key = get_user_list_media_item(item)
        if not isinstance(media_key, str):
            logger_gui.error("Please select a favorites category.")
            return
        favorite_name = FAVORITES.get(media_key, {}).get("name", media_key)
        logger_gui.info(f"Fetching all items from favorites: {favorite_name}")
        favorite_function = favorite_function_factory(self.main_window.tidal, media_key)
        media_items = favorite_function()
        if not media_items:
            logger_gui.info(f"No items found in favorites: {favorite_name}")
            return
        queued_count = 0
        for media_item in media_items:
            queue_dl_item = self.main_window.queue_manager.media_to_queue_download_model(media_item)
            if queue_dl_item:
                self.main_window.queue_manager.queue_download_media(queue_dl_item)
                queued_count += 1
        logger_gui.info(f"✅ Successfully queued {queued_count} items from favorites: {favorite_name}")

    def _download_albums_from_fav_artists(self, media_items: list) -> None:
        """Download all albums from favorite artists."""
        all_albums = {}
        for artist in media_items:
            try:
                artist_albums = items_results_all(self.main_window.tidal.session, artist)
                for album in artist_albums:
                    if isinstance(album, Album) and album.id:
                        all_albums[album.id] = album
            except Exception as e:
                logger_gui.error(f"Error getting albums from artist '{artist.name}': {e}")
        if all_albums:
            self.main_window._queue_loaded_albums(all_albums)

    def _download_albums_from_fav_tracks(self, media_items: list) -> None:
        """Download all albums from favorite tracks."""
        album_ids = self.main_window._extract_album_ids_from_tracks(media_items)
        if album_ids:
            albums_dict = self.main_window._load_albums_with_rate_limiting(album_ids)
            if albums_dict:
                self.main_window._queue_loaded_albums(albums_dict)

    def on_download_albums_from_favorites(self, point: QtCore.QPoint) -> None:
        """Download all unique albums from items in a Favorites category."""
        item = self.main_window.tr_lists_user.itemAt(point)
        media_key = get_user_list_media_item(item)
        if not isinstance(media_key, str):
            return
        favorite_function = favorite_function_factory(self.main_window.tidal, media_key)
        media_items = favorite_function()
        if not media_items:
            return

        if media_key == "fav_albums":
            albums_dict = {album.id: album for album in media_items if isinstance(album, Album) and album.id}
            self.main_window._queue_loaded_albums(albums_dict)
        elif media_key == "fav_artists":
            self._download_albums_from_fav_artists(media_items)
        else:
            self._download_albums_from_fav_tracks(media_items)

    def on_download_all_albums_from_playlist(self, point: QtCore.QPoint) -> None:
        """Download all unique albums from tracks in a playlist."""
        item = self.main_window.tr_lists_user.itemAt(point)
        media_list = get_user_list_media_item(item)
        if not isinstance(media_list, Playlist | UserPlaylist | Mix):
            logger_gui.error("Please select a playlist or mix.")
            return
        media_items = items_results_all(self.main_window.tidal.session, media_list)
        album_ids = self.main_window._extract_album_ids_from_tracks(media_items)
        if not album_ids:
            logger_gui.warning("No albums found in this playlist.")
            return
        albums_dict = self.main_window._load_albums_with_rate_limiting(album_ids)
        if not albums_dict:
            logger_gui.error("Failed to load any albums from playlist.")
            return
        self.main_window._queue_loaded_albums(albums_dict)
        message = f"Added {len(albums_dict)} albums to download queue"
        self.main_window.s_statusbar_message.emit(StatusbarMessage(message=message, timeout=3000))

    def on_tr_lists_user_expanded(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Handle expansion of folders in the user lists tree."""
        if item.childCount() > 0 and item.child(0).isDisabled():
            self.main_window.thread_it(self.tr_lists_user_load_folder_children, item)

    def tr_lists_user_load_folder_children(self, parent_item: QtWidgets.QTreeWidgetItem) -> None:
        """Load and display children of a folder in the user lists tree."""
        folder = get_user_list_media_item(parent_item)
        if not isinstance(folder, Folder):
            return
        self.main_window.s_spinner_start.emit(self.main_window.tr_lists_user)
        try:
            folders, playlists = self._fetch_folder_contents(folder)
            self.main_window.s_populate_folder_children.emit(parent_item, folders, playlists)
        finally:
            self.main_window.s_spinner_stop.emit()

    def on_populate_folder_children(
        self, parent_item: QtWidgets.QTreeWidgetItem, folders: list[Folder], playlists: list[Playlist]
    ) -> None:
        """Populate folder children in the main thread."""
        parent_item.takeChild(0)
        for sub_folder in folders:
            twi_child = QtWidgets.QTreeWidgetItem(parent_item)
            twi_child.setText(0, f"📁 {sub_folder.name}")
            set_user_list_media(twi_child, sub_folder)
            info = f"({sub_folder.total_number_of_items} items)" if sub_folder.total_number_of_items else ""
            twi_child.setText(2, info)
            dummy = QtWidgets.QTreeWidgetItem(twi_child)
            dummy.setDisabled(True)
        for playlist in playlists:
            twi_child = QtWidgets.QTreeWidgetItem(parent_item)
            twi_child.setText(0, playlist.name or "")
            set_user_list_media(twi_child, playlist)
            info = f"({playlist.num_tracks + playlist.num_videos} Tracks)"
            if playlist.description:
                info += f" {playlist.description}"
            twi_child.setText(2, info)

    def _fetch_folder_contents(self, folder: Folder) -> tuple[list[Folder], list[Playlist]]:
        """Fetch contents of a folder."""
        folder_id = folder.id or "root"
        folders, playlists = [], []
        offset, limit = 0, 50
        while True:
            batch = self.main_window.tidal.session.user.favorites.playlist_folders(
                limit=limit, offset=offset, parent_folder_id=folder_id
            )
            if not batch:
                break
            folders.extend(batch)
            if len(batch) < limit:
                break
            offset += limit
        offset = 0
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
        """Fetch all playlists from a folder."""
        _, playlists = self._fetch_folder_contents(folder)
        return playlists

    def _get_playlist_tracks(self, playlist: Playlist | UserPlaylist | Mix) -> list:
        """Fetch all tracks from a playlist."""
        return [
            item
            for item in items_results_all(self.main_window.tidal.session, playlist)
            if isinstance(item, self.main_window.tidal.session.track)
        ]

    def on_list_items_show(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Show the items in the selected playlist or mix."""
        self.main_window.thread_it(self.list_items_show, item)

    def list_items_show(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Fetch and display the items in a playlist, mix, or folder."""
        media_list = get_user_list_media_item(item)
        if not media_list:
            return
        self.main_window.s_spinner_start.emit(self.main_window.tr_results)
        try:
            if isinstance(media_list, Folder):
                self._show_folder_contents(media_list)
            elif isinstance(media_list, str) and media_list.startswith("fav_"):
                function_list = favorite_function_factory(self.main_window.tidal, media_list)
                self.main_window.list_items_show_result(favorite_function=function_list)
            else:
                self.main_window.list_items_show_result(media_list)
                self.main_window.thread_it(self.main_window.cover_manager.load_cover, media_list)
        finally:
            self.main_window.s_spinner_stop.emit()

    def _show_folder_contents(self, folder: Folder) -> None:
        """Display folder contents in results pane."""
        folders, playlists = self._fetch_folder_contents(folder)
        items = folders + playlists
        result = self.main_window.search_manager.search_result_to_model(items)
        self.main_window.search_manager.populate_tree_results(result)
