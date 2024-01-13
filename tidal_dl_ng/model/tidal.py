from dataclasses import dataclass


@dataclass
class StreamManifest:
    stream_url: str
    codecs: str
    mime_type: str
    file_extension: str
    encryption_type: str | None = None
    encryption_key: str | None = None
