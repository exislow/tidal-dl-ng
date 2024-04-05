from dataclasses import dataclass


@dataclass
class ReleaseLatest:
    version: str
    url: str
    release_info: str


@dataclass
class ProjectInformation:
    version: str
    repository_url: str
