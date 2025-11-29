import contextlib
import os
from collections.abc import Callable

import requests
from tidalapi import Album, Mix, Playlist, Session, Track, UserPlaylist, Video
from tidalapi.artist import Artist, Role
from tidalapi.media import MediaMetadataTags, Quality
from tidalapi.session import SearchTypes
from tidalapi.user import LoggedInUser

from tidal_dl_ng.constants import FAVORITES, MediaType
from tidal_dl_ng.helper.exceptions import MediaUnknown


def name_builder_artist(media: Track | Video | Album, delimiter: str = ", ") -> str:
    """Builds a string of artist names for a track, video, or album.

    Returns a delimited string of all artist names associated with the given media.

    Args:
        media (Track | Video | Album): The media object to extract artist names from.
        delimiter (str, optional): The delimiter to use between artist names. Defaults to ", ".

    Returns:
        str: A delimited string of artist names.
    """
    return delimiter.join(artist.name for artist in media.artists)


def name_builder_album_artist(media: Track | Album, first_only: bool = False, delimiter: str = ", ") -> str:
    """Builds a string of main album artist names for a track or album.

    Returns a delimited string of main artist names from the album, optionally including only the first main artist.

    Args:
        media (Track | Album): The media object to extract artist names from.
        first_only (bool, optional): If True, only the first main artist is included. Defaults to False.
        delimiter (str, optional): The delimiter to use between artist names. Defaults to ", ".

    Returns:
        str: A delimited string of main album artist names.
    """
    artists_tmp: [str] = []
    artists: [Artist] = media.album.artists if isinstance(media, Track) else media.artists

    for artist in artists:
        if Role.main in artist.roles:
            artists_tmp.append(artist.name)

            if first_only:
                break

    return delimiter.join(artists_tmp)


def name_builder_title(media: Track | Video | Mix | Playlist | Album | Video) -> str:
    result: str = (
        media.title if isinstance(media, Mix) else media.full_name if hasattr(media, "full_name") else media.name
    )

    return result


def name_builder_item(media: Track | Video) -> str:
    return f"{name_builder_artist(media)} - {name_builder_title(media)}"


def get_tidal_media_id(url_or_id_media: str) -> str:

    id_dirty = url_or_id_media.rsplit("/", 1)[-1]
    id_media = id_dirty.rsplit("?", 1)[0]

    return id_media


def get_tidal_media_type(url_media: str) -> MediaType | bool:
    result: MediaType | bool = False
    url_split = url_media.split("/")[-2]

    if len(url_split) > 1:
        media_name = url_media.split("/")[-2]

        if media_name == "track":
            result = MediaType.TRACK
        elif media_name == "video":
            result = MediaType.VIDEO
        elif media_name == "album":
            result = MediaType.ALBUM
        elif media_name == "playlist":
            result = MediaType.PLAYLIST
        elif media_name == "mix":
            result = MediaType.MIX
        elif media_name == "artist":
            result = MediaType.ARTIST

    return result


def url_ending_clean(url: str) -> str:
    """Checks if a link ends with "/u" or "?u" and removes that part.

    Args:
        url (str): The URL to clean.

    Returns:
        str: The cleaned URL.
    """
    return url[:-2] if url.endswith("/u") or url.endswith("?u") else url


def search_results_all(session: Session, needle: str, types_media: SearchTypes = None) -> dict[str, [SearchTypes]]:
    limit: int = 300
    offset: int = 0
    done: bool = False
    result: dict[str, [SearchTypes]] = {}

    while not done:
        tmp_result: dict[str, [SearchTypes]] = session.search(
            query=needle, models=types_media, limit=limit, offset=offset
        )
        tmp_done: bool = True

        for key, value in tmp_result.items():
            # Append pagination results, if there are any
            if offset == 0:
                result = tmp_result
                tmp_done = False
            elif bool(value):
                result[key] += value
                tmp_done = False

        # Next page
        offset += limit
        done = tmp_done

    return result


def items_results_all(
    session: Session, media_list: [Mix | Playlist | Album | Artist], videos_include: bool = True
) -> [Track | Video | Album]:
    result: [Track | Video | Album] = []

    if isinstance(media_list, Mix):
        result = media_list.items()
    else:
        func_get_items_media: [Callable] = []

        if isinstance(media_list, Playlist | Album):
            if videos_include:
                func_get_items_media.append(media_list.items)
            else:
                func_get_items_media.append(media_list.tracks)
        elif isinstance(media_list, Artist):
            func_get_items_media.append(media_list.get_albums)
            func_get_items_media.append(media_list.get_ep_singles)

        result = paginate_results(func_get_items_media)

    return result


def all_artist_album_ids(media_artist: Artist) -> [int | None]:
    result: [int] = []
    func_get_items_media: [Callable] = [media_artist.get_albums, media_artist.get_ep_singles]
    albums: [Album] = paginate_results(func_get_items_media)

    for album in albums:
        result.append(album.id)

    return result


def paginate_results(func_get_items_media: [Callable]) -> [Track | Video | Album | Playlist | UserPlaylist]:
    result: [Track | Video | Album] = []

    for func_media in func_get_items_media:
        limit: int = 100
        offset: int = 0
        done: bool = False

        if func_media.__func__ == LoggedInUser.playlist_and_favorite_playlists:
            limit: int = 50

        while not done:
            tmp_result: [Track | Video | Album | Playlist | UserPlaylist] = func_media(limit=limit, offset=offset)

            if bool(tmp_result):
                result += tmp_result
                # Get the next page in the next iteration.
                offset += limit
            else:
                done = True

    return result


def user_media_lists(session: Session) -> dict[str, list]:
    """Fetch user media lists using tidalapi's built-in pagination where available.

    Returns a dictionary with 'playlists' and 'mixes' keys containing lists of media items.
    For playlists, includes both Folder and Playlist objects at the root level.

    Args:
        session (Session): TIDAL session object.

    Returns:
        dict[str, list]: Dictionary with 'playlists' (includes Folder and Playlist) and 'mixes' lists.
    """
    # Use built-in pagination for playlists (root level only)
    playlists = session.user.favorites.playlists_paginated()

    # Fetch root-level folders manually (no paginated version available)
    folders = []
    offset = 0
    limit = 50

    while True:
        batch = session.user.favorites.playlist_folders(limit=limit, offset=offset, parent_folder_id="root")
        if not batch:
            break
        folders.extend(batch)
        if len(batch) < limit:
            break
        offset += limit

    # Combine folders and playlists
    all_playlists = folders + playlists

    # Get mixes
    user_mixes = session.mixes().categories[0].items

    return {"playlists": all_playlists, "mixes": user_mixes}


def instantiate_media(
    session: Session,
    media_type: type[MediaType.TRACK, MediaType.VIDEO, MediaType.ALBUM, MediaType.PLAYLIST, MediaType.MIX],
    id_media: str,
) -> Track | Video | Album | Playlist | Mix | Artist:
    if media_type == MediaType.TRACK:
        media = session.track(id_media, with_album=True)
    elif media_type == MediaType.VIDEO:
        media = session.video(id_media)
    elif media_type == MediaType.ALBUM:
        media = session.album(id_media)
    elif media_type == MediaType.PLAYLIST:
        media = session.playlist(id_media)
    elif media_type == MediaType.MIX:
        media = session.mix(id_media)
    elif media_type == MediaType.ARTIST:
        media = session.artist(id_media)
    else:
        raise MediaUnknown

    return media


def quality_audio_highest(media: Track | Album) -> Quality:
    quality: Quality

    # media_metadata_tags may be missing (Mock objects) or None; use safe getter
    tags = getattr(media, "media_metadata_tags", None)
    try:
        iterable_tags = set(tags) if tags is not None else set()
    except Exception:
        # If tags is a Mock or non-iterable, fall back to empty set
        iterable_tags = set()

    if MediaMetadataTags.hi_res_lossless in iterable_tags:
        quality = Quality.hi_res_lossless
    elif MediaMetadataTags.lossless in iterable_tags:
        quality = Quality.high_lossless
    else:
        quality = getattr(media, "audio_quality", Quality.low_320k)

    return quality


def favorite_function_factory(tidal, favorite_item: str):
    function_name: str = FAVORITES[favorite_item]["function_name"]
    function_list: Callable = getattr(tidal.session.user.favorites, function_name)

    return function_list


def fetch_raw_media_json(
    session: Session, media_type: str, media_id: str, country_code: str | None = None, extra_params: dict | None = None
) -> dict | None:
    """Fetch raw JSON for a media resource using tidalapi's session.request.

    Args:
        session (Session): the tidalapi Session
        media_type (str): 'tracks' or 'albums'
        media_id (str): id of media
        country_code (str | None): optional countryCode param

    Returns:
        dict | None: parsed JSON or None if fetch fails
    """
    try:
        params = {}
        # If caller didn't provide a country code, check environment variable
        cc = country_code or os.environ.get("TIDAL_COUNTRY")
        if cc:
            params["countryCode"] = cc
        # merge extra params if provided (do not overwrite existing keys unless provided)
        if extra_params and isinstance(extra_params, dict):
            for k, v in extra_params.items():
                params[k] = v

        # Use session.request.request to call the internal API endpoint
        resp = session.request.request("GET", f"{media_type}/{media_id}", params=params)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError:
        return None  # Silently ignore HTTP errors
    except Exception:
        return None  # Silently ignore other errors


def fetch_raw_track_and_album(
    session: Session,
    track_id: str,
    country_code: str | None = None,
    extra_params: dict | None = None,
) -> tuple[dict | None, dict | None]:
    """Convenience to fetch raw track JSON and its album JSON (if available).

    Returns a tuple (track_json, album_json).

    Uses TIDAL API parameters to fetch extended metadata.
    Note: 'credits' and 'contributors' are NOT available in TIDAL API v2.
    Available include values: albums, artists, genres, lyrics, owners, providers,
    radio, shares, similarTracks, sourceFile, trackStatistics
    """
    # Use valid include parameters according to TIDAL API v2 spec
    # https://tidal-music.github.io/tidal-api-reference/
    default_track_params = {
        "include": "albums,artists,genres",  # Valid parameters per API spec
    }
    merged_track_params = {**default_track_params, **(extra_params or {})}

    track_json = fetch_raw_media_json(
        session,
        "tracks",
        str(track_id),
        country_code=country_code,
        extra_params=merged_track_params,
    )

    album_json = None
    try:
        if isinstance(track_json, dict):
            album = track_json.get("album")
            album_id = album.get("id") if isinstance(album, dict) else album
            if album_id:
                # Request extended album metadata
                default_album_params = {
                    "include": "artists,genres",  # Valid parameters for albums
                }
                merged_album_params = {**default_album_params, **(extra_params or {})}

                album_json = fetch_raw_media_json(
                    session,
                    "albums",
                    str(album_id),
                    country_code=country_code,
                    extra_params=merged_album_params,
                )
    except Exception:
        album_json = None

    return track_json, album_json


def _normalize_dict_contributors(raw_contributors: dict) -> dict[str, list[str]]:
    """Process contributors in dict format: role -> list[{name, ...}]."""
    result: dict[str, list[str]] = {}
    for role, people in raw_contributors.items():
        if not isinstance(people, list):
            continue
        names: list[str] = []
        for person in people:
            if isinstance(person, dict):
                name = person.get("name")
                if isinstance(name, str) and name:
                    names.append(name)
        if names:
            result[role] = names
    return result


def _normalize_list_contributors(raw_contributors: list) -> dict[str, list[str]]:
    """Process contributors in list format: [{name, role, ...}, ...]."""
    result: dict[str, list[str]] = {}
    for person in raw_contributors:
        if not isinstance(person, dict):
            continue
        name = person.get("name")
        role = person.get("role")
        if isinstance(name, str) and name and isinstance(role, str) and role:
            result.setdefault(role, []).append(name)
    return result


def _normalize_contributors(raw_contributors: object) -> dict[str, list[str]]:
    """Normalize various possible contributor JSON shapes into role -> list[str] names.

    The TIDAL API has used at least two shapes historically:
    - dict role -> list[ {"name": str, ...} ]
    - list[ {"name": str, "role": str, ...} ]

    We accept both and ignore malformed entries.
    """
    if isinstance(raw_contributors, dict):
        return _normalize_dict_contributors(raw_contributors)
    if isinstance(raw_contributors, list):
        return _normalize_list_contributors(raw_contributors)
    return {}


def _extract_bpm_from_track(track_json: dict) -> int | None:
    """Extract BPM from track JSON."""
    bpm = track_json.get("bpm")
    if isinstance(bpm, int | float):
        return int(round(bpm))
    if isinstance(bpm, str):
        with contextlib.suppress(ValueError):
            return int(round(float(bpm)))
    return None


def _process_credits_contributors(credits_list: list) -> dict[str, list[str]]:
    """Process credits API v2 format and return contributors by role."""
    role_mapping = {
        "producer": "producer",
        "producers": "producer",
        "composer": "composer",
        "composers": "composer",
        "lyricist": "lyricist",
        "lyricists": "lyricist",
        "writer": "composer",
        "writers": "composer",
    }
    result: dict[str, list[str]] = {}
    for credit in credits_list:
        if not isinstance(credit, dict):
            continue
        credit_type = credit.get("type", "").lower()
        contributors = credit.get("contributors", [])
        role = role_mapping.get(credit_type, credit_type)
        if isinstance(contributors, list):
            for contributor in contributors:
                if isinstance(contributor, dict):
                    name = contributor.get("name")
                    if name:
                        result.setdefault(role, []).append(name)
    return result


def _extract_track_contributors(track_json: dict) -> dict[str, list[str]]:
    """Extract contributors from track JSON."""
    # Try credits first (API v2)
    track_credits = track_json.get("credits")
    if track_credits and isinstance(track_credits, list):
        contributors = _process_credits_contributors(track_credits)
        if contributors:
            return contributors
    # Fallback to old format
    raw_contributors = track_json.get("contributors")
    if raw_contributors:
        return _normalize_contributors(raw_contributors)
    return {}


def _process_genre_item(g: object) -> str | None:
    """Extract genre name from various formats."""
    if isinstance(g, str) and g:
        return g
    if isinstance(g, dict):
        name = g.get("name")
        if isinstance(name, str) and name:
            return name
    return None


def _deduplicate_genres(genres: list[str]) -> list[str]:
    """Deduplicate genres while preserving order."""
    seen: set[str] = set()
    unique: list[str] = []
    for g in genres:
        if g not in seen:
            seen.add(g)
            unique.append(g)
    return unique


def _extract_album_label_genres(album_json: dict) -> tuple[str, list[str]]:
    """Extract label and genres from album JSON."""
    # Label
    label = album_json.get("label") or album_json.get("recordLabel")
    label_str = label if isinstance(label, str) else ""

    # Genres
    raw_genres = album_json.get("genres") or album_json.get("genre")
    genres: list[str] = []

    if isinstance(raw_genres, list):
        for g in raw_genres:
            genre = _process_genre_item(g)
            if genre:
                genres.append(genre)
    elif isinstance(raw_genres, str) and raw_genres:
        genres.append(raw_genres)
    else:
        genre = _process_genre_item(raw_genres)
        if genre:
            genres.append(genre)

    # Deduplicate while preserving order
    if genres:
        return label_str, _deduplicate_genres(genres)
    return label_str, []


def _extract_album_contributors(album_json: dict) -> dict[str, list[str]]:
    """Extract contributors from album JSON."""
    # Try credits first (API v2)
    album_credits = album_json.get("credits")
    if album_credits and isinstance(album_credits, list):
        contributors = _process_credits_contributors(album_credits)
        if contributors:
            return contributors
    # Fallback to old format
    raw_contributors = album_json.get("contributors")
    if raw_contributors:
        return _normalize_contributors(raw_contributors)
    return {}


def parse_track_and_album_extras(
    track_json: dict | None,
    album_json: dict | None,
) -> dict:
    """Extract extra metadata from raw TIDAL JSON for a track and its album.

    Returned dict keys (all optional, may be missing or empty):
      - bpm: int | None
      - label: str
      - genres: list[str]
      - contributors_by_role: dict[str, list[str]]
    """

    extras: dict = {
        "bpm": None,
        "label": "",
        "genres": [],
        "contributors_by_role": {},
    }

    # Extract from track
    if isinstance(track_json, dict):
        extras["bpm"] = _extract_bpm_from_track(track_json)
        extras["contributors_by_role"] = _extract_track_contributors(track_json)

    # Extract from album
    if isinstance(album_json, dict):
        label, genres = _extract_album_label_genres(album_json)
        extras["label"] = label
        extras["genres"] = genres

        # If we did not get track-level contributors, try album-level
        if not extras["contributors_by_role"]:
            extras["contributors_by_role"] = _extract_album_contributors(album_json)

    return extras


def extract_contributor_names(
    contributors_by_role: dict[str, list[str]] | None,
    role: str,
    delimiter: str = ", ",
) -> str:
    """Return a delimited string of contributor names for a given role.

    If the role is not present or has no names, returns an empty string.
    Role matching is case-insensitive.
    """
    if not contributors_by_role:
        return ""

    # Normalise keys to lowercase for robust lookups.
    role_lc = role.lower()
    for r, names in contributors_by_role.items():
        if not isinstance(r, str):
            continue
        if r.lower() == role_lc and isinstance(names, list):
            filtered = [n for n in names if isinstance(n, str) and n]
            if filtered:
                return delimiter.join(filtered)

    return ""
