import pathlib
from dataclasses import dataclass

from requests import HTTPError


@dataclass
class DownloadSegmentResult:
    result: bool
    url: str
    path_segment: pathlib.Path
    id_segment: int
    error: HTTPError | None = None
