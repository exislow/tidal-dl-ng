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
    BTS = "application/vnd.tidal.bts"
    VIDEO = "video/mp2t"


class CoverDimensions(Enum):
    Px320 = "320x320"
    Px640 = "640x640"
    Px1280 = "1280x1280"
