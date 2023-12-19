import os
import pathlib
import platform
import re
from collections.abc import Callable
from pathlib import Path

from pathvalidate import sanitize_filename
from tidalapi import Album, Playlist, Track, UserPlaylist, Video, Mix


def path_base():
    if "XDG_CONFIG_HOME" in os.environ:
        return os.environ["XDG_CONFIG_HOME"]
    elif "HOME" in os.environ:
        return os.environ["HOME"]
    elif "HOMEDRIVE" in os.environ and "HOMEPATH" in os.environ:
        return os.path.join(os.environ["HOMEDRIVE"], os.environ["HOMEPATH"])
    else:
        return os.path.abspath("./")


def path_file_log():
    return os.path.join(path_base(), ".tidal-dl-ng.log")


def path_file_token():
    return os.path.join(path_base(), ".tidal-dl-ng_token.json")


def path_file_settings():
    return os.path.join(path_base(), ".tidal-dl-ng_settings.json")


def format_path_media(fmt_template: str, media: Track | Album | Playlist | UserPlaylist | Video | Mix) -> str:
    result = fmt_template

    # Search track format template for placeholder.
    regex = r"\{(.+?)\}"
    matches = re.finditer(regex, fmt_template, re.MULTILINE)
    fn_format = get_fn_format(media)

    for _matchNum, match in enumerate(matches, start=1):
        template_str = match.group()
        result_fmt = fn_format(match.group(1), media)

        if result_fmt:
            value = sanitize_filename(result_fmt)
            result = result.replace(template_str, value)

    return result


def format_str_track(name: str, media: Track) -> str | bool:
    result: str | bool = False

    if name == "track_num":
        result = str(media.track_num).rjust(2, "0")
    elif name == "artist_name":
        result = ", ".join(artist.name for artist in media.artists)
    elif name == "track_title":
        result = media.name

    return result


def format_str_album(name: str, media: Album) -> str | bool:
    result: str | bool = False

    if name == "album_title":
        result = media.name
    elif name == "artist_name":
        result = media.artist.name

    return result


def format_str_playlist(name: str, media: Playlist) -> str | bool:
    result: str | bool = False

    if name == "playlist_name":
        result = media.name

    return result


def format_str_mix(name: str, media: Mix) -> str | bool:
    result: str | bool = False

    if name == "mix_name":
        result = media.title

    return result


def format_str_video(name: str, media: Video) -> str | bool:
    result: str | bool = False

    if name == "artist_name":
        result = ", ".join(artist.name for artist in media.artists)
    elif name == "track_title":
        result = media.name

    return result


def get_fn_format(media: Track | Album | Playlist | UserPlaylist | Video | Mix) -> Callable:
    result = None

    if isinstance(media, Track):
        result = format_str_track
    elif isinstance(media, Album):
        result = format_str_album
    elif isinstance(media, (Playlist, UserPlaylist)):
        result = format_str_playlist
    elif isinstance(media, Mix):
        result = format_str_mix
    elif isinstance(media, Video):
        result = format_str_video

    return result


def length_max_name_file() -> int:
    system = platform.system()
    result: int = 255

    try:
        if system in ['Darwin', 'Linux']:
            result: int = os.pathconf('/', 'PC_NAME_MAX')
    except Exception as e:
        pass

    return result


def length_max_name_path() -> int:
    system = platform.system()
    result: int = 255

    try:
        if system in ['Darwin', 'Linux']:
            result: int = os.pathconf('/', 'PC_PATH_MAX')
    except Exception as e:
        pass

    return result


def path_validate(path_file: str, adapt: bool = False) -> (bool, str):
    result: bool = False
    length_max_path: int = length_max_name_path()
    length_max_file: int = length_max_name_file()
    path, file = os.path.split(path_file)
    filename, extension = os.path.splitext(file)

    if len(path) >= length_max_path:
        result = False

        if adapt:
            path = Path.home()

    if len(file) >= length_max_file:
        result = False

        if adapt:
            file = f'{filename[:length_max_file - len(extension + "_")]}_{extension}'

    path_file = os.path.join(path, file)

    return result, path_file


def check_file_exists(path_file: str):
    result = pathlib.Path(path_file).is_file()

    return result
