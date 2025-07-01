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
from tidal_dl_ng.constants import (
    FILENAME_LENGTH_MAX,
    FILENAME_SANITIZE_PLACEHOLDER,
    FORMAT_TEMPLATE_EXPLICIT,
    UNIQUIFY_THRESHOLD,
    MediaType,
)
from tidal_dl_ng.helper.tidal import name_builder_album_artist, name_builder_artist, name_builder_title


def path_home() -> str:
    """Get the home directory path.

    Returns:
        str: The home directory path.
    """
    if "XDG_CONFIG_HOME" in os.environ:
        return os.environ["XDG_CONFIG_HOME"]
    elif "HOME" in os.environ:
        return os.environ["HOME"]
    elif "HOMEDRIVE" in os.environ and "HOMEPATH" in os.environ:
        return os.path.join(os.environ["HOMEDRIVE"], os.environ["HOMEPATH"])
    else:
        return os.path.abspath("./")


def path_config_base() -> str:
    """Get the base configuration path.

    Returns:
        str: The base configuration path.
    """
    # https://wiki.archlinux.org/title/XDG_Base_Directory
    # X11 workaround: If user specified config path is set, do not point to "~/.config"
    path_user_custom: str = os.environ.get("XDG_CONFIG_HOME", "")
    path_config: str = ".config" if not path_user_custom else ""
    path_base: str = os.path.join(path_home(), path_config, __name_display__)

    return path_base


def path_file_log() -> str:
    """Get the path to the log file.

    Returns:
        str: The log file path.
    """
    return os.path.join(path_config_base(), "app.log")


def path_file_token() -> str:
    """Get the path to the token file.

    Returns:
        str: The token file path.
    """
    return os.path.join(path_config_base(), "token.json")


def path_file_settings() -> str:
    """Get the path to the settings file.

    Returns:
        str: The settings file path.
    """
    return os.path.join(path_config_base(), "settings.json")


def format_path_media(
    fmt_template: str,
    media: Track | Album | Playlist | UserPlaylist | Video | Mix,
    album_track_num_pad_min: int = 0,
    list_pos: int = 0,
    list_total: int = 0,
) -> str:
    result = fmt_template

    # Search track format template for placeholder.
    regex = r"\{(.+?)\}"
    matches = re.finditer(regex, fmt_template, re.MULTILINE)

    for _matchNum, match in enumerate(matches, start=1):
        template_str = match.group()
        result_fmt = format_str_media(match.group(1), media, album_track_num_pad_min, list_pos, list_total)

        if result_fmt != match.group(1):
            # Sanitize here, in case of the filename has slashes or something, which will be recognized later as a directory separator.
            # Do not sanitize if value is the FORMAT_TEMPLATE_EXPLICIT placeholder, since it has a leading whitespace which otherwise gets removed.
            value = (
                sanitize_filename(result_fmt) if result_fmt != FORMAT_TEMPLATE_EXPLICIT else FORMAT_TEMPLATE_EXPLICIT
            )
            result = result.replace(template_str, value)

    return result


def format_str_media(
    name: str,
    media: Track | Album | Playlist | UserPlaylist | Video | Mix,
    album_track_num_pad_min: int = 0,
    list_pos: int = 0,
    list_total: int = 0,
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
                result = name_builder_album_artist(media, first_only=True)
            case "album_artists":
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
                    result = calculate_number_padding(
                        album_track_num_pad_min,
                        media.track_num,
                        media.album.num_tracks if hasattr(media, "album") else 1,
                    )
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
                    result = ", ".join(tag for tag in media.media_metadata_tags if tag is not None)
            case "track_explicit":
                if isinstance(media, Track | Video):
                    result = FORMAT_TEMPLATE_EXPLICIT if media.explicit else ""
            case "album_explicit":
                if isinstance(media, Album):
                    result = FORMAT_TEMPLATE_EXPLICIT if media.explicit else ""
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
            case "list_pos":
                if isinstance(media, Track | Video):
                    # TODO: Rename `album_track_num_pad_min` globally.
                    result = calculate_number_padding(album_track_num_pad_min, list_pos, list_total)
    except Exception as e:
        # TODO: Implement better exception logging.
        print(e)

    return result


def calculate_number_padding(padding_minimum: int, item_position: int, items_max: int) -> str:
    """Calculate the padded number string for an item.

    Args:
        padding_minimum (int): Minimum number of digits for padding.
        item_position (int): The position of the item.
        items_max (int): The maximum number of items.

    Returns:
        str: The padded number string.
    """
    result: str

    if items_max > 0:
        count_digits = max(int(math.log10(items_max)) + 1, padding_minimum)
        result = str(item_position).zfill(count_digits)
    else:
        result = str(item_position)

    return result


def get_format_template(
    media: Track | Album | Playlist | UserPlaylist | Video | Mix | MediaType, settings
) -> str | bool:
    """Get the format template for a given media type.

    Args:
        media (Track | Album | Playlist | UserPlaylist | Video | Mix | MediaType): The media object or type.
        settings: The settings object containing format templates.

    Returns:
        str | bool: The format template string or False if not found.
    """
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
    """Sanitize a file path to ensure it is valid and optionally make it unique.

    Args:
        path_file (pathlib.Path): The file path to sanitize.
        adapt (bool, optional): Whether to adapt the path in case of errors. Defaults to False.
        uniquify (bool, optional): Whether to make the file name unique. Defaults to False.

    Returns:
        pathlib.Path: The sanitized file path.
    """
    sanitized_filename = sanitize_filename(
        path_file.name, replacement_text="_", validate_after_sanitize=True, platform="auto"
    )

    if not sanitized_filename.endswith(path_file.suffix):
        sanitized_filename = (
            sanitized_filename[: -len(path_file.suffix)] + FILENAME_SANITIZE_PLACEHOLDER + path_file.suffix
        )

    sanitized_path = pathlib.Path(
        *[
            (
                sanitize_filename(part, replacement_text="_", validate_after_sanitize=True, platform="auto")
                if part not in path_file.anchor
                else part
            )
            for part in path_file.parent.parts
        ]
    )

    try:
        sanitized_path = sanitize_filepath(
            sanitized_path, replacement_text="_", validate_after_sanitize=True, platform="auto"
        )
    except ValidationError as e:
        if adapt and str(e).startswith("[PV1101]"):
            sanitized_path = pathlib.Path.home()
        else:
            raise

    result = sanitized_path / sanitized_filename

    return path_file_uniquify(result) if uniquify else result


def path_file_uniquify(path_file: pathlib.Path) -> pathlib.Path:
    """Ensure a file path is unique by appending a suffix if necessary.

    Args:
        path_file (pathlib.Path): The file path to uniquify.

    Returns:
        pathlib.Path: The unique file path.
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
    """Generate a unique suffix for a file path.

    Args:
        path_file (pathlib.Path): The file path to check for uniqueness.
        seperator (str, optional): The separator to use for the suffix. Defaults to "_".

    Returns:
        str: The unique suffix, or an empty string if not needed.
    """
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
    """Check if a file exists.

    Args:
        path_file (pathlib.Path): The file path to check.
        extension_ignore (bool, optional): Whether to ignore the file extension. Defaults to False.

    Returns:
        bool: True if the file exists, False otherwise.
    """
    if extension_ignore:
        path_file_stem: str = pathlib.Path(path_file).stem
        path_parent: pathlib.Path = pathlib.Path(path_file).parent
        path_files: [str] = []

        for extension in AudioExtensions:
            path_files.append(str(path_parent.joinpath(path_file_stem + extension)))
    else:
        path_files: [str] = [path_file]

    result = any(os.path.isfile(_file) for _file in path_files)

    return result


def resource_path(relative_path):
    """Get the absolute path to a resource.

    Args:
        relative_path (str): The relative path to the resource.

    Returns:
        str: The absolute path to the resource.
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def url_to_filename(url: str) -> str:
    """Convert a URL to a valid filename.

    Args:
        url (str): The URL to convert.

    Returns:
        str: The corresponding filename.

    Raises:
        ValueError: If the URL contains invalid characters for a filename.
    """
    urlpath: str = urlsplit(url).path
    basename: str = posixpath.basename(unquote(urlpath))

    if os.path.basename(basename) != basename or unquote(posixpath.basename(urlpath)) != basename:
        raise ValueError  # reject '%2f' or 'dir%5Cbasename.ext' on Windows

    return basename
