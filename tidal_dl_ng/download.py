import os
import pathlib
import random
import shutil
import tempfile
import time
from collections.abc import Callable
from uuid import uuid4

import ffmpeg
import m3u8
import requests
from constants import COVER_NAME
from requests.exceptions import HTTPError
from rich.progress import Progress, TaskID
from tidalapi import Album, Mix, Playlist, Session, Track, UserPlaylist, Video
from tidalapi.media import AudioExtensions, Codec, Quality, StreamManifest, VideoExtensions

from tidal_dl_ng.config import Settings
from tidal_dl_ng.constants import EXTENSION_LYRICS, REQUESTS_TIMEOUT_SEC, MediaType, QualityVideo, SkipExisting
from tidal_dl_ng.helper.decryption import decrypt_file, decrypt_security_token
from tidal_dl_ng.helper.exceptions import MediaMissing
from tidal_dl_ng.helper.path import check_file_exists, format_path_media, path_file_sanitize
from tidal_dl_ng.helper.tidal import (
    instantiate_media,
    items_results_all,
    name_builder_album_artist,
    name_builder_artist,
    name_builder_item,
    name_builder_title,
)
from tidal_dl_ng.metadata import Metadata
from tidal_dl_ng.model.gui_data import ProgressBars


# TODO: Set appropriate client string and use it for video download.
# https://github.com/globocom/m3u8#using-different-http-clients
class RequestsClient:
    def download(
        self, uri: str, timeout: int = REQUESTS_TIMEOUT_SEC, headers: dict | None = None, verify_ssl: bool = True
    ):
        if not headers:
            headers = {}

        o = requests.get(uri, timeout=timeout, headers=headers)

        return o.text, o.url


# TODO: Use pathlib.Path everywhere
class Download:
    settings: Settings
    session: Session
    skip_existing: SkipExisting = SkipExisting.Disabled
    fn_logger: Callable
    progress_gui: ProgressBars
    progress: Progress

    def __init__(
        self,
        session: Session,
        path_base: str,
        fn_logger: Callable,
        skip_existing: SkipExisting = SkipExisting.Disabled,
        progress_gui: ProgressBars = None,
        progress: Progress = None,
    ):
        self.settings = Settings()
        self.session = session
        self.skip_existing = skip_existing
        self.fn_logger = fn_logger
        self.progress_gui = progress_gui
        self.progress = progress
        self.path_base = path_base

        if not self.settings.data.path_binary_ffmpeg and (
            self.settings.data.video_convert_mp4 or self.settings.data.extract_flac
        ):
            self.settings.data.video_convert_mp4 = False
            self.settings.data.extract_flac = False

            self.fn_logger.error(
                "FFmpeg path is not set. Videos can be downloaded but will not be processed. FLAC cannot be "
                "extracted from MP4 containers. Make sure FFmpeg is installed. The path to the FFmpeg binary must "
                "be set in (`path_binary_ffmpeg`)."
            )

    def _download(
        self,
        media: Track | Video,
        path_file: str,
    ) -> str:
        media_name: str = name_builder_item(media)
        urls: [str]

        # Get urls for media.
        if isinstance(media, Track):
            urls = media.get_stream().get_stream_manifest().urls
            stream_manifest: StreamManifest = media.get_stream().get_stream_manifest()
        elif isinstance(media, Video):
            m3u8_variant: m3u8.M3U8 = m3u8.load(media.get_url())
            # Find the desired video resolution or the next best one.
            m3u8_playlist, codecs = self._extract_video_stream(m3u8_variant, int(self.settings.data.quality_video))
            # Populate urls.
            urls = m3u8_playlist.files

        # Set the correct progress output channel.
        if self.progress_gui is None:
            progress_stdout: bool = True
        else:
            progress_stdout: bool = False
            # Send signal to GUI with media name
            self.progress_gui.item_name.emit(media_name[:30])

        # Compute total iterations for progress
        urls_count: int = len(urls)

        if urls_count > 1:
            progress_total: int = urls_count
            block_size: int | None = None
        elif urls_count == 1:
            # Will be computed later.
            progress_total: float = None
        else:
            raise ValueError

        # Create progress Task
        p_task: TaskID = self.progress.add_task(
            f"[blue]Item '{media_name[:30]}'",
            total=progress_total,
            visible=progress_stdout,
        )

        # Write content to file until progress is finished.
        while not self.progress.tasks[p_task].finished:
            with open(path_file, "wb") as f:
                for url in urls:
                    try:
                        # Create the request object with stream=True, so the content won't be loaded into memory at once.
                        r = requests.get(url, stream=True, timeout=REQUESTS_TIMEOUT_SEC)

                        r.raise_for_status()

                        # Compute progress iterations based on the file size and update task details.
                        if not progress_total:
                            # Get file size and compute progress steps
                            total_size_in_bytes: int = int(r.headers.get("content-length", 0))
                            block_size: int | None = 1048576
                            progress_total: float = total_size_in_bytes / block_size

                            self.progress.update(p_task, total=progress_total)

                        # Write the content to disk. If `chunk_size` is set to `None` the whole file will be written at once.
                        for data in r.iter_content(chunk_size=block_size):
                            f.write(data)
                            # Advance progress bar.
                            self.progress.advance(p_task)
                    except HTTPError as e:
                        if url is urls[-1]:
                            # It happens, if a track is very short (< 8 seconds or so), that the last URL in `urls` is
                            # invalid (HTTP Error 500) and not necessary. File won't be corrupt.
                            # Thus, advance progress bar to avoid infinity loops.
                            self.progress.advance(p_task)
                        else:
                            # Finish downloading early and report error.
                            # TODO: The track should somehow be marked as corrupt.
                            self.progress.update(p_task, completed=progress_total)
                            self.fn_logger.error(e)
                    finally:
                        # To send the progress to the GUI, we need to emit the percentage.
                        if not progress_stdout:
                            self.progress_gui.item.emit(self.progress.tasks[p_task].percentage)

        if isinstance(media, Track) and stream_manifest.is_encrypted:
            key, nonce = decrypt_security_token(stream_manifest.encryption_key)
            tmp_path_file_decrypted = path_file + "_decrypted"
            decrypt_file(path_file, tmp_path_file_decrypted, key, nonce)
        else:
            tmp_path_file_decrypted = path_file

        return tmp_path_file_decrypted

    def item(
        self,
        file_template: str,
        media: Track | Video = None,
        media_id: str = None,
        media_type: MediaType = None,
        video_download: bool = True,
        download_delay: bool = False,
        quality_audio: Quality | None = None,
        quality_video: QualityVideo | None = None,
        is_parent_album: bool = False,
    ) -> (bool, str):
        try:
            if media_id and media_type:
                # If no media instance is provided, we need to create the media instance.
                media = instantiate_media(self.session, media_type, media_id)
            elif isinstance(media, Track):  # Check if media is available not deactivated / removed from TIDAL.
                if not media.available:
                    self.fn_logger.info(
                        f"This track is not available for listening anymore on TIDAL. Skipping: {name_builder_item(media)}"
                    )

                    return False, ""
                else:
                    # Re-create media instance with full album information
                    media = self.session.track(media.id, with_album=True)
            elif not media:
                raise MediaMissing
        except:
            return False, ""

        # If video download is not allowed end here
        if not video_download and isinstance(media, Video):
            self.fn_logger.info(
                f"Video downloads are deactivated (see settings). Skipping video: {name_builder_item(media)}"
            )

            return False, ""

        # Get extension.
        file_extension: str

        if isinstance(media, Track):
            # If a quality is explicitly set, change it.
            if quality_audio:
                quality_audio_old: Quality = self.adjust_quality_audio(quality_audio)

            file_extension = media.get_stream().get_stream_manifest().file_extension
            # Use M4A extension for MP4 audio tracks, because it looks better and is completely interchangeable.
            file_extension = AudioExtensions.M4A if file_extension == AudioExtensions.MP4 else file_extension

            if self.settings.data.extract_flac:
                do_flac_extract = False

                if (
                    media.get_stream().get_stream_manifest().codecs.upper() == Codec.FLAC
                    and file_extension != AudioExtensions.FLAC
                ):
                    file_extension = AudioExtensions.FLAC
                    do_flac_extract = True
        elif isinstance(media, Video):
            if quality_video:
                quality_video_old: QualityVideo = self.adjust_quality_video(quality_video)

            file_extension = AudioExtensions.MP4 if self.settings.data.video_convert_mp4 else VideoExtensions.TS

        # Create file name and path
        file_name_relative = format_path_media(file_template, media)
        path_media_dst = os.path.abspath(
            os.path.normpath(os.path.join(os.path.expanduser(self.path_base), file_name_relative))
        )

        # Sanitize final path_file to fit into OS boundaries.
        uniquify: bool = self.skip_existing == SkipExisting.Append
        path_media_dst = path_file_sanitize(path_media_dst + file_extension, adapt=True, uniquify=uniquify)

        # Compute if and how downloads need to be skipped.
        if self.skip_existing in (SkipExisting.ExtensionIgnore, SkipExisting.Filename):
            extension_ignore: bool = self.skip_existing == SkipExisting.ExtensionIgnore
            file_exists: bool = check_file_exists(path_media_dst, extension_ignore=extension_ignore)
        else:
            file_exists: bool = False

        if not file_exists:
            # Create a temp directory and file.
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_path_dir:
                tmp_path_file = os.path.join(tmp_path_dir, str(uuid4()))
                # Download media.
                tmp_path_file = self._download(media=media, path_file=tmp_path_file)

                # Convert video from TS to MP4
                if isinstance(media, Video) and self.settings.data.video_convert_mp4:
                    # Convert `*.ts` file to `*.mp4` using ffmpeg
                    tmp_path_file = self._video_convert(tmp_path_file)

                # Extract FLAC from MP4 container using ffmpeg
                if isinstance(media, Track) and self.settings.data.extract_flac and do_flac_extract:
                    tmp_path_file = self._extract_flac(tmp_path_file)

                tmp_path_lyrics: pathlib.Path | None = None
                tmp_path_cover: pathlib.Path | None = None

                # Write metadata to file.
                if not isinstance(media, Video):
                    result_metadata, tmp_path_lyrics, tmp_path_cover = self.metadata_write(
                        media, tmp_path_file, is_parent_album
                    )

                # Move final file to the configured destination directory.
                os.makedirs(os.path.dirname(path_media_dst), exist_ok=True)
                shutil.move(tmp_path_file, path_media_dst)

                # Move lyrics file
                if self.settings.data.lyrics_file and not isinstance(media, Video):
                    self._move_lyrics(tmp_path_lyrics, path_media_dst)

                # Move cover file
                if self.settings.data.cover_album_file:
                    self._move_cover(tmp_path_cover, path_media_dst)
        else:
            self.fn_logger.debug(f"Download skipped, since file exists: '{path_media_dst}'")

        status_download: bool = not file_exists

        if quality_audio:
            # Set quality back to the global user value
            self.adjust_quality_audio(quality_audio_old)

        if quality_video:
            # Set quality back to the global user value
            self.adjust_quality_video(quality_video_old)

        # Whether a file was downloaded or skipped and the download delay is enabled, wait until the next download.
        # Only use this, if you have a list of several Track items.
        if download_delay:
            time_sleep: float = round(random.SystemRandom().uniform(2, 5), 1)

            self.fn_logger.debug(f"Next download will start in {time_sleep} seconds.")
            time.sleep(time_sleep)

        return status_download, path_media_dst

    def adjust_quality_audio(self, quality) -> Quality:
        # Save original quality settings
        quality_old: Quality = self.session.audio_quality
        self.session.audio_quality = quality

        return quality_old

    def adjust_quality_video(self, quality) -> QualityVideo:
        quality_old: QualityVideo = self.settings.data.quality_video

        self.settings.data.quality_video = quality

        return quality_old

    def _move_file(self, path_file_source: pathlib.Path, path_file_destination: str | pathlib.Path) -> bool:
        result: bool

        # Check if the file was downloaded
        if path_file_source and os.path.isfile(path_file_source):
            # Move it.
            shutil.move(path_file_source, path_file_destination)

            result = True
        else:
            result = False

        return result

    def _move_lyrics(self, path_lyrics: pathlib.Path, file_media_dst: str) -> bool:
        # Build tmp lyrics filename
        path_file_lyrics: str = os.path.splitext(file_media_dst)[0] + EXTENSION_LYRICS
        result: bool = self._move_file(path_lyrics, path_file_lyrics)

        return result

    def _move_cover(self, path_cover: pathlib.Path, file_media_dst: str) -> bool:
        # Build tmp lyrics filename
        path_file_cover: pathlib.Path = pathlib.Path(file_media_dst).parent.absolute() / COVER_NAME
        result: bool = self._move_file(path_cover, path_file_cover)

        return result

    def lyrics_to_file(self, dir_destination: pathlib.Path, lyrics: str) -> str:
        return self.write_to_tmp_file(dir_destination, mode="x", content=lyrics)

    def cover_to_file(self, dir_destination: pathlib.Path, image: bytes) -> str:
        return self.write_to_tmp_file(dir_destination, mode="xb", content=image)

    def write_to_tmp_file(self, dir_destination: pathlib.Path, mode: str, content: str | bytes) -> str:
        result: str = dir_destination / str(uuid4())
        encoding: str | None = "utf-8" if isinstance(content, str) else None

        try:
            with open(result, mode=mode, encoding=encoding) as f:
                f.write(content)
        except:
            result = ""

        return result

    @staticmethod
    def cover_data(url: str = None, path_file: str = None) -> str | bytes:
        result: str | bytes = ""

        if url:
            try:
                result = requests.get(url, timeout=REQUESTS_TIMEOUT_SEC).content
            except Exception as e:
                # TODO: Implement propper logging.
                print(e)
        elif path_file:
            try:
                with open(path_file, "rb") as f:
                    result = f.read()
            except OSError as e:
                # TODO: Implement propper logging.
                print(e)

        return result

    def metadata_write(
        self, track: Track, path_media: str, is_parent_album: str
    ) -> (bool, pathlib.Path | None, pathlib.Path | None):
        result: bool = False
        path_lyrics: pathlib.Path | None = None
        path_cover: pathlib.Path | None = None
        release_date: str = (
            track.album.available_release_date.strftime("%Y-%m-%d")
            if track.album.available_release_date
            else track.album.release_date.strftime("%Y-%m-%d") if track.album.release_date else ""
        )
        copy_right: str = track.copyright if hasattr(track, "copyright") and track.copyright else ""
        isrc: str = track.isrc if hasattr(track, "isrc") and track.isrc else ""
        lyrics: str = ""
        cover_data: bytes = None

        if self.settings.data.lyrics_embed or self.settings.data.lyrics_file:
            # Try to retrieve lyrics.
            try:
                lyrics_obj = track.lyrics()

                if lyrics_obj.subtitles:
                    lyrics = lyrics_obj.subtitles
                elif lyrics_obj.text:
                    lyrics = lyrics_obj.text
            except:
                lyrics = ""
                # TODO: Implement proper logging.
                print(f"Could not retrieve lyrics for `{name_builder_item(track)}`.")

        if lyrics and self.settings.data.lyrics_file:
            path_lyrics = self.lyrics_to_file(pathlib.Path(path_media).parent, lyrics)

        if self.settings.data.metadata_cover_embed or (self.settings.data.cover_album_file and is_parent_album):
            url_cover = track.album.image(int(self.settings.data.metadata_cover_dimension))
            cover_data = self.cover_data(url=url_cover)

        if cover_data and self.settings.data.cover_album_file and is_parent_album:
            path_cover = self.cover_to_file(pathlib.Path(path_media).parent, cover_data)

        # `None` values are not allowed.
        m: Metadata = Metadata(
            path_file=path_media,
            lyrics=lyrics,
            copy_right=copy_right,
            title=name_builder_title(track),
            artists=name_builder_artist(track),
            album=track.album.name if track.album else "",
            tracknumber=track.track_num,
            date=release_date,
            isrc=isrc,
            albumartist=name_builder_album_artist(track),
            totaltrack=track.album.num_tracks if track.album and track.album.num_tracks else 1,
            totaldisc=track.album.num_volumes if track.album and track.album.num_volumes else 1,
            discnumber=track.volume_num if track.volume_num else 1,
            cover_data=cover_data if self.settings.data.metadata_cover_embed else None,
        )

        m.save()

        result = True

        return result, path_lyrics, path_cover

    def items(
        self,
        file_template: str,
        media: Album | Playlist | UserPlaylist | Mix = None,
        media_id: str = None,
        media_type: MediaType = None,
        video_download: bool = False,
        download_delay: bool = True,
        quality_audio: Quality | None = None,
        quality_video: QualityVideo | None = None,
    ):
        # If no media instance is provided, we need to create the media instance.
        if media_id and media_type:
            media = instantiate_media(self.session, media_type, media_id)
        elif not media:
            raise MediaMissing

        # Create file name and path
        file_name_relative = format_path_media(file_template, media)

        # Get the name of the list and check, if videos should be included.
        videos_include: bool = True

        if isinstance(media, Mix):
            list_media_name = media.title[:30]
        elif video_download:
            list_media_name = name_builder_title(media)[:30]
        else:
            videos_include = False
            list_media_name = name_builder_title(media)[:30]

        # Get all items of the list.
        items = items_results_all(media, videos_include=videos_include)

        # Determine where to redirect the progress information.
        if self.progress_gui is None:
            progress_stdout: bool = True
        else:
            progress_stdout: bool = False
            self.progress_gui.list_name.emit(list_media_name[:30])

        # Create the list progress task.
        p_task1: TaskID = self.progress.add_task(
            f"[green]List '{list_media_name}'", total=len(items), visible=progress_stdout
        )

        is_album: bool = isinstance(media, Album)

        # Iterate through list items
        while not self.progress.finished:
            for item_media in items:
                # Download the item.
                status_download, result_path_file = self.item(
                    media=item_media,
                    file_template=file_name_relative,
                    quality_audio=quality_audio,
                    quality_video=quality_video,
                    download_delay=download_delay,
                    is_parent_album=is_album,
                )

                # Advance progress bar.
                self.progress.advance(p_task1)

                if not progress_stdout:
                    self.progress_gui.list_item.emit(self.progress.tasks[p_task1].percentage)

    def _video_convert(self, path_file: str) -> str:
        path_file_out = path_file + AudioExtensions.MP4
        result, _ = (
            ffmpeg.input(path_file)
            .output(path_file_out, map=0, c="copy", loglevel="quiet")
            .run(cmd=self.settings.data.path_binary_ffmpeg)
        )

        return path_file_out

    def _extract_flac(self, path_media_src: str) -> str:
        path_media_out = path_media_src + AudioExtensions.FLAC
        result, _ = (
            ffmpeg.input(path_media_src)
            .output(
                path_media_out, map=0, movflags="use_metadata_tags", acodec="copy", map_metadata="0:g", loglevel="quiet"
            )
            .run(cmd=self.settings.data.path_binary_ffmpeg)
        )

        return path_media_out

    def _extract_video_stream(self, m3u8_variant: m3u8.M3U8, quality: int) -> (m3u8.M3U8 | bool, str):
        m3u8_playlist: m3u8.M3U8 | bool = False
        resolution_best: int = 0
        mime_type: str = ""

        if m3u8_variant.is_variant:
            for playlist in m3u8_variant.playlists:
                if resolution_best < playlist.stream_info.resolution[1]:
                    resolution_best = playlist.stream_info.resolution[1]
                    m3u8_playlist = m3u8.load(playlist.uri)
                    mime_type = playlist.stream_info.codecs

                    if quality == playlist.stream_info.resolution[1]:
                        break

        return m3u8_playlist, mime_type
