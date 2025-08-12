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
    """Format a string based on media attributes.

    Args:
        name (str): The format template name.
        media (Track | Album | Playlist | UserPlaylist | Video | Mix): The media object.
        album_track_num_pad_min (int): Minimum padding for track numbers. Defaults to 0.
        list_pos (int): Position in a list. Defaults to 0.
        list_total (int): Total items in a list. Defaults to 0.

    Returns:
        str: The formatted string.
    """
    try:
        # Try each formatter function in sequence
        for formatter in (
            _format_names,
            _format_numbers,
            _format_ids,
            _format_durations,
            _format_dates,
            _format_metadata,
            _format_volumes,
        ):
            result = formatter(name, media, album_track_num_pad_min, list_pos, list_total)
            if result is not None:
                return result
    except Exception as e:
        # TODO: Implement better exception logging.
        print(e)

    return name


def _format_artist_names(
    name: str,
    media: Track | Album | Playlist | UserPlaylist | Video | Mix,
    *_args,
) -> str | None:
    """Handle artist name-related format strings.

    Args:
        name (str): The format string name to check.
        media (Track | Album | Playlist | UserPlaylist | Video | Mix): The media object to extract artist information from.
        *_args (Any): Additional arguments (not used).

    Returns:
        str | None: The formatted artist name or None if the format string is not artist-related.
    """
    if name == "artist_name" and isinstance(media, Track | Video):
        if hasattr(media, "artists"):
            return name_builder_artist(media)
        elif hasattr(media, "artist"):
            return media.artist.name
    elif name == "album_artist":
        return name_builder_album_artist(media, first_only=True)
    elif name == "album_artists":
        return name_builder_album_artist(media)
    return None


def _format_titles(
    name: str,
    media: Track | Album | Playlist | UserPlaylist | Video | Mix,
    *_args,
) -> str | None:
    """Handle title-related format strings.

    Args:
        name (str): The format string name to check.
        media (Track | Album | Playlist | UserPlaylist | Video | Mix): The media object to extract title information from.
        *_args (Any): Additional arguments (not used).

    Returns:
        str | None: The formatted title or None if the format string is not title-related.
    """
    if name == "track_title" and isinstance(media, Track | Video):
        return name_builder_title(media)
    elif name == "mix_name" and isinstance(media, Mix):
        return media.title
    elif name == "playlist_name" and isinstance(media, Playlist | UserPlaylist):
        return media.name
    elif name == "album_title":
        if isinstance(media, Album):
            return media.name
        elif isinstance(media, Track):
            return media.album.name
    return None


def _format_names(
    name: str,
    media: Track | Album | Playlist | UserPlaylist | Video | Mix,
    *_args,
) -> str | None:
    """Handle name-related format strings.

    Args:
        name (str): The format string name to check.
        media (Track | Album | Playlist | UserPlaylist | Video | Mix): The media object to extract name information from.
        *_args (Any): Additional arguments (not used).

    Returns:
        str | None: The formatted name or None if the format string is not name-related.
    """
    # First try artist name formats
    result = _format_artist_names(name, media)
    if result is not None:
        return result

    # Then try title formats
    return _format_titles(name, media)


def _format_numbers(
    name: str,
    media: Track | Album | Playlist | UserPlaylist | Video | Mix,
    album_track_num_pad_min: int,
    list_pos: int,
    list_total: int,
    *_args,
) -> str | None:
    """Handle number-related format strings.

    Args:
        name (str): The format string name to check.
        media (Track | Album | Playlist | UserPlaylist | Video | Mix): The media object to extract number information from.
        album_track_num_pad_min (int): Minimum padding for track numbers.
        list_pos (int): Position in a list.
        list_total (int): Total items in a list.
        *_args (Any): Additional arguments (not used).

    Returns:
        str | None: The formatted number or None if the format string is not number-related.
    """
    if name == "album_track_num" and isinstance(media, Track | Video):
        return calculate_number_padding(
            album_track_num_pad_min,
            media.track_num,
            media.album.num_tracks if hasattr(media, "album") else 1,
        )
    elif name == "album_num_tracks" and isinstance(media, Track | Video):
        return str(media.album.num_tracks if hasattr(media, "album") else 1)
    elif name == "list_pos" and isinstance(media, Track | Video):
        # TODO: Rename `album_track_num_pad_min` globally.
        return calculate_number_padding(album_track_num_pad_min, list_pos, list_total)
    return None


def _format_ids(
    name: str,
    media: Track | Album | Playlist | UserPlaylist | Video | Mix,
    *_args,
) -> str | None:
    """Handle ID-related format strings.

    Args:
        name (str): The format string name to check.
        media (Track | Album | Playlist | UserPlaylist | Video | Mix): The media object to extract ID information from.
        *_args (Any): Additional arguments (not used).

    Returns:
        str | None: The formatted ID or None if the format string is not ID-related.
    """
    # Handle track and playlist IDs
    if (
        (name == "track_id" and isinstance(media, Track))
        or (name == "playlist_id" and isinstance(media, Playlist))
        or (name == "video_id" and isinstance(media, Video))
    ):
        return str(media.id)
    # Handle album IDs
    elif name == "album_id":
        if isinstance(media, Album):
            return str(media.id)
        elif isinstance(media, Track):
            return str(media.album.id)
    # Handle ISRC
    elif name == "isrc" and isinstance(media, Track):
        return media.isrc
    return None


def _format_durations(
    name: str,
    media: Track | Album | Playlist | UserPlaylist | Video | Mix,
    *_args,
) -> str | None:
    """Handle duration-related format strings.

    Args:
        name (str): The format string name to check.
        media (Track | Album | Playlist | UserPlaylist | Video | Mix): The media object to extract duration information from.
        *_args (Any): Additional arguments (not used).

    Returns:
        str | None: The formatted duration or None if the format string is not duration-related.
    """
    # Format track durations
    if name == "track_duration_seconds" and isinstance(media, Track | Video):
        return str(media.duration)
    elif name == "track_duration_minutes" and isinstance(media, Track | Video):
        m, s = divmod(media.duration, 60)
        return f"{m:01d}:{s:02d}"

    # Format album durations
    elif name == "album_duration_seconds" and isinstance(media, Album):
        return str(media.duration)
    elif name == "album_duration_minutes" and isinstance(media, Album):
        m, s = divmod(media.duration, 60)
        return f"{m:01d}:{s:02d}"

    # Format playlist durations
    elif name == "playlist_duration_seconds" and isinstance(media, Album):
        return str(media.duration)
    elif name == "playlist_duration_minutes" and isinstance(media, Album):
        m, s = divmod(media.duration, 60)
        return f"{m:01d}:{s:02d}"

    return None


def _format_dates(
    name: str,
    media: Track | Album | Playlist | UserPlaylist | Video | Mix,
    *_args,
) -> str | None:
    """Handle date-related format strings.

    Args:
        name (str): The format string name to check.
        media (Track | Album | Playlist | UserPlaylist | Video | Mix): The media object to extract date information from.
        *_args (Any): Additional arguments (not used).

    Returns:
        str | None: The formatted date or None if the format string is not date-related.
    """
    if name == "album_year":
        if isinstance(media, Album):
            return str(media.year)
        elif isinstance(media, Track):
            return str(media.album.year)
    elif name == "album_date":
        if isinstance(media, Album):
            return media.release_date.strftime("%Y-%m-%d") if media.release_date else None
        elif isinstance(media, Track):
            return media.album.release_date.strftime("%Y-%m-%d") if media.album.release_date else None

    return None


def _format_metadata(
    name: str,
    media: Track | Album | Playlist | UserPlaylist | Video | Mix,
    *_args,
) -> str | None:
    """Handle metadata-related format strings.

    Args:
        name (str): The format string name to check.
        media (Track | Album | Playlist | UserPlaylist | Video | Mix): The media object to extract metadata information from.
        *_args (Any): Additional arguments (not used).

    Returns:
        str | None: The formatted metadata or None if the format string is not metadata-related.
    """
    if name == "video_quality" and isinstance(media, Video):
        return media.video_quality
    elif name == "track_quality" and isinstance(media, Track):
        return ", ".join(tag for tag in media.media_metadata_tags if tag is not None)
    elif (name == "track_explicit" and isinstance(media, Track | Video)) or (
        name == "album_explicit" and isinstance(media, Album)
    ):
        return FORMAT_TEMPLATE_EXPLICIT if media.explicit else ""
    return None


def _format_volumes(
    name: str,
    media: Track | Album | Playlist | UserPlaylist | Video | Mix,
    *_args,
) -> str | None:
    """Handle volume-related format strings.

    Args:
        name (str): The format string name to check.
        media (Track | Album | Playlist | UserPlaylist | Video | Mix): The media object to extract volume information from.
        *_args (Any): Additional arguments (not used).

    Returns:
        str | None: The formatted volume information or None if the format string is not volume-related.
    """
    if name == "album_num_volumes" and isinstance(media, Album):
        return str(media.num_volumes)
    elif name == "track_volume_num" and isinstance(media, Track | Video):
        return str(media.volume_num)
    elif name == "track_volume_num_optional" and isinstance(media, Track | Video):
        num_volumes: int = media.album.num_volumes if hasattr(media, "album") else 1
        return "" if num_volumes == 1 else str(media.volume_num)
    elif name == "track_volume_num_optional_CD" and isinstance(media, Track | Video):
        num_volumes: int = media.album.num_volumes if hasattr(media, "album") else 1
        return "" if num_volumes == 1 else f"CD{media.volume_num!s}"
    return None


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


def file_unique_suffix(path_file: pathlib.Path, separator: str = "_") -> str:
    """Generate a unique suffix for a file path.

    Args:
        path_file (pathlib.Path): The file path to check for uniqueness.
        separator (str, optional): The separator to use for the suffix. Defaults to "_".

    Returns:
        str: The unique suffix, or an empty string if not needed.
    """
    threshold_zfill: int = len(str(UNIQUIFY_THRESHOLD))
    count: int = 0
    path_file_tmp: pathlib.Path = deepcopy(path_file)
    unique_suffix: str = ""

    while check_file_exists(path_file_tmp) and count < UNIQUIFY_THRESHOLD:
        count += 1
        unique_suffix = separator + str(count).zfill(threshold_zfill)
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
        path_files: list[str] = []

        path_files.extend(str(path_parent.joinpath(path_file_stem + extension)) for extension in AudioExtensions)
    else:
        path_files: list[str] = [str(path_file)]

    return any(os.path.isfile(_file) for _file in path_files)


def resource_path(relative_path: str) -> str:
    """Get the absolute path to a resource.

    Args:
        relative_path: The relative path to the resource.

    Returns:
        str: The absolute path to the resource.
    """
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))

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
