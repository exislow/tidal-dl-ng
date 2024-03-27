from dataclasses import dataclass


@dataclass
class ReleaseLatest:
    version: str
    url: str
    release_info: str
