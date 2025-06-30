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
    P360: str = "360"
    P480: str = "480"
    P720: str = "720"
    P1080: str = "1080"


class MediaType(StrEnum):
    TRACK: str = "track"
    VIDEO: str = "video"
    PLAYLIST: str = "playlist"
    ALBUM: str = "album"
    MIX: str = "mix"
    ARTIST: str = "artist"


class CoverDimensions(StrEnum):
    Px80: str = "80"
    Px160: str = "160"
    Px320: str = "320"
    Px640: str = "640"
    Px1280: str = "1280"


class TidalLists(StrEnum):
    Playlists: str = "Playlists"
    Favorites: str = "Favorites"
    Mixes: str = "Mixes"


class QueueDownloadStatus(StrEnum):
    Waiting: str = "⏳️"
    Downloading: str = "▶️"
    Finished: str = "✅"
    Failed: str = "❌"
    Skipped: str = "↪️"


FAVORITES: {} = {
    "fav_videos": {"name": "Videos", "function_name": "videos"},
    "fav_tracks": {"name": "Tracks", "function_name": "tracks"},
    "fav_mixes": {"name": "Mixes & Radio", "function_name": "mixes"},
    "fav_artists": {"name": "Artists", "function_name": "artists"},
    "fav_albums": {"name": "Albums", "function_name": "albums"},
}
