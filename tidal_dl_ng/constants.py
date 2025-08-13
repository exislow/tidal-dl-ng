from enum import StrEnum

CTX_TIDAL: str = "tidal"
REQUESTS_TIMEOUT_SEC: int = 45
EXTENSION_LYRICS: str = ".lrc"
UNIQUIFY_THRESHOLD: int = 99
FILENAME_SANITIZE_PLACEHOLDER: str = "_"
COVER_NAME: str = "cover.jpg"
BLOCK_SIZE: int = 4096
BLOCKS: int = 1024
CHUNK_SIZE: int = BLOCK_SIZE * BLOCKS
PLAYLIST_EXTENSION: str = ".m3u"
PLAYLIST_PREFIX: str = "_"
FILENAME_LENGTH_MAX: int = 255
FORMAT_TEMPLATE_EXPLICIT: str = " (Explicit)"


class QualityVideo(StrEnum):
    P360 = "360"
    P480 = "480"
    P720 = "720"
    P1080 = "1080"


class MediaType(StrEnum):
    TRACK = "track"
    VIDEO = "video"
    PLAYLIST = "playlist"
    ALBUM = "album"
    MIX = "mix"
    ARTIST = "artist"


class CoverDimensions(StrEnum):
    Px80 = "80"
    Px160 = "160"
    Px320 = "320"
    Px640 = "640"
    Px1280 = "1280"
    PxORIGIN = "origin"


class TidalLists(StrEnum):
    Playlists = "Playlists"
    Favorites = "Favorites"
    Mixes = "Mixes"


class QueueDownloadStatus(StrEnum):
    Waiting = "⏳️"
    Downloading = "▶️"
    Finished = "✅"
    Failed = "❌"
    Skipped = "↪️"


FAVORITES: dict[str, dict[str, str]] = {
    "fav_videos": {"name": "Videos", "function_name": "videos"},
    "fav_tracks": {"name": "Tracks", "function_name": "tracks"},
    "fav_mixes": {"name": "Mixes & Radio", "function_name": "mixes"},
    "fav_artists": {"name": "Artists", "function_name": "artists"},
    "fav_albums": {"name": "Albums", "function_name": "albums"},
}


class AudioExtensionsValid(StrEnum):
    FLAC = ".flac"
    M4A = ".m4a"
    MP4 = ".mp4"
    MP3 = ".mp3"
    OGG = ".ogg"
    ALAC = ".alac"
