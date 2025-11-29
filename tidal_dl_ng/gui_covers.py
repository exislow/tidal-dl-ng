"""Cover management for GUI - Handles cover loading, caching and display."""

from contextlib import suppress

from PySide6 import QtGui

from tidal_dl_ng.cache import CoverPixmapCache
from tidal_dl_ng.download import Download
from tidal_dl_ng.helper.path import resource_path
from tidal_dl_ng.logger import logger_gui
from tidal_dl_ng.worker import Worker


class CoverManager:
    """Manages cover art loading, caching and display operations."""

    def __init__(self, parent_window, threadpool, info_tab_widget):
        """Initialize the cover manager.

        Args:
            parent_window: Main window instance
            threadpool: QThreadPool for async operations
            info_tab_widget: InfoTabWidget instance for display
        """
        self.parent = parent_window
        self.threadpool = threadpool
        self.info_tab = info_tab_widget
        self.cache = CoverPixmapCache()
        self.cover_url_current = ""

    def load_cover(self, media, use_cache_check: bool = True):
        """Load and display cover for media item.

        Args:
            media: Media object (Track, Album, etc.)
            use_cache_check: If True, check cache before loading
        """
        if use_cache_check:
            # Try cache first for instant display
            cover_url = self._get_cover_url(media)
            if cover_url:
                if cover_url == self.cover_url_current:
                    return  # Already displayed

                cached_pixmap = self.cache.get(cover_url)
                if cached_pixmap:
                    self._display_cover(cached_pixmap, cover_url)
                    return

        # Load asynchronously
        worker = Worker(self._load_cover_async, media)
        self.threadpool.start(worker)

    def _load_cover_async(self, media):
        """Load cover in background thread."""
        # Emit spinner on tab widget instead of InfoTabWidget (which is QObject, not QWidget)
        tab_widget = self.info_tab.tab_widget if hasattr(self.info_tab, "tab_widget") else None
        if tab_widget:
            self.parent.s_spinner_start.emit(tab_widget)

        try:
            cover_url = self._get_cover_url(media)

            if cover_url and self.cover_url_current != cover_url:
                # Check cache again (thread-safe)
                cached_pixmap = self.cache.get(cover_url)
                if cached_pixmap:
                    self._display_cover(cached_pixmap, cover_url)
                else:
                    # Download and cache
                    data_cover = Download.cover_data(cover_url)
                    pixmap = QtGui.QPixmap()
                    pixmap.loadFromData(data_cover)
                    self.cache.set(cover_url, pixmap)
                    self._display_cover(pixmap, cover_url)
            elif not cover_url:
                self._display_default_cover()
        except Exception as e:
            logger_gui.warning(f"Failed to load cover: {e}")
            self._display_default_cover()
        finally:
            self.parent.s_spinner_stop.emit()

    def _get_cover_url(self, media) -> str | None:
        """Extract cover URL from media object."""
        with suppress(Exception):
            if hasattr(media, "album") and media.album:
                return media.album.image()
            if hasattr(media, "image") and callable(getattr(media, "image", None)):
                return media.image()
        return None

    def _display_cover(self, pixmap: QtGui.QPixmap, url: str):
        """Display a pixmap on the info tab."""
        self.info_tab.set_cover_pixmap(pixmap)
        self.info_tab.cover_url_current = url
        self.cover_url_current = url

    def _display_default_cover(self):
        """Display default cover image."""
        path_image = resource_path("tidal_dl_ng/ui/default_album_image.png")
        pixmap = QtGui.QPixmap(path_image)
        self.info_tab.set_cover_pixmap(pixmap)
        self.info_tab.cover_url_current = ""
        self.cover_url_current = ""

    def preload_covers_for_playlist(self, items: list) -> None:
        """Preload cover pixmaps for a list of tracks in background.

        Args:
            items: List of Track/Video objects to preload covers for.
        """

        def worker() -> None:
            # Extract unique cover URLs
            cover_urls = set()
            for item in items[:50]:  # Limit to first 50
                with suppress(Exception):
                    url = self._get_cover_url(item)
                    if url:
                        cover_urls.add(url)

            # Preload each unique cover
            for cover_url in cover_urls:
                if self.cache.get(cover_url):
                    continue  # Already cached

                with suppress(Exception):
                    data_cover = Download.cover_data(cover_url)
                    pixmap = QtGui.QPixmap()
                    pixmap.loadFromData(data_cover)
                    self.cache.set(cover_url, pixmap)
                    logger_gui.debug(f"Preloaded cover: {cover_url[:50]}...")

        worker_obj = Worker(worker)
        self.threadpool.start(worker_obj)

    def _queue_cover_fetch(self, media):
        """Queue a cover fetch operation for a media item."""
        with suppress(Exception):
            # previously try/except/pass
            self.threadpool.start(Worker(self.load_cover, media))

    def _fetch_cover_pixmap(self, media, use_cache_check: bool):
        """Fetch cover pixmap for media, with optional cache check."""
        with suppress(Exception):
            # previously try/except/continue inside loop
            pixmap = self.cache.get(self._get_cover_url(media))
            if pixmap:
                return pixmap

            # If not in cache, download cover
            cover_url = self._get_cover_url(media)
            if cover_url:
                data_cover = Download.cover_data(cover_url)
                pixmap = QtGui.QPixmap()
                pixmap.loadFromData(data_cover)
                self.cache.set(cover_url, pixmap)
                return pixmap

        return None
