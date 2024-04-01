from enum import Enum

CTX_TIDAL: str = "tidal"
REQUESTS_TIMEOUT_SEC: int = 45
EXTENSION_LYRICS: str = ".lrc"
UNIQUIFY_THRESHOLD: int = 99
FILENAME_SANITIZE_PLACEHOLDER: str = "_"


class QualityVideo(Enum):
    P360: int = 360
    P480: int = 480
    P720: int = 720
    P1080: int = 1080


class MediaType(Enum):
    TRACK: str = "track"
    VIDEO: str = "video"
    PLAYLIST: str = "playlist"
    ALBUM: str = "album"
    MIX: str = "mix"


class SkipExisting(Enum):
    Disabled: bool = False
    Filename: str = "exact"
    ExtensionIgnore: str = "extension_ignore"
    Append: str = "append"


class StreamManifestMimeType(Enum):
    MPD: str = "application/dash+xml"
    BTS: str = "application/vnd.tidal.bts"
    VIDEO: str = "video/mp2t"


class CoverDimensions(Enum):
    Px80: int = 80
    Px160: int = 160
    Px320: int = 320
    Px640: int = 640
    Px1280: int = 1280


class TidalLists(Enum):
    Playlists: str = "Playlists"
    Favorites: str = "Favorites"
    Mixes: str = "Mixes"


class AudioExtensions(Enum):
    FLAC: str = ".flac"
    M4A: str = ".m4a"
    MP4: str = ".mp4"


class VideoExtensions(Enum):
    TS: str = ".ts"


class QueueDownloadStatus(Enum):
    Waiting: str = "⏳️"
    Downloading: str = "▶️"
    Finished: str = "✅"
    Failed: str = "❌"
