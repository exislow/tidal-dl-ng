import base64
import json
import os
import random
import shutil
import tempfile
import time
from logging import Logger
from uuid import uuid4

import ffmpeg
import m3u8
import requests
from pathvalidate import sanitize_filepath
from requests.exceptions import HTTPError
from rich.progress import Progress
from tidalapi import Album, Mix, Playlist, Session, Track, UserPlaylist, Video

from tidal_dl_ng.config import Settings
from tidal_dl_ng.constants import REQUESTS_TIMEOUT_SEC, MediaType
from tidal_dl_ng.helper.decryption import decrypt_file, decrypt_security_token
from tidal_dl_ng.helper.exceptions import MediaUnknown
from tidal_dl_ng.helper.path import check_file_exists, format_path_media, path_validate
from tidal_dl_ng.helper.wrapper import WrapperLogger
from tidal_dl_ng.metadata import Metadata
from tidal_dl_ng.model.gui_data import ProgressBars


# TODO: Set appropriate client string and use it for video download.
# https://github.com/globocom/m3u8#using-different-http-clients
class RequestsClient:
    def download(self, uri: str, timeout: int = None, headers: dict | None = None, verify_ssl: bool = True):
        if not headers:
            headers = {}

        o = requests.get(uri, timeout=timeout, headers=headers)

        return o.text, o.url


class Download:
    # TODO: Implement download cover 1280.
    session: Session = None
    skip_existing: bool = False

    def __init__(self, session: Session, skip_existing: bool = False):
        self.session = session
        self.skip_existing = skip_existing

    def _video(self, video: Video, path_file: str) -> str | None:
        result: str | None = None
        m3u8_variant: m3u8.M3U8 = m3u8.load(video.get_url())
        m3u8_playlist: m3u8.M3U8 | bool = False
        settings: Settings = Settings()
        resolution_best: int = 0

        if m3u8_variant.is_variant:
            for playlist in m3u8_variant.playlists:
                if resolution_best < playlist.stream_info.resolution[1]:
                    resolution_best = playlist.stream_info.resolution[1]
                    m3u8_playlist = m3u8.load(playlist.uri)

                    if settings.data.quality_video.value == playlist.stream_info.resolution[1]:
                        break

            if m3u8_playlist:
                with open(path_file, "wb") as f:
                    for segment in m3u8_playlist.data["segments"]:
                        url = segment["uri"]
                        r = requests.get(url, timeout=REQUESTS_TIMEOUT_SEC)

                        f.write(r.content)

                result = path_file

        return result

    def item(
        self,
        path_base: str,
        fn_logger: Logger | WrapperLogger,
        id_media: str = None,
        file_template: str = None,
        media: Track | Video = None,
        media_type: MediaType = None,
        video_download: bool = True,
        progress_gui: ProgressBars = None,
        progress: Progress = None,
    ) -> (bool, str):
        if id_media:
            if media_type == MediaType.Track:
                media = Track(self.session, id_media)
            elif media_type == MediaType.Video:
                media = Video(self.session, id_media)

                # If video download is not allowed
                if not video_download:
                    return False, ""
            else:
                raise MediaUnknown
        else:
            media = media

        if file_template:
            file_name_relative = format_path_media(file_template, media)
            path_file = os.path.abspath(os.path.normpath(os.path.join(path_base, file_name_relative)))
        else:
            path_file = os.path.abspath(os.path.normpath(format_path_media(path_base, media)))

        if isinstance(media, Track):
            stream = media.stream()
            # TODO: Check for `manifest_mime_type'. It could be also xml.
            stream_manifest = json.loads(base64.b64decode(stream.manifest).decode("utf-8"))
            # TODO: Handle more than one dowload URL
            stream_url = stream_manifest["urls"][0]
            file_extension = self.get_file_extension(stream_url, stream_manifest["codecs"])
        elif isinstance(media, Video):
            file_extension = ".ts"

        path_file = sanitize_filepath(path_file + file_extension)
        # Check if path & filename longer than the OS allows. Shorten if necessary.
        validation_result, path_file = path_validate(path_file, True)

        download_skip = check_file_exists(path_file) if self.skip_existing else False

        if not download_skip:
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_path_dir:
                tmp_path_file = os.path.join(tmp_path_dir, str(uuid4()) + file_extension)

                if isinstance(media, Track):
                    # TODO: Refactor to separate method.
                    if progress_gui is None:
                        progress_stdout: bool = True
                    else:
                        progress_stdout: bool = False
                        progress_gui.item_name.emit(media.name)

                    try:
                        # Streaming, so we can iterate over the response.
                        r = requests.get(stream_url, stream=True, timeout=REQUESTS_TIMEOUT_SEC)
                        r.raise_for_status()
                        total_size_in_bytes = int(r.headers.get("content-length", 0))
                        block_size = 4096
                        p_task = progress.add_task(
                            f"[blue]Item '{media.name[:30]}'",
                            total=total_size_in_bytes / block_size,
                            visible=progress_stdout,
                        )

                        while not progress.tasks[p_task].finished:
                            with open(tmp_path_file, "wb") as f:
                                for data in r.iter_content(chunk_size=block_size):
                                    f.write(data)
                                    progress.advance(p_task, advance=1)

                                    if not progress_stdout:
                                        progress_gui.item.emit(progress.tasks[p_task].percentage)
                    except HTTPError:
                        # TODO: Handle Exception...
                        pass

                    needs_decryption = self.is_encrypted(stream_manifest)

                    if needs_decryption:
                        key, nonce = decrypt_security_token(stream_manifest["encryptionKey"])
                        tmp_path_file_decrypted = tmp_path_file + "_decrypted"
                        decrypt_file(tmp_path_file, tmp_path_file_decrypted, key, nonce)
                    else:
                        tmp_path_file_decrypted = tmp_path_file

                    self.metadata_write(media, tmp_path_file_decrypted)
                elif isinstance(media, Video):
                    tmp_path_file_decrypted = self._video(media, tmp_path_file)

                    # TODO: Check if is possible to write metadata to MPEG Transport Stream files.
                    # TODO: Make optional.
                    if True:
                        tmp_path_file_decrypted = self._video_convert(tmp_path_file_decrypted)
                        path_file = os.path.splitext(path_file)[0] + ".mp4"

                os.makedirs(os.path.dirname(path_file), exist_ok=True)
                shutil.move(tmp_path_file_decrypted, path_file)
        else:
            fn_logger.debug(f"Download skipped, since file exists: '{path_file}'")

        return not download_skip, path_file

    def cover_url(self, sid: str, width: int = 320, height: int = 320):
        if sid is None:
            return ""

        return f"https://resources.tidal.com/images/{sid.replace('-', '/')}/{int(width)}x{int(height)}.jpg"

    def metadata_write(self, track: Track, path_file: str):
        settings: Settings = Settings()
        result: bool = False
        release_date: str = track.album.release_date.strftime("%Y-%m-%d") if track.album.release_date else ""
        copy_right: str = track.copyright if track.copyright else ""
        isrc: str = track.isrc if track.isrc else ""

        try:
            lyrics: str = track.lyrics().subtitles if hasattr(track, "lyrics") else ""
        except HTTPError:
            lyrics: str = ""

        # TODO: Check if it is possible to pass "None" values.
        m: Metadata = Metadata(
            path_file=path_file,
            lyrics=lyrics,
            copy_right=copy_right,
            title=track.name,
            artists=[artist.name for artist in track.artists],
            album=track.album.name,
            tracknumber=track.track_num,
            date=release_date,
            isrc=isrc,
            albumartist=track.artist.name,
            totaltrack=track.album.num_tracks if track.album.num_tracks else 1,
            totaldisc=track.album.num_volumes if track.album.num_volumes else 1,
            discnumber=track.volume_num,
            url_cover=self.cover_url(track.album.cover, settings.data.metadata_cover_width,
                                     settings.data.metadata_cover_height),
        )

        m.save()

        result = True

        return result

    def items(
        self,
        path_base: str,
        fn_logger: Logger | WrapperLogger,
        id_media: str = None,
        media_type: MediaType = None,
        file_template: str = None,
        list_media: Album | Playlist | UserPlaylist | Mix = None,
        video_download: bool = False,
        progress_gui: ProgressBars = None,
        progress: Progress = None,
        download_delay: bool = True,
    ):
        if not list_media:
            if media_type == MediaType.Album:
                list_media = Album(self.session, id_media)
            elif media_type == MediaType.Playlist:
                list_media = Playlist(self.session, id_media)
            elif media_type == MediaType.Mix:
                list_media = Mix(self.session, id_media)
            else:
                raise MediaUnknown

        if file_template:
            file_name_relative = format_path_media(file_template, list_media)
            path_file = path_base
        else:
            file_name_relative = file_template
            path_file = format_path_media(path_base, list_media)

        # TODO: Extend with pagination support: Iterate through `items` and `tracks`until len(returned list) == 0
        if isinstance(list_media, Mix):
            items = list_media.items()
            list_media_name = list_media.title[:30]
        elif video_download:
            items = list_media.items(limit=100)
            list_media_name = list_media.name[:30]
        else:
            items = list_media.tracks(limit=999)
            list_media_name = list_media.name[:30]

        if progress_gui is None:
            progress_stdout: bool = True
        else:
            progress_stdout: bool = False

        p_task1 = progress.add_task(f"[green]List '{list_media_name}'", total=len(items), visible=progress_stdout)

        while not progress.finished:
            for media in items:
                Progress()
                # TODO: Handle return value of `track` method.
                status_download, result_path_file = self.item(
                    path_base=path_file,
                    file_template=file_name_relative,
                    media=media,
                    progress_gui=progress_gui,
                    progress=progress,
                    fn_logger=fn_logger,
                )
                progress.advance(p_task1)

                if not progress_stdout:
                    progress_gui.list_item.emit(progress.tasks[p_task1].percentage)

                if download_delay and status_download:
                    time_sleep: float = round(random.SystemRandom().uniform(2, 5), 1)

                    # TODO: Fix logging. Is not displayed in debug window.
                    fn_logger.debug(f"Next download will start in {time_sleep} seconds.")
                    time.sleep(time_sleep)

    def is_encrypted(self, manifest: dict) -> bool:
        result = manifest["encryptionType"] != "NONE"

        return result

    def get_file_extension(self, stream_url: str, stream_codec: str) -> str:
        result = None

        if ".flac" in stream_url:
            result = ".flac"
        elif ".mp4" in stream_url:
            if "ac4" in stream_codec or "mha1" in stream_codec:
                result = ".mp4"
            elif "flac" in stream_codec:
                result = ".flac"
            else:
                result = ".m4a"
        else:
            result = ".m4a"

        return result

    def _video_convert(self, path_file: str) -> str:
        path_file_out = os.path.splitext(path_file)[0] + ".mp4"
        result, _ = ffmpeg.input(path_file).output(path_file_out, map=0, c="copy").run()

        return path_file_out
