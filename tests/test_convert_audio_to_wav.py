"""Tests for WAV conversion helper."""

import pathlib
from unittest.mock import MagicMock

import pytest
from tidalapi.media import AudioExtensions

from tidal_dl_ng.download import Download


class FFmpegStub:
    """A stubbed FFmpeg wrapper that records calls for assertions."""

    def __init__(self, executable: str):
        """Initialize the stub with the provided executable path."""
        self.executable = executable
        self.options: list[tuple[str, ...]] = []
        self.input_url: str | None = None
        self.output_url: str | None = None
        self.output_kwargs: dict[str, str] = {}

    def option(self, *args: str) -> "FFmpegStub":
        """Record an option call and return self for chaining."""
        self.options.append(args)
        return self

    def input(self, url: str) -> "FFmpegStub":
        """Record the input URL and return self for chaining."""
        self.input_url = url
        return self

    def output(self, url: str, **kwargs: str) -> "FFmpegStub":
        """Record output configuration and return self for chaining."""
        self.output_url = url
        self.output_kwargs = kwargs
        return self

    def execute(self) -> None:
        """No-op execute placeholder for the stub."""


def _build_download(ffmpeg_path: str | None) -> Download:
    """Create a Download instance with stubbed settings and logger."""
    download = object.__new__(Download)
    settings_data = type("SettingsDataStub", (), {"path_binary_ffmpeg": ffmpeg_path})()
    download.settings = type("SettingsStub", (), {"data": settings_data})()
    download.fn_logger = MagicMock()
    return download


def test_convert_audio_to_wav_without_ffmpeg_path(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure conversion is skipped and original path returned when FFmpeg path is missing."""
    media_src: pathlib.Path = tmp_path / "track.flac"
    media_src.write_text("dummy")
    download = _build_download(ffmpeg_path=None)
    monkeypatch.setattr("tidal_dl_ng.download.FFmpeg", lambda *args, **kwargs: None)

    result_path = download._convert_audio_to_wav(media_src)

    assert result_path == media_src
    assert media_src.exists()
    download.fn_logger.error.assert_called_once()


def test_convert_audio_to_wav_runs_ffmpeg_and_removes_source(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run conversion with FFmpeg configured and ensure source is deleted."""
    media_src: pathlib.Path = tmp_path / "track.flac"
    media_src.write_text("dummy")
    download = _build_download(ffmpeg_path="/usr/bin/ffmpeg")

    ffmpeg_instances: list[FFmpegStub] = []

    def _factory(executable: str) -> FFmpegStub:
        """Capture FFmpeg calls for assertions."""
        stub = FFmpegStub(executable=executable)
        ffmpeg_instances.append(stub)
        return stub

    monkeypatch.setattr("tidal_dl_ng.download.FFmpeg", _factory)

    result_path = download._convert_audio_to_wav(media_src)

    assert result_path == media_src.with_suffix(AudioExtensions.WAV)
    assert not media_src.exists()
    assert ffmpeg_instances, "FFmpeg should be invoked during conversion"
    ffmpeg_stub = ffmpeg_instances[0]
    assert ffmpeg_stub.executable == "/usr/bin/ffmpeg"
    assert ffmpeg_stub.input_url == str(media_src)
    assert ffmpeg_stub.output_url == str(result_path)
    assert ffmpeg_stub.output_kwargs == {
        "acodec": "pcm_s16le",
        "map_metadata": "0:g",
        "loglevel": "quiet",
    }
    assert ("hide_banner",) in ffmpeg_stub.options
    assert ("nostdin",) in ffmpeg_stub.options
