"""Cache management for GUI - LRU caches for performance optimization."""

from PySide6 import QtCore, QtGui


class TrackExtrasCache:
    """Thread-safe LRU cache for track extra metadata."""

    def __init__(self, max_size: int = 256):
        self._lock = QtCore.QReadWriteLock()
        self._data: dict[str, dict] = {}
        self._order: list[str] = []
        self._max_size = max_size

    def get(self, track_id: str) -> dict | None:
        """Get cached extras for a track ID."""
        with QtCore.QReadLocker(self._lock):
            return self._data.get(track_id)

    def set(self, track_id: str, extras: dict) -> None:
        """Cache extras for a track ID with LRU eviction."""
        with QtCore.QWriteLocker(self._lock):
            if track_id in self._data:
                self._order.remove(track_id)
            self._data[track_id] = extras
            self._order.append(track_id)
            if len(self._order) > self._max_size:
                oldest = self._order.pop(0)
                self._data.pop(oldest, None)


class CoverPixmapCache:
    """Thread-safe LRU cache for cover pixmaps to avoid re-downloading."""

    def __init__(self, max_size: int = 100):
        self._lock = QtCore.QReadWriteLock()
        self._pixmaps: dict[str, QtGui.QPixmap] = {}
        self._order: list[str] = []
        self._max_size = max_size

    def get(self, cover_url: str) -> QtGui.QPixmap | None:
        """Get cached pixmap for a cover URL."""
        with QtCore.QReadLocker(self._lock):
            return self._pixmaps.get(cover_url)

    def set(self, cover_url: str, pixmap: QtGui.QPixmap) -> None:
        """Cache a pixmap with LRU eviction."""
        with QtCore.QWriteLocker(self._lock):
            if cover_url in self._pixmaps:
                self._order.remove(cover_url)
            self._pixmaps[cover_url] = pixmap
            self._order.append(cover_url)
            if len(self._order) > self._max_size:
                oldest = self._order.pop(0)
                self._pixmaps.pop(oldest, None)
