import math
import os
import pathlib
import posixpath
import re
import sys
from copy import deepcopy
from urllib.parse import unquote, urlsplit

from pathvalidate import sanitize_filename, sanitize_filepath
from pathvalidate.error import ValidationError
from tidalapi import Album, Mix, Playlist, Track, UserPlaylist, Video
from tidalapi.media import AudioExtensions

from tidal_dl_ng import __name_display__
from tidal_dl_ng.constants import FILENAME_LENGTH_MAX, FILENAME_SANITIZE_PLACEHOLDER, UNIQUIFY_THRESHOLD, MediaType
from tidal_dl_ng.helper.tidal import name_builder_album_artist, name_builder_artist, name_builder_title


def path_home() -> str:
    if "XDG_CONFIG_HOME" in os.environ:
        return os.environ["XDG_CONFIG_HOME"]
    elif "HOME" in os.environ:
        return os.environ["HOME"]
    elif "HOMEDRIVE" in os.environ and "HOMEPATH" in os.environ:
        return os.path.join(os.environ["HOMEDRIVE"], os.environ["HOMEPATH"])
    else:
        return os.path.abspath("./")


def path_config_base() -> str:
    # https://wiki.archlinux.org/title/XDG_Base_Directory
    # X11 workaround: If user specified config path is set, do not point to "~/.config"
    path_user_custom: str = os.environ.get("XDG_CONFIG_HOME", "")
    path_config: str = ".config" if not path_user_custom else ""
    path_base: str = os.path.join(path_home(), path_config, __name_display__)

    return path_base


def path_file_log() -> str:
    return os.path.join(path_config_base(), "app.log")


def path_file_token() -> str:
    return os.path.join(path_config_base(), "token.json")


def path_file_settings() -> str:
    return os.path.join(path_config_base(), "settings.json")


def format_path_media(
    fmt_template: str, media: Track | Album | Playlist | UserPlaylist | Video | Mix, album_track_num_pad_min: int = 0
) -> str:
    result = fmt_template

    # Search track format template for placeholder.
    regex = r"\{(.+?)\}"
    matches = re.finditer(regex, fmt_template, re.MULTILINE)

    for _matchNum, match in enumerate(matches, start=1):
        template_str = match.group()
        result_fmt = format_str_media(match.group(1), media, album_track_num_pad_min)

        if result_fmt != match.group(1):
            value = sanitize_filename(result_fmt)
            result = result.replace(template_str, value)

    return result


def format_str_media(
    name: str, media: Track | Album | Playlist | UserPlaylist | Video | Mix, album_track_num_pad_min: int = 0
) -> str:
    result: str = name

    try:
        match name:
            case "artist_name":
                if isinstance(media, Track | Video):
                    if hasattr(media, "artists"):
                        result = name_builder_artist(media)
                    elif hasattr(media, "artist"):
                        result = media.artist.name
            case "album_artist":
                result = name_builder_album_artist(media)
            case "track_title":
                if isinstance(media, Track | Video):
                    result = name_builder_title(media)
            case "mix_name":
                if isinstance(media, Mix):
                    result = media.title
            case "playlist_name":
                if isinstance(media, Playlist | UserPlaylist):
                    result = media.name
            case "album_title":
                if isinstance(media, Album):
                    result = media.name
                elif isinstance(media, Track):
                    result = media.album.name
            case "album_track_num":
                if isinstance(media, Track | Video):
                    num_tracks: int = media.album.num_tracks if hasattr(media, "album") else 1
                    count_digits: int = int(math.log10(num_tracks)) + 1
                    count_digits_computed: int = (
                        count_digits if count_digits > album_track_num_pad_min else album_track_num_pad_min
                    )
                    result = str(media.track_num).zfill(count_digits_computed)
            case "album_num_tracks":
                if isinstance(media, Track | Video):
                    result = str(media.album.num_tracks if hasattr(media, "album") else 1)
            case "track_id":
                if isinstance(media, Track | Video):
                    result = str(media.id)
            case "playlist_id":
                if isinstance(media, Playlist):
                    result = str(media.id)
            case "album_id":
                if isinstance(media, Album):
                    result = str(media.id)
                elif isinstance(media, Track):
                    result = str(media.album.id)
            case "track_duration_seconds":
                if isinstance(media, Track | Video):
                    result = str(media.duration)
            case "track_duration_minutes":
                if isinstance(media, Track | Video):
                    m, s = divmod(media.duration, 60)
                    result = f"{m:01d}:{s:02d}"
            case "album_duration_seconds":
                if isinstance(media, Album):
                    result = str(media.duration)
            case "album_duration_minutes":
                if isinstance(media, Album):
                    m, s = divmod(media.duration, 60)
                    result = f"{m:01d}:{s:02d}"
            case "playlist_duration_seconds":
                if isinstance(media, Album):
                    result = str(media.duration)
            case "playlist_duration_minutes":
                if isinstance(media, Album):
                    m, s = divmod(media.duration, 60)
                    result = f"{m:01d}:{s:02d}"
            case "album_year":
                if isinstance(media, Album):
                    result = str(media.year)
                elif isinstance(media, Track):
                    result = str(media.album.year)
            case "video_quality":
                if isinstance(media, Video):
                    result = media.video_quality
            case "track_quality":
                if isinstance(media, Track):
                    result = ", ".join(tag for tag in media.media_metadata_tags)
            case "track_explicit":
                if isinstance(media, Track | Video):
                    result = " (Explicit)" if media.explicit else ""
            case "album_explicit":
                if isinstance(media, Album):
                    result = " (Explicit)" if media.explicit else ""
            case "album_num_volumes":
                if isinstance(media, Album):
                    result = str(media.num_volumes)
            case "track_volume_num":
                if isinstance(media, Track | Video):
                    result = str(media.volume_num)
            case "track_volume_num_optional":
                if isinstance(media, Track | Video):
                    num_volumes: int = media.album.num_volumes if hasattr(media, "album") else 1
                    result = "" if num_volumes == 1 else str(media.volume_num)
            case "track_volume_num_optional_CD":
                if isinstance(media, Track | Video):
                    num_volumes: int = media.album.num_volumes if hasattr(media, "album") else 1
                    result = "" if num_volumes == 1 else f"CD{media.volume_num!s}"
            case "isrc":
                if isinstance(media, Track):
                    result = media.isrc
    except Exception as e:
        # TODO: Implement better exception logging.
        print(e)

        pass

    return result


def get_format_template(
    media: Track | Album | Playlist | UserPlaylist | Video | Mix | MediaType, settings
) -> str | bool:
    result = False

    if isinstance(media, Track) or media == MediaType.TRACK:
        result = settings.data.format_track
    elif isinstance(media, Album) or media == MediaType.ALBUM or media == MediaType.ARTIST:
        result = settings.data.format_album
    elif isinstance(media, Playlist | UserPlaylist) or media == MediaType.PLAYLIST:
        result = settings.data.format_playlist
    elif isinstance(media, Mix) or media == MediaType.MIX:
        result = settings.data.format_mix
    elif isinstance(media, Video) or media == MediaType.VIDEO:
        result = settings.data.format_video

    return result


def path_file_sanitize(path_file: pathlib.Path, adapt: bool = False, uniquify: bool = False) -> pathlib.Path:
    # Get each directory name separately (first value in tuple; second value is for the file suffix).
    to_sanitize: [[str, str]] = path_split_parts_suffix(path_file)
    sanitized_path_file: pathlib.Path = pathlib.Path(to_sanitize.pop(0)[0])

    for name, suffix in to_sanitize:
        # Sanitize names: We need first top make sure that none file / directory name has bad chars or is longer than 255 chars.
        try:
            # sanitize_filename can shorten the file name actually
            filename_sanitized: str = sanitize_filename(
                name + suffix, replacement_text=" ", validate_after_sanitize=True, platform="auto"
            )

            # Check if the file extension was removed by shortening the filename length
            if not filename_sanitized.endswith(suffix):
                # Add the original file extension
                file_suffix: str = FILENAME_SANITIZE_PLACEHOLDER + path_file.suffix
                filename_sanitized = filename_sanitized[: -len(file_suffix)] + file_suffix
        except ValidationError as e:
            if adapt:
                # TODO: Implement proper exception handling and logging.
                # Hacky stuff, since the sanitizing function does not shorten the filename (filename too long)
                if str(e).startswith("[PV1101]"):
                    byte_ct: int = len(name.encode(sys.getfilesystemencoding())) - FILENAME_LENGTH_MAX
                    filename_sanitized = (
                        name[: -byte_ct - len(FILENAME_SANITIZE_PLACEHOLDER) - len(suffix)]
                        + FILENAME_SANITIZE_PLACEHOLDER
                        + suffix
                    )
                else:
                    raise
            else:
                raise
        finally:
            sanitized_path_file = sanitized_path_file / filename_sanitized

    # Sanitize the whole path. The whole path with filename is not allowed to be longer then the max path length depending on the OS.
    try:
        sanitized_path_file: pathlib.Path = sanitize_filepath(
            sanitized_path_file, replacement_text=" ", validate_after_sanitize=True, platform="auto"
        )
    except ValidationError as e:
        # If adaption of path is allowed in case of an error set path to HOME.
        if adapt:
            if str(e).startswith("[PV1101]"):
                sanitized_path_file = pathlib.Path.home() / sanitized_path_file.name
            else:
                raise
        else:
            raise

    # Uniquify
    if uniquify:
        sanitized_path_file = path_file_uniquify(sanitized_path_file)

    return sanitized_path_file


def path_file_uniquify(path_file: pathlib.Path) -> pathlib.Path:
    """Checks whether the file exists, if so it tries to return an unique name suffix.

    :param path_file: Path to file name which shall be unique.
    :type path_file: pathlib.Path
    :return: Unique file name with path for given input.
    :rtype: pathlib.Path
    """
    unique_suffix: str = file_unique_suffix(path_file)

    if unique_suffix:
        file_suffix = unique_suffix + path_file.suffix
        # For most OS filename has a character limit of 255.
        path_file = (
            path_file.parent / (str(path_file.stem)[: -len(file_suffix)] + file_suffix)
            if len(str(path_file.parent / (path_file.stem + unique_suffix))) > FILENAME_LENGTH_MAX
            else path_file.parent / (path_file.stem + unique_suffix)
        )

    return path_file


def file_unique_suffix(path_file: pathlib.Path, seperator: str = "_") -> str:
    threshold_zfill: int = len(str(UNIQUIFY_THRESHOLD))
    count: int = 0
    path_file_tmp: pathlib.Path = deepcopy(path_file)
    unique_suffix: str = ""

    while check_file_exists(path_file_tmp) and count < UNIQUIFY_THRESHOLD:
        count += 1
        unique_suffix = seperator + str(count).zfill(threshold_zfill)
        path_file_tmp = path_file.parent / (path_file.stem + unique_suffix + path_file.suffix)

    return unique_suffix


def check_file_exists(path_file: pathlib.Path, extension_ignore: bool = False) -> bool:
    if extension_ignore:
        path_file_stem: str = pathlib.Path(path_file).stem
        path_parent: pathlib.Path = pathlib.Path(path_file).parent
        path_files: [str] = []

        for extension in AudioExtensions:
            path_files.append(str(path_parent.joinpath(path_file_stem + extension)))
    else:
        path_files: [str] = [path_file]

    result = bool(sum([[True] if os.path.isfile(_file) else [] for _file in path_files], []))

    return result


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def url_to_filename(url: str) -> str:
    """Return basename corresponding to url.
    >>> print(url_to_filename('http://example.com/path/to/file%C3%80?opt=1'))
    fileÀ
    >>> print(url_to_filename('http://example.com/slash%2fname')) # '/' in name
    Taken from https://gist.github.com/zed/c2168b9c52b032b5fb7d
    Traceback (most recent call last):
    ...
    ValueError
    """
    urlpath: str = urlsplit(url).path
    basename: str = posixpath.basename(unquote(urlpath))

    if os.path.basename(basename) != basename or unquote(posixpath.basename(urlpath)) != basename:
        raise ValueError  # reject '%2f' or 'dir%5Cbasename.ext' on Windows

    return basename


def path_split_parts_suffix(p: pathlib.Path) -> [[str, str]]:
    """Splits the path to file in parts and also splits the suffix from the file stem.

    :param p: Path to file which should be split in parts.
    :type p: pathlib.Path
    :return: List of tuples (Stem, Suffix) of each path part.
    """
    result: [[str, str]] = [[part, ""] for part in p.parts]
    result[-1][0] = p.stem
    result[-1][-1] = p.suffix

    return result
