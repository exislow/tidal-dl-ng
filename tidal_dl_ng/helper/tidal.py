from collections.abc import Callable

from tidalapi import Album, Mix, Playlist, Session, Track, UserPlaylist, Video
from tidalapi.artist import Artist, Role
from tidalapi.media import MediaMetadataTags, Quality
from tidalapi.session import SearchTypes
from tidalapi.user import LoggedInUser

from tidal_dl_ng.constants import FAVORITES, MediaType
from tidal_dl_ng.helper.exceptions import MediaUnknown


def name_builder_artist(media: Track | Video | Album) -> str:
    return ", ".join(artist.name for artist in media.artists)


def name_builder_album_artist(media: Track | Album, first_only: bool = False) -> str:
    artists_tmp: [str] = []
    artists: [Artist] = media.album.artists if isinstance(media, Track) else media.artists

    for artist in artists:
        if Role.main in artist.roles:
            artists_tmp.append(artist.name)

        if first_only:
            break

    return ", ".join(artists_tmp)


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
    media_list: [Mix | Playlist | Album | Artist], videos_include: bool = True
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
        else:
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


def user_media_lists(session: Session) -> [Playlist | UserPlaylist | Mix]:
    user_playlists: [Playlist | UserPlaylist] = paginate_results([session.user.playlist_and_favorite_playlists])
    user_mixes: [Mix] = session.mixes().categories[0].items
    result: [Playlist | UserPlaylist | Mix] = user_playlists + user_mixes

    return result


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

    if MediaMetadataTags.hi_res_lossless in media.media_metadata_tags:
        quality = Quality.hi_res_lossless
    elif MediaMetadataTags.lossless in media.media_metadata_tags:
        quality = Quality.high_lossless
    else:
        quality = media.audio_quality

    return quality


def favorite_function_factory(tidal, favorite_item: str):
    function_name: str = FAVORITES[favorite_item]["function_name"]
    function_list: Callable = getattr(tidal.session.user.favorites, function_name)

    return function_list
