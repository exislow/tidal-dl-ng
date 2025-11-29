"""Helpers for populating media details in InfoTabWidget - Reduces code duplication."""

from tidal_dl_ng.helper.metadata_utils import find_attr, safe_str
from tidal_dl_ng.helper.tidal import name_builder_title
from tidal_dl_ng.ui.info_tab_widget import TrackInfoFormatter


class MediaDetailsHelper:
    """Helper class to populate media details, reducing duplication in InfoTabWidget."""

    @staticmethod
    def populate_basic_fields(labels: dict, media, media_type: str = "track") -> None:
        """Populate fields common to all media types.

        Args:
            labels: Dictionary mapping field names to QLabel widgets
            media: The media object (Track, Video, Album, etc.)
            media_type: Type of media ("track", "video", "album")
        """
        # Title and version
        title = name_builder_title(media) if media_type != "album" else getattr(media, "name", None)
        version = getattr(media, "version", None)
        labels["title"].setText(safe_str(title))
        labels["version"].setText(safe_str(version))

        # Artists
        artists = TrackInfoFormatter.format_artists(media)
        labels["artists"].setText(safe_str(artists))

        # Duration
        duration = TrackInfoFormatter.format_duration(getattr(media, "duration", None))
        labels["duration"].setText(safe_str(duration))

        # Popularity
        popularity = getattr(media, "popularity", None)
        labels["popularity"].setText(safe_str(popularity))

    @staticmethod
    def populate_album_fields(labels: dict, media) -> None:
        """Populate album-related fields."""
        album_name = None
        release_date = None

        if hasattr(media, "album") and media.album:
            album_name = getattr(media.album, "name", None)
            if hasattr(media.album, "release_date"):
                release_date = TrackInfoFormatter.format_date(media.album.release_date)
        elif hasattr(media, "release_date"):
            release_date = TrackInfoFormatter.format_date(media.release_date)

        labels["album"].setText(safe_str(album_name))
        labels["release_date"].setText(safe_str(release_date))

    @staticmethod
    def populate_technical_fields(labels: dict, media) -> None:
        """Populate technical fields (codec, bitrate, ISRC, track number)."""
        # Codec & Bitrate
        codec = TrackInfoFormatter.format_codec(media)
        labels["codec"].setText(safe_str(codec))
        bitrate = TrackInfoFormatter.format_bitrate(media)
        labels["bitrate"].setText(safe_str(bitrate))

        # ISRC
        isrc = getattr(media, "isrc", None)
        labels["isrc"].setText(safe_str(isrc))

        # Track Number
        track_number = find_attr(media, "track_number", "tracknumber", "number", "position")
        if not track_number and hasattr(media, "album") and media.album:
            track_number = find_attr(media.album, "track_number", "tracknumber")
        labels["track_number"].setText(safe_str(track_number))

    @staticmethod
    def populate_metadata_fields(labels: dict, media) -> None:
        """Populate metadata fields (BPM, Label, Producers, Composers)."""
        # BPM
        bpm = find_attr(media, "bpm", "tempo")
        if not bpm and hasattr(media, "album") and media.album:
            bpm = find_attr(media.album, "bpm", "tempo")
        labels["bpm"].setText(safe_str(bpm))

        # Label
        label = None
        if hasattr(media, "album") and media.album:
            label = find_attr(media.album, "label", "label_name", "recordLabel")
        if not label:
            label = find_attr(media, "label", "label_name", "recordLabel")
        labels["label"].setText(safe_str(label))

        # Producers/Composers
        producers = find_attr(media, "producers", "producer")
        labels["producers"].setText(safe_str(producers) if producers else "—")

        composers = find_attr(media, "composers", "composer")
        labels["composers"].setText(safe_str(composers) if composers else "—")

    @staticmethod
    def populate_genres(labels: dict, media) -> None:
        """Extract and populate genre information with filtering."""
        genres = find_attr(media, "genres", "genre")
        if not genres and hasattr(media, "album") and media.album:
            genres = find_attr(media.album, "genres", "genre")

        if not genres:
            labels["genres"].setText("—")
            return

        # Normalize to list and filter technical tags
        genre_list = genres if isinstance(genres, list | tuple) else [genres]
        excluded = ("atmos", "dolby", "hq", "lossless", "mqa", "flac", "wav", "pcm", "audio", "bit", "track")
        filtered = [
            str(g) for g in genre_list if g and isinstance(g, str) and not any(kw in g.lower() for kw in excluded)
        ]

        labels["genres"].setText(safe_str(", ".join(filtered)) if filtered else "—")
