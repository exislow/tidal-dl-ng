from enum import Enum

CTX_TIDAL: str = "tidal"
REQUESTS_TIMEOUT_SEC = 45


class QualityVideo(Enum):
    P360: int = 360
    P480: int = 480
    P720: int = 720
    P1080: int = 1080


class MediaType(Enum):
    Track: str = "track"
    Video: str = "video"
    Playlist: str = "playlist"
    Album: str = "album"
    Mix: str = "mix"


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
    PLAYLISTS = "Playlists"
    FAVORITES = "Favorites"
    MIXES = "Mixes"
