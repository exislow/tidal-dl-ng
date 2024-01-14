from dataclasses import dataclass


@dataclass
class StreamManifest:
    codecs: str
    mime_type: str
    urls: [str]
    file_extension: str
    encryption_type: str | None = None
    encryption_key: str | None = None
