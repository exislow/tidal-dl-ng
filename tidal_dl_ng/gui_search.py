# tidal_dl_ng/gui_search.py

from typing import TYPE_CHECKING, Any

from tidalapi import Album, Artist, Mix, Playlist, Track, Video
from tidalapi.media import AudioMode
from tidalapi.playlist import Folder
from tidalapi.session import SearchTypes

from tidal_dl_ng.helper.tidal import (
    get_tidal_media_id,
    get_tidal_media_type,
    instantiate_media,
    name_builder_artist,
    quality_audio_highest,
    search_results_all,
    url_ending_clean,
)
from tidal_dl_ng.logger import logger_gui
from tidal_dl_ng.model.gui_data import ResultItem

if TYPE_CHECKING:
    from tidal_dl_ng.gui import MainWindow


class GuiSearchManager:
    """Manages the search GUI and logic."""

    def __init__(self, main_window: "MainWindow"):
        """Initialize the search manager."""
        self.main_window: "MainWindow" = main_window

    def search_populate_results(self, query: str, type_media: Any) -> None:
        """Populate the results tree with search results."""
        results = self.search(query, [type_media])
        self.main_window.populate_tree_results(results)

    def search(self, query: str, types_media: list[Any]) -> list[ResultItem]:
        """Perform a search and return a list of ResultItems."""
        query_clean = query.strip()
        if "http" in query_clean:
            query_clean = url_ending_clean(query_clean)
            media_type = get_tidal_media_type(query_clean)
            item_id = get_tidal_media_id(query_clean)
            try:
                media = instantiate_media(self.main_window.tidal.session, media_type, item_id)
                result_search = {"direct": [media]}
            except Exception:
                logger_gui.error(f"Media not found (ID: {item_id}). Maybe it is not available anymore.")
                result_search = {"direct": []}
        else:
            result_search = search_results_all(
                session=self.main_window.tidal.session, needle=query_clean, types_media=types_media
            )
        result = []
        for _media_type, l_media in result_search.items():
            if isinstance(l_media, list):
                result.extend(self.search_result_to_model(l_media))
        return result

    def search_result_to_model(self, items: list[SearchTypes]) -> list[ResultItem]:
        """Convert search results to ResultItem models."""
        return [self._to_result_item(idx, item) for idx, item in enumerate(items) if self._to_result_item(idx, item)]

    def _to_result_item(self, idx: int, item: Any) -> ResultItem | None:
        """Helper to convert a single item to ResultItem."""
        if not item or (hasattr(item, "available") and not item.available):
            return None

        explicit = " 🅴" if isinstance(item, Track | Video | Album) and item.explicit else ""
        date_user_added = (
            item.user_date_added.strftime("%Y-%m-%d_%H:%M") if getattr(item, "user_date_added", None) else ""
        )
        date_release = self._get_date_release(item)

        type_handlers = {
            Track: self._result_item_from_track,
            Video: self._result_item_from_video,
            Playlist: self._result_item_from_playlist,
            Album: self._result_item_from_album,
            Mix: self._result_item_from_mix,
            Artist: self._result_item_from_artist,
            Folder: self._result_item_from_folder,
        }

        for item_type, handler in type_handlers.items():
            if isinstance(item, item_type):
                return handler(idx, item, explicit, date_user_added, date_release)
        return None

    def _get_date_release(self, item: Any) -> str:
        """Get the release date string for an item."""
        if hasattr(item, "album") and item.album and getattr(item.album, "release_date", None):
            return item.album.release_date.strftime("%Y-%m-%d_%H:%M")
        if hasattr(item, "release_date") and item.release_date:
            return item.release_date.strftime("%Y-%m-%d_%H:%M")
        return ""

    def _result_item_from_track(
        self, idx: int, item: Track, explicit: str, date_user_added: str, date_release: str
    ) -> ResultItem:
        """Create a ResultItem from a Track."""
        final_quality = quality_audio_highest(item)
        if hasattr(item, "audio_modes") and AudioMode.dolby_atmos.value in item.audio_modes:
            final_quality = f"{final_quality} / Dolby Atmos"
        return ResultItem(
            position=idx,
            artist=name_builder_artist(item),
            title=f"{item.name}{explicit}",
            album=item.album.name,
            duration_sec=item.duration,
            obj=item,
            quality=final_quality,
            explicit=bool(item.explicit),
            date_user_added=date_user_added,
            date_release=date_release,
        )

    def _result_item_from_video(
        self, idx: int, item: Video, explicit: str, date_user_added: str, date_release: str
    ) -> ResultItem:
        """Create a ResultItem from a Video."""
        return ResultItem(
            position=idx,
            artist=name_builder_artist(item),
            title=f"{item.name}{explicit}",
            album=item.album.name if item.album else "",
            duration_sec=item.duration,
            obj=item,
            quality=item.video_quality,
            explicit=bool(item.explicit),
            date_user_added=date_user_added,
            date_release=date_release,
        )

    def _result_item_from_playlist(
        self, idx: int, item: Playlist, explicit: str, date_user_added: str, date_release: str
    ) -> ResultItem:
        """Create a ResultItem from a Playlist."""
        return ResultItem(
            position=idx,
            artist=", ".join(artist.name for artist in item.promoted_artists) if item.promoted_artists else "",
            title=item.name,
            album="",
            duration_sec=item.duration,
            obj=item,
            quality="",
            explicit=False,
            date_user_added=date_user_added,
            date_release=date_release,
        )

    def _result_item_from_album(
        self, idx: int, item: Album, explicit: str, date_user_added: str, date_release: str
    ) -> ResultItem:
        """Create a ResultItem from an Album."""
        return ResultItem(
            position=idx,
            artist=name_builder_artist(item),
            title="",
            album=f"{item.name}{explicit}",
            duration_sec=item.duration,
            obj=item,
            quality=quality_audio_highest(item),
            explicit=bool(item.explicit),
            date_user_added=date_user_added,
            date_release=date_release,
        )

    def _result_item_from_mix(
        self, idx: int, item: Mix, explicit: str, date_user_added: str, date_release: str
    ) -> ResultItem:
        """Create a ResultItem from a Mix."""
        return ResultItem(
            position=idx,
            artist=item.sub_title,
            title=item.title,
            album="",
            duration_sec=-1,
            obj=item,
            quality="",
            explicit=False,
            date_user_added=date_user_added,
            date_release=date_release,
        )

    def _result_item_from_artist(
        self, idx: int, item: Artist, explicit: str, date_user_added: str, date_release: str
    ) -> ResultItem:
        """Create a ResultItem from an Artist."""
        return ResultItem(
            position=idx,
            artist=item.name,
            title="",
            album="",
            duration_sec=-1,
            obj=item,
            quality="",
            explicit=False,
            date_user_added=date_user_added,
            date_release=date_release,
        )

    def _result_item_from_folder(
        self, idx: int, item: Folder, explicit: str, date_user_added: str, date_release: str
    ) -> ResultItem:
        """Create a ResultItem from a Folder."""
        total_items = item.total_number_of_items if hasattr(item, "total_number_of_items") else 0
        return ResultItem(
            position=idx,
            artist="",
            title=f"📁 {item.name} ({total_items} items)",
            album="",
            duration_sec=-1,
            obj=item,
            quality="",
            explicit=False,
            date_user_added=date_user_added,
            date_release=date_release,
        )
