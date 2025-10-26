from dataclasses import InitVar, dataclass, field
from threading import Lock

from tidalapi.media import Quality

from tidal_dl_ng.constants import QualityVideo, QueueDownloadStatus

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
    name: str
    type_media: str
    quality_audio: Quality
    quality_video: QualityVideo
    obj: object
    status_init: InitVar[str] = QueueDownloadStatus.Waiting
    _status: str = field(init=False)
    _file_path: str | None = field(default=None, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def __post_init__(self, status_init: str):
        """Assigns the initial state after creation."""
        self._status = status_init

    def set_file_path(self, path: str) -> None:
        """Thread-safe setter for file_path."""
        with self._lock:
            self._file_path = path

    def get_file_path(self) -> str | None:
        """Thread-safe getter for file_path."""
        with self._lock:
            return self._file_path

    def set_status(self, status: str) -> None:
        """Thread-safe setter for status."""
        with self._lock:
            self._status = status

    def get_status(self) -> str:
        """Thread-safe getter for status."""
        with self._lock:
            return self._status
