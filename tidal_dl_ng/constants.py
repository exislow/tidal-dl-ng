from enum import Enum

CTX_TIDAL: str = "tidal"
REQUESTS_TIMEOUT_SEC = 45
EXTENSION_LYRICS = ".lrc"


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


class StreamManifestMimeType(Enum):
    MPD: str = "application/dash+xml"
    BTS: str = "application/vnd.tidal.bts"
    VIDEO: str = "video/mp2t"


class CoverDimensions(Enum):
    Px320: str = "320x320"
    Px640: str = "640x640"
    Px1280: str = "1280x1280"


class TidalLists(Enum):
    PLAYLISTS: str = "Playlists"
    FAVORITES: str = "Favorites"
    MIXES: str = "Mixes"


class AudioExtensions(Enum):
    FLAC = ".flac"
    M4A = ".m4a"
    MP4 = ".mp4"


class VideoExtensions(Enum):
    TS = ".ts"
