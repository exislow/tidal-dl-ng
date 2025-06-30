import os
import pathlib
import random
import shutil
import tempfile
import time
from collections.abc import Callable
from concurrent import futures
from threading import Event
from uuid import uuid4

import m3u8
import requests
from ffmpeg import FFmpeg
from pathvalidate import sanitize_filename
from requests.adapters import HTTPAdapter, Retry
from requests.exceptions import HTTPError
from rich.progress import Progress, TaskID
from tidalapi import Album, Mix, Playlist, Session, Track, UserPlaylist, Video
from tidalapi.exceptions import TooManyRequests
from tidalapi.media import AudioExtensions, Codec, Quality, Stream, StreamManifest, VideoExtensions

from tidal_dl_ng.config import Settings
from tidal_dl_ng.constants import (
    CHUNK_SIZE,
    COVER_NAME,
    EXTENSION_LYRICS,
    PLAYLIST_EXTENSION,
    PLAYLIST_PREFIX,
    REQUESTS_TIMEOUT_SEC,
    MediaType,
    QualityVideo,
)
from tidal_dl_ng.helper.decryption import decrypt_file, decrypt_security_token
from tidal_dl_ng.helper.exceptions import MediaMissing
from tidal_dl_ng.helper.path import (
    check_file_exists,
    format_path_media,
    path_file_sanitize,
    url_to_filename,
)
from tidal_dl_ng.helper.tidal import (
    instantiate_media,
    items_results_all,
    name_builder_album_artist,
    name_builder_artist,
    name_builder_item,
    name_builder_title,
)
from tidal_dl_ng.metadata import Metadata
from tidal_dl_ng.model.downloader import DownloadSegmentResult
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
    skip_existing: bool = False
    fn_logger: Callable
    progress_gui: ProgressBars
    progress: Progress
    progress_overall: Progress
    event_abort: Event
    event_run: Event

    def __init__(
        self,
        session: Session,
        path_base: str,
        fn_logger: Callable,
        skip_existing: bool = False,
        progress_gui: ProgressBars = None,
        progress: Progress = None,
        progress_overall: Progress = None,
        event_abort: Event = None,
        event_run: Event = None,
    ):
        self.settings = Settings()
        self.session = session
        self.skip_existing = skip_existing
        self.fn_logger = fn_logger
        self.progress_gui = progress_gui
        self.progress = progress
        self.progress_overall = progress_overall
        self.path_base = path_base
        self.event_abort = event_abort
        self.event_run = event_run

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
        path_file: pathlib.Path,
        stream_manifest: StreamManifest | None = None,
    ) -> (bool, pathlib.Path):
        media_name: str = name_builder_item(media)
        urls: [str]
        path_base: pathlib.Path = path_file.parent
        result_segments: bool = True
        dl_segment_results: [DownloadSegmentResult] = []
        result_merge: bool = False

        # Get urls for media.
        try:
            if isinstance(media, Track):
                urls = stream_manifest.get_urls()
            elif isinstance(media, Video):
                m3u8_variant: m3u8.M3U8 = m3u8.load(media.get_url())
                # Find the desired video resolution or the next best one.
                m3u8_playlist, codecs = self._extract_video_stream(m3u8_variant, int(self.settings.data.quality_video))
                # Populate urls.
                urls = m3u8_playlist.files
        except Exception:
            return False, path_file

        # Set the correct progress output channel.
        if self.progress_gui is None:
            progress_to_stdout: bool = True
        else:
            progress_to_stdout: bool = False
            # Send signal to GUI with media name
            self.progress_gui.item_name.emit(media_name[:30])

        # Compute total iterations for progress
        urls_count: int = len(urls)

        if urls_count > 1:
            progress_total: int = urls_count
            block_size: int | None = None
        elif urls_count == 1:
            try:
                # Get file size and compute progress steps
                r = requests.head(urls[0], timeout=REQUESTS_TIMEOUT_SEC)
                total_size_in_bytes: int = int(r.headers.get("content-length", 0))
                block_size: int | None = 1048576
                progress_total: float = total_size_in_bytes / block_size
            finally:
                r.close()
        else:
            raise ValueError

        # Create progress Task
        p_task: TaskID = self.progress.add_task(
            f"[blue]Item '{media_name[:30]}'",
            total=progress_total,
            visible=progress_to_stdout,
        )

        # Download segments until progress is finished.
        # TODO: Compute download speed (https://github.com/Textualize/rich/blob/master/examples/downloader.py)
        while not self.progress.tasks[p_task].finished:
            with futures.ThreadPoolExecutor(
                max_workers=self.settings.data.downloads_simultaneous_per_track_max
            ) as executor:
                # Dispatch all download tasks to worker threads
                l_futures: [futures.Future] = [
                    executor.submit(self._download_segment, url, path_base, block_size, p_task, progress_to_stdout)
                    for url in urls
                ]

                # Report results as they become available
                for future in futures.as_completed(l_futures):
                    # Retrieve result
                    result_dl_segment: DownloadSegmentResult = future.result()

                    dl_segment_results.append(result_dl_segment)

                    # check for a link that was skipped
                    if not result_dl_segment.result and (result_dl_segment.url is not urls[-1]):
                        # Sometimes it happens, if a track is very short (< 8 seconds or so), that the last URL in `urls` is
                        # invalid (HTTP Error 500) and not necessary. File won't be corrupt.
                        # If this is NOT the case, but any other URL has resulted in an error,
                        # mark the whole thing as corrupt.
                        result_segments = False
                        self.fn_logger.error(f"Something went wrong while downloading {media_name}. File is corrupt!")

                    # If app is terminated (CTRL+C)
                    if self.event_abort.is_set():
                        # Cancel all not yet started tasks
                        for f in l_futures:
                            f.cancel()

                        return False, path_file

        tmp_path_file_decrypted: pathlib.Path = path_file

        # Only if no error happened while downloading.
        if result_segments:
            # Bring list into right order, so segments can be easily merged.
            dl_segment_results.sort(key=lambda x: x.id_segment)
            result_merge: bool = self._segments_merge(path_file, dl_segment_results)

            if not result_merge:
                self.fn_logger.error(f"Something went wrong while writing to {media_name}. File is corrupt!")
            elif result_merge and isinstance(media, Track) and stream_manifest.is_encrypted:
                key, nonce = decrypt_security_token(stream_manifest.encryption_key)
                tmp_path_file_decrypted = path_file.with_suffix(".decrypted")
                decrypt_file(path_file, tmp_path_file_decrypted, key, nonce)

        return result_merge, tmp_path_file_decrypted

    def _segments_merge(self, path_file, dl_segment_results) -> bool:
        result: bool = True

        # Copy the content of all segments into one file.
        try:
            with path_file.open("wb") as f_target:
                for dl_segment_result in dl_segment_results:
                    with dl_segment_result.path_segment.open("rb") as f_segment:
                        # Read and write junks, which gives better HDD write performance
                        while segment := f_segment.read(CHUNK_SIZE):
                            f_target.write(segment)

                    # Delete segment from HDD
                    dl_segment_result.path_segment.unlink()

        except Exception:
            if dl_segment_result is not dl_segment_results[-1]:
                result = False

        return result

    def _download_segment(
        self, url: str, path_base: pathlib.Path, block_size: int | None, p_task: TaskID, progress_to_stdout: bool
    ) -> DownloadSegmentResult:
        result: bool = False
        path_segment: pathlib.Path = path_base / url_to_filename(url)
        # Calculate the segment ID based on the file name within the URL.
        filename_stem: str = str(path_segment.stem).split("_")[-1]
        # CAUTION: This is a workaround, so BTS (LOW quality) track will work. They usually have only ONE link.
        id_segment: int = int(filename_stem) if filename_stem.isdecimal() else 0
        error: HTTPError | None = None

        # If app is terminated (CTRL+C)
        if self.event_abort.is_set():
            return DownloadSegmentResult(
                result=False, url=url, path_segment=path_segment, id_segment=id_segment, error=error
            )

        if not self.event_run.is_set():
            self.event_run.wait()

        # Retry download on failed segments, with an exponential delay between retries
        with requests.Session() as s:
            retries = Retry(total=5, backoff_factor=1)  # , status_forcelist=[ 502, 503, 504 ])

            s.mount("https://", HTTPAdapter(max_retries=retries))

            try:
                # Create the request object with stream=True, so the content won't be loaded into memory at once.
                r = s.get(url, stream=True, timeout=REQUESTS_TIMEOUT_SEC)

                r.raise_for_status()

                # Write the content to disk. If `chunk_size` is set to `None` the whole file will be written at once.
                with path_segment.open("wb") as f:
                    for data in r.iter_content(chunk_size=block_size):
                        f.write(data)
                        # Advance progress bar.
                        self.progress.advance(p_task)

                result = True
            except Exception:
                self.progress.advance(p_task)

        # To send the progress to the GUI, we need to emit the percentage.
        if not progress_to_stdout:
            self.progress_gui.item.emit(self.progress.tasks[p_task].percentage)

        return DownloadSegmentResult(
            result=result, url=url, path_segment=path_segment, id_segment=id_segment, error=error
        )

    def extension_guess(
        self, quality_audio: Quality, metadata_tags: [str], is_video: bool
    ) -> AudioExtensions | VideoExtensions:
        result: AudioExtensions | VideoExtensions

        if is_video:
            result = AudioExtensions.MP4 if self.settings.data.video_convert_mp4 else VideoExtensions.TS
        else:
            result = (
                AudioExtensions.FLAC
                if (
                    self.settings.data.extract_flac
                    and quality_audio in (Quality.hi_res_lossless, Quality.high_lossless)
                )
                or ("HIRES_LOSSLESS" not in metadata_tags and quality_audio not in (Quality.low_96k, Quality.low_320k))
                or quality_audio == Quality.high_lossless
                else AudioExtensions.M4A
            )

        return result

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
        list_position: int = 0,
        list_total: int = 0,
    ) -> (bool, pathlib.Path):
        try:
            if media_id and media_type:
                # If no media instance is provided, we need to create the media instance.
                media = instantiate_media(self.session, media_type, media_id)
            elif isinstance(media, Track | Video):  # Check if media is available not deactivated / removed from TIDAL.
                if not media.available:
                    self.fn_logger.info(
                        f"This item is not available for listening anymore on TIDAL. Skipping: {name_builder_item(media)}"
                    )

                    return False, ""
                elif isinstance(media, Track):
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

        # Create file name and path
        file_extension_dummy: str = self.extension_guess(
            quality_audio,
            metadata_tags=[] if isinstance(media, Video) else media.media_metadata_tags,
            is_video=isinstance(media, Video),
        )
        file_name_relative: str = format_path_media(
            file_template, media, self.settings.data.album_track_num_pad_min, list_position, list_total
        )
        path_media_dst: pathlib.Path = (
            pathlib.Path(self.path_base).expanduser() / (file_name_relative + file_extension_dummy)
        ).absolute()

        # Sanitize final path_file to fit into OS boundaries.
        path_media_dst = pathlib.Path(path_file_sanitize(path_media_dst, adapt=True))

        # Compute if and how downloads need to be skipped.
        skip_download: bool = False

        if self.skip_existing:
            skip_file: bool = check_file_exists(path_media_dst, extension_ignore=False)

            if self.settings.data.symlink_to_track and not isinstance(media, Video):
                # Compute symlink tracks path, sanitize and check if file exists
                file_name_track_dir_relative: str = format_path_media(self.settings.data.format_track, media)
                path_media_track_dir: pathlib.Path = (
                    pathlib.Path(self.path_base).expanduser() / (file_name_track_dir_relative + file_extension_dummy)
                ).absolute()
                path_media_track_dir = pathlib.Path(path_file_sanitize(path_media_track_dir, adapt=True))
                file_exists_track_dir: bool = check_file_exists(path_media_track_dir, extension_ignore=False)
                file_exists_playlist_dir: bool = (
                    not file_exists_track_dir and skip_file and not path_media_dst.is_symlink()
                )
                skip_download = file_exists_playlist_dir or file_exists_track_dir

                # If
                if skip_file and file_exists_playlist_dir:
                    skip_file = False
        else:
            skip_file: bool = False

        if not skip_file:
            # If a quality is explicitly set, change it and remember the previously set quality.
            quality_audio_old: Quality = self.adjust_quality_audio(quality_audio) if quality_audio else quality_audio
            quality_video_old: QualityVideo = (
                self.adjust_quality_video(quality_video) if quality_video else quality_video
            )
            do_flac_extract = False
            # Get extension.
            file_extension: str
            stream_manifest: StreamManifest | None = None

            if isinstance(media, Track):
                try:
                    media_stream: Stream = media.get_stream()
                    stream_manifest = media_stream.get_stream_manifest()
                except TooManyRequests:
                    self.fn_logger.exception(
                        f"Too many requests against TIDAL backend. Skipping '{name_builder_item(media)}'. "
                        f"Consider to activate delay between downloads."
                    )

                    return False, ""
                except Exception:
                    self.fn_logger.exception(f"Something went wrong. Skipping '{name_builder_item(media)}'.")

                    return False, ""

                file_extension = stream_manifest.file_extension

                if self.settings.data.extract_flac and (
                    stream_manifest.codecs.upper() == Codec.FLAC and file_extension != AudioExtensions.FLAC
                ):
                    file_extension = AudioExtensions.FLAC
                    do_flac_extract = True
            elif isinstance(media, Video):
                file_extension = AudioExtensions.MP4 if self.settings.data.video_convert_mp4 else VideoExtensions.TS

            # If file extension was guessed wrong in the beginning
            if path_media_dst.suffix != file_extension:
                # Compute file name, sanitize once again, because file extension could have been replaced after guessing it first and create destination directory
                path_media_dst = path_media_dst.with_suffix(file_extension)
                path_media_dst = pathlib.Path(path_file_sanitize(path_media_dst, adapt=True))

            os.makedirs(path_media_dst.parent, exist_ok=True)

            if not skip_download:
                # Create a temp directory and file.
                with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_path_dir:
                    tmp_path_file: pathlib.Path = pathlib.Path(tmp_path_dir) / str(uuid4())

                    # Create empty file
                    tmp_path_file.touch()

                    # Download media.
                    result_download, tmp_path_file = self._download(
                        media=media, stream_manifest=stream_manifest, path_file=tmp_path_file
                    )

                    if result_download:
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
                                media, tmp_path_file, is_parent_album, media_stream
                            )

                        # Move lyrics file
                        if self.settings.data.lyrics_file and not isinstance(media, Video) and tmp_path_lyrics:
                            self._move_lyrics(tmp_path_lyrics, path_media_dst)

                        # Move cover file
                        # TODO: Cover is downloaded with every track of the album. Needs refactoring, so cover is only
                        #  downloaded for an album once.
                        if self.settings.data.cover_album_file and tmp_path_cover:
                            self._move_cover(tmp_path_cover, path_media_dst)

                        self.fn_logger.info(f"Downloaded item '{name_builder_item(media)}'.")

                        # Move final file to the configured destination directory.
                        shutil.move(tmp_path_file, path_media_dst)

            # If files needs to be symlinked, do postprocessing here.
            if self.settings.data.symlink_to_track and not isinstance(media, Video):
                path_media_track_dir: pathlib.Path = self.media_move_and_symlink(media, path_media_dst, file_extension)

            if quality_audio:
                # Set quality back to the global user value
                self.adjust_quality_audio(quality_audio_old)

            if quality_video:
                # Set quality back to the global user value
                self.adjust_quality_video(quality_video_old)
        else:
            self.fn_logger.debug(f"Download skipped, since file exists: '{path_media_dst}'")

        status_download: bool = not skip_file

        # Whether a file was downloaded or skipped and the download delay is enabled, wait until the next download.
        # Only use this, if you have a list of several Track items.
        if (download_delay and not skip_file) and not self.event_abort.is_set():
            time_sleep: float = round(
                random.SystemRandom().uniform(
                    self.settings.data.download_delay_sec_min, self.settings.data.download_delay_sec_max
                ),
                1,
            )

            self.fn_logger.debug(f"Next download will start in {time_sleep} seconds.")
            time.sleep(time_sleep)

        return status_download, path_media_dst

    def media_move_and_symlink(
        self, media: Track | Video, path_media_src: pathlib.Path, file_extension: str
    ) -> pathlib.Path:
        # Compute tracks path, sanitize and ensure path exists
        file_name_relative: str = format_path_media(self.settings.data.format_track, media)
        path_media_dst: pathlib.Path = (
            pathlib.Path(self.path_base).expanduser() / (file_name_relative + file_extension)
        ).absolute()
        path_media_dst = pathlib.Path(path_file_sanitize(path_media_dst, adapt=True))

        os.makedirs(path_media_dst.parent, exist_ok=True)

        # Move item and symlink it
        if path_media_dst != path_media_src:
            if self.skip_existing:
                skip_file: bool = check_file_exists(path_media_dst, extension_ignore=False)
                skip_symlink: bool = path_media_src.is_symlink()
            else:
                skip_file: bool = False
                skip_symlink: bool = False

            if not skip_file:
                self.fn_logger.debug(f"Move: {path_media_src} -> {path_media_dst}")
                shutil.move(path_media_src, path_media_dst)

            if not skip_symlink:
                self.fn_logger.debug(f"Symlink: {path_media_src} -> {path_media_dst}")
                path_media_dst_relative: pathlib.Path = path_media_dst.relative_to(path_media_src.parent, walk_up=True)

                path_media_src.unlink(missing_ok=True)
                path_media_src.symlink_to(path_media_dst_relative)

        return path_media_dst

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
        if path_file_source and path_file_source.is_file():
            # Move it.
            shutil.move(path_file_source, path_file_destination)

            result = True
        else:
            result = False

        return result

    def _move_lyrics(self, path_lyrics: pathlib.Path, file_media_dst: pathlib.Path) -> bool:
        # Build tmp lyrics filename
        path_file_lyrics: pathlib.Path = file_media_dst.with_suffix(EXTENSION_LYRICS)
        result: bool = self._move_file(path_lyrics, path_file_lyrics)

        return result

    def _move_cover(self, path_cover: pathlib.Path, file_media_dst: pathlib.Path) -> bool:
        # Build tmp lyrics filename
        path_file_cover: pathlib.Path = file_media_dst.parent / COVER_NAME
        result: bool = self._move_file(path_cover, path_file_cover)

        return result

    def lyrics_to_file(self, dir_destination: pathlib.Path, lyrics: str) -> str:
        return self.write_to_tmp_file(dir_destination, mode="x", content=lyrics)

    def cover_to_file(self, dir_destination: pathlib.Path, image: bytes) -> str:
        return self.write_to_tmp_file(dir_destination, mode="xb", content=image)

    def write_to_tmp_file(self, dir_destination: pathlib.Path, mode: str, content: str | bytes) -> str:
        result: pathlib.Path = dir_destination / str(uuid4())
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
                response: requests.Response = requests.get(url, timeout=REQUESTS_TIMEOUT_SEC)
                result = response.content
            except Exception as e:
                # TODO: Implement propper logging.
                print(e)
            finally:
                response.close()
        elif path_file:
            try:
                with open(path_file, "rb") as f:
                    result = f.read()
            except OSError as e:
                # TODO: Implement propper logging.
                print(e)

        return result

    def metadata_write(
        self, track: Track, path_media: pathlib.Path, is_parent_album: bool, media_stream: Stream
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
            path_lyrics = self.lyrics_to_file(path_media.parent, lyrics)

        if self.settings.data.metadata_cover_embed or (self.settings.data.cover_album_file and is_parent_album):
            url_cover = track.album.image(int(self.settings.data.metadata_cover_dimension))
            cover_data = self.cover_data(url=url_cover)

        if cover_data and self.settings.data.cover_album_file and is_parent_album:
            path_cover = self.cover_to_file(path_media.parent, cover_data)

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
            album_replay_gain=media_stream.album_replay_gain,
            album_peak_amplitude=media_stream.album_peak_amplitude,
            track_replay_gain=media_stream.track_replay_gain,
            track_peak_amplitude=media_stream.track_peak_amplitude,
            url_share=track.share_url if track.share_url else "",
            replay_gain_write=self.settings.data.metadata_replay_gain,
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
        try:
            if media_id and media_type:
                # If no media instance is provided, we need to create the media instance.
                # Throws `tidalapi.exceptions.ObjectNotFound` if item is not available anymore.
                media = instantiate_media(self.session, media_type, media_id)
            elif isinstance(media, Album):  # Check if media is available not deactivated / removed from TIDAL.
                if not media.available:
                    self.fn_logger.info(
                        f"This item is not available for listening anymore on TIDAL. Skipping: {name_builder_title(media)}"
                    )

                    return
            elif not media:
                raise MediaMissing
        except:
            return

        # Create file name and path
        file_name_relative: str = format_path_media(file_template, media)

        # Get the name of the list and check, if videos should be included.
        list_media_name: str = name_builder_title(media)
        list_media_name_short: str = list_media_name[:30]

        # Get all items of the list.
        items = items_results_all(media, videos_include=video_download)

        # Determine where to redirect the progress information.
        if self.progress_gui is None:
            progress_stdout: bool = True
        else:
            progress_stdout: bool = False
            self.progress_gui.list_name.emit(list_media_name_short)

        progress: Progress = self.progress_overall if self.progress_overall else self.progress

        # Create the list progress task.
        p_task1: TaskID = progress.add_task(
            f"[green]List '{list_media_name_short}'", total=len(items), visible=progress_stdout
        )

        is_album: bool = isinstance(media, Album)
        # TODO: Refactor strings to constants (also in cfg.py)
        sort_by_track_num: bool = bool("album_track_num" in file_name_relative or "list_pos" in file_name_relative)
        result_dirs: [pathlib.Path] = []
        list_total: int = len(items)

        # Iterate through list items
        while not progress.finished:
            with futures.ThreadPoolExecutor(max_workers=self.settings.data.downloads_concurrent_max) as executor:
                # Dispatch all download tasks to worker threads
                l_futures: [futures.Future] = [
                    executor.submit(
                        self.item,
                        media=item_media,
                        file_template=file_name_relative,
                        quality_audio=quality_audio,
                        quality_video=quality_video,
                        download_delay=download_delay,
                        is_parent_album=is_album,
                        list_position=count + 1,
                        list_total=list_total,
                    )
                    for count, item_media in enumerate(items)
                ]

                # Report results as they become available
                for future in futures.as_completed(l_futures):
                    # Retrieve result
                    status, result_path_file = future.result()

                    if result_path_file:
                        result_dirs.append(result_path_file.parent)

                    # Advance progress bar.
                    progress.advance(p_task1)

                    if not progress_stdout:
                        self.progress_gui.list_item.emit(progress.tasks[p_task1].percentage)

                    # If app is terminated (CTRL+C)
                    if self.event_abort.is_set():
                        # Cancel all not yet started tasks
                        for f in l_futures:
                            f.cancel()

                        # End method here.
                        return

        # Create playlist file
        if self.settings.data.playlist_create:
            self.playlist_populate(set(result_dirs), list_media_name, is_album, sort_by_track_num)

        self.fn_logger.info(f"Finished list '{list_media_name}'.")

    def playlist_populate(
        self, dirs_scoped: [pathlib.Path], name_list: str, is_album: bool, sort_alphabetically
    ) -> [pathlib.Path]:
        result: [pathlib.Path] = []

        # For each dir, which contains tracks
        for dir_scoped in dirs_scoped:
            # Sanitize final playlist name to fit into OS boundaries.
            path_playlist = dir_scoped / sanitize_filename(PLAYLIST_PREFIX + name_list + PLAYLIST_EXTENSION)
            path_playlist = pathlib.Path(path_file_sanitize(path_playlist, adapt=True))

            self.fn_logger.debug(f"Playlist: Creating {path_playlist}")

            # Get all tracks in the directory
            path_tracks: [pathlib.Path] = []

            for extension_audio in AudioExtensions:
                path_tracks = path_tracks + list(dir_scoped.glob(f"*{extension_audio!s}"))

            # Sort alphabetically, e.g. if items are prefixed with numbers
            if sort_alphabetically:
                path_tracks.sort()
            elif not is_album:
                # If it is not an album sort by modification time
                path_tracks.sort(key=lambda x: os.path.getmtime(x))

            # Write data to m3u file
            with path_playlist.open(mode="w", encoding="utf-8") as f:
                for path_track in path_tracks:
                    # If it's a symlink write the relative file path to the actual track into the playlist file
                    if path_track.is_symlink():
                        media_file_target = path_track.resolve().relative_to(path_track.parent, walk_up=True)
                    else:
                        media_file_target = path_track.name

                    f.write(str(media_file_target) + os.linesep)

            result.append(path_playlist)

        return result

    def _video_convert(self, path_file: pathlib.Path) -> pathlib.Path:
        path_file_out: pathlib.Path = path_file.with_suffix(AudioExtensions.MP4)
        ffmpeg = (
            FFmpeg(executable=self.settings.data.path_binary_ffmpeg)
            .option("y")
            .input(url=path_file)
            .output(url=path_file_out, codec="copy", map=0, loglevel="quiet")
        )

        ffmpeg.execute()

        return path_file_out

    def _extract_flac(self, path_media_src: pathlib.Path) -> pathlib.Path:
        path_media_out = path_media_src.with_suffix(AudioExtensions.FLAC)
        ffmpeg = (
            FFmpeg(executable=self.settings.data.path_binary_ffmpeg)
            .input(url=path_media_src)
            .output(
                url=path_media_out,
                map=0,
                movflags="use_metadata_tags",
                acodec="copy",
                map_metadata="0:g",
                loglevel="quiet",
            )
        )

        ffmpeg.execute()

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
