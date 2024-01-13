from enum import Enum

CTX_TIDAL: str = "tidal"
REQUESTS_TIMEOUT_SEC = 45


class QualityVideo(Enum):
    P360 = 360
    P480 = 480
    P720 = 720
    P1080 = 1080


class MediaType(Enum):
    Track = "track"
    Video = "video"
    Playlist = "playlist"
    Album = "album"
    Mix = "mix"


class SkipExisting(Enum):
    Disabled = False
    Filename = "exact"
    ExtensionIgnore = "extension_ignore"


class StreamManifestMimeType(Enum):
    MPD = "application/dash+xml"
    JSON = "a"
    VIDEO = "video/mp2t"
