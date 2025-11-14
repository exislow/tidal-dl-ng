import pathlib
from dataclasses import dataclass, field
from threading import Lock

from tidalapi.media import Quality

from tidal_dl_ng.constants import QualityVideo

try:
    from PySide6 import QtCore

    @dataclass
    class ProgressBars:
        item: QtCore.Signal
        item_name: QtCore.Signal
        list_item: QtCore.Signal
        list_name: QtCore.Signal

except ModuleNotFoundError:

    class ProgressBars:
        pass


@dataclass
class ResultItem:
    position: int
    artist: str
    title: str
    album: str
    duration_sec: int
    obj: object
    quality: str
    explicit: bool
    date_user_added: str
    date_release: str


@dataclass
class StatusbarMessage:
    message: str
    timeout: int = 0


@dataclass
class QueueDownloadItem:
    status: str
    name: str
    type_media: str
    quality_audio: Quality
    quality_video: QualityVideo
    obj: object
    _file_path: pathlib.Path | None = field(default=None, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    @property
    def file_path(self) -> pathlib.Path | None:
        """Get the downloaded file path (thread-safe)."""
        with self._lock:
            return self._file_path

    @file_path.setter
    def file_path(self, path: pathlib.Path | None) -> None:
        """Set the downloaded file path (thread-safe)."""
        with self._lock:
            self._file_path = path
