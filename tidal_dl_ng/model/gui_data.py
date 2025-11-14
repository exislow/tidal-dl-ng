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
    """Download queue item model.

    Attributes:
        status (str): Current download status.
        name (str): Display name of the media item.
        type_media (str): Type of media (Track, Album, etc).
        quality_audio (Quality): Audio quality setting.
        quality_video (QualityVideo): Video quality setting.
        obj (object): The actual media object.
        file_path (pathlib.Path | None): Path to downloaded file/directory (thread-safe property).
    """

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
        """Get the downloaded file path (thread-safe).

        Returns:
            pathlib.Path | None: Path to the downloaded file or directory, or None if not yet set.
        """
        with self._lock:
            return self._file_path

    @file_path.setter
    def file_path(self, path: pathlib.Path | None) -> None:
        """Set the downloaded file path (thread-safe).

        Args:
            path (pathlib.Path | None): Path to the downloaded file or directory.
        """
        with self._lock:
            self._file_path = path
