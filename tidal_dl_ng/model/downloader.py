import pathlib
from dataclasses import dataclass

from requests import HTTPError
from tidalapi.media import Stream, StreamManifest


@dataclass
class DownloadSegmentResult:
    result: bool
    url: str
    path_segment: pathlib.Path
    id_segment: int
    error: HTTPError | None = None


@dataclass
class TrackStreamInfo:
    """Container for track stream information."""

    stream_manifest: StreamManifest | None
    file_extension: str
    requires_flac_extraction: bool
    media_stream: Stream | None
