from enum import Enum

CTX_TIDAL: str = "tidal"


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
