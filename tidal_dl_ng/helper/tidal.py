from tidalapi import Album, Mix, Playlist, Session, Track, UserPlaylist, Video
from tidalapi.session import SearchTypes

from tidal_dl_ng.constants import MediaType


def name_builder_artist(media: Track) -> str:
    return ", ".join(artist.name for artist in media.artists)


def name_builder_title(media: Track) -> str:
    return media.name


def name_builder_item(media: Track) -> str:
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


def items_results_all(media_list: [Mix | Playlist | Album], videos_include: bool = True) -> [Track | Video]:
    limit: int = 100
    offset: int = 0
    done: bool = False
    result: [Track | Video] = []

    if isinstance(media_list, Mix):
        result = media_list.items()
    else:
        while not done:
            tmp_result: [Track | Video] = (
                media_list.items(limit=limit, offset=offset)
                if videos_include
                else media_list.tracks(limit=limit, offset=offset)
            )

            if bool(tmp_result):
                result += tmp_result
                # Get the next page in the next iteration.
                offset += limit
            else:
                done = True

    return result


def user_media_lists(session: Session) -> [Playlist | UserPlaylist | Mix]:
    user_playlists: [Playlist | UserPlaylist] = session.user.playlist_and_favorite_playlists()
    user_mixes: [Mix] = session.mixes().categories[0].items
    result: [Playlist | UserPlaylist | Mix] = user_playlists + user_mixes

    return result
