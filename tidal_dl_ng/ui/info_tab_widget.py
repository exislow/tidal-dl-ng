"""Info Tab Widget - Dynamic tabbed information panel for track hover preview.

This module provides a sophisticated tabbed widget that displays rich metadata
for TIDAL media items on hover, implementing a debounced event system to prevent
UI flickering and unnecessary API calls.

Architecture:
    - InfoTabWidget: Main container with two tabs (Details + Cover Art)
    - DebounceTimer: Configurable timer to prevent event flooding
    - TrackInfoFormatter: Utility class to format track metadata consistently

Performance Considerations:
    - Pre-loaded metadata to avoid API chattiness
    - Debounced hover events (300-400ms delay)
    - Thread-safe signal emissions for cross-thread updates
"""

import datetime
from collections.abc import Callable, Iterable
from contextlib import suppress
from typing import TYPE_CHECKING

from PySide6 import QtCore, QtGui, QtWidgets
from tidalapi import Album, Mix, Playlist, Track, Video
from tidalapi.artist import Artist
from tidalapi.media import AudioMode

from tidal_dl_ng.helper.metadata_utils import extract_names_from_mixed, find_attr, safe_str
from tidal_dl_ng.helper.path import resource_path
from tidal_dl_ng.helper.tidal import name_builder_artist, name_builder_title, quality_audio_highest

if TYPE_CHECKING:
    pass


class TrackInfoFormatter:
    """Formats track metadata into human-readable strings.

    This utility class handles the conversion of raw TIDAL API objects into
    formatted display strings for the UI.
    """

    @staticmethod
    def _get_artist_name(artist: object) -> str:
        """Safely get artist name from artist object."""
        name = getattr(artist, "name", None)
        if name is None:
            with suppress(Exception):
                return str(artist)
            return "Unknown"
        return str(name)

    @staticmethod
    def _format_artist_roles(artist: object) -> list[str]:
        """Extract and format artist roles."""
        if not hasattr(artist, "roles") or not artist.roles:
            return []
        roles = []
        for role in artist.roles:
            rname = getattr(role, "name", None)
            if rname is None:
                with suppress(Exception):
                    rname = str(role)
            if rname:
                roles.append(str(rname))
        return roles

    @staticmethod
    def format_artists(media: Track | Video | Album) -> str:
        """Format artist names with roles if available.

        Args:
            media (Track | Video | Album): The media object with artist information.

        Returns:
            str: Formatted artist string (e.g., "Artist1, Artist2 (Feature)").
        """
        with suppress(Exception):
            artist_parts: list[str] = []
            artists = getattr(media, "artists", [])

            for artist in artists:
                name = TrackInfoFormatter._get_artist_name(artist)
                roles = TrackInfoFormatter._format_artist_roles(artist)

                if roles and roles[0] != "main":
                    name = f"{name} ({', '.join(roles)})"
                artist_parts.append(name)

            if artist_parts:
                return ", ".join(artist_parts)

        return name_builder_artist(media) if hasattr(media, "artists") else "Unknown Artist"

    @staticmethod
    def format_codec(track: Track) -> str:
        """Format codec information including audio mode.

        Args:
            track (Track): The track object.

        Returns:
            str: Formatted codec string (e.g., "FLAC / Dolby Atmos").
        """
        codec_parts: list[str] = []

        # If this is a Video object, prefer video_quality (e.g., '1080p')
        if hasattr(track, "video_quality"):
            with suppress(Exception):
                return str(track.video_quality)

        # Get base quality for audio tracks
        quality = quality_audio_highest(track)
        if quality:
            codec_parts.append(str(quality).upper())

        # Check for Dolby Atmos
        if hasattr(track, "audio_modes") and track.audio_modes and AudioMode.dolby_atmos.value in track.audio_modes:
            codec_parts.append("Dolby Atmos")

        # Check for MQA
        if (
            hasattr(track, "media_metadata_tags")
            and track.media_metadata_tags
            and "MQA" in str(track.media_metadata_tags)
        ):
            codec_parts.append("MQA")

        return " / ".join(codec_parts) if codec_parts else "N/A"

    @staticmethod
    def format_duration(duration_sec: int | None) -> str:
        """Format duration in seconds to MM:SS format.

        Args:
            duration_sec (int | None): Duration in seconds.

        Returns:
            str: Formatted duration string.
        """
        # Treat 0 as a valid duration (00:00); only None or missing -> N/A
        if duration_sec is None:
            return "N/A"

        minutes = duration_sec // 60
        seconds = duration_sec % 60
        return f"{minutes:02d}:{seconds:02d}"

    @staticmethod
    def format_date(date_obj) -> str:
        """Format date object to readable string.

        Args:
            date_obj: Date object (datetime or similar).

        Returns:
            str: Formatted date string (YYYY-MM-DD) or N/A.
        """
        if date_obj is None:
            return "N/A"

        try:
            # Only call strftime on actual date/datetime objects to avoid
            # mocks or unrelated objects having a 'strftime' attribute.
            if isinstance(date_obj, datetime.date | datetime.datetime):
                return date_obj.strftime("%Y-%m-%d")

            # If it's already a string, return as-is
            if isinstance(date_obj, str):
                return date_obj

            # Fallback to string conversion
            return str(date_obj)
        except Exception:
            return "N/A"

    @staticmethod
    def format_bitrate(track: Track) -> str:
        """Format bitrate information.

        Args:
            track (Track): The track object.

        Returns:
            str: Formatted bitrate string.
        """
        # Check for bit depth and sample rate
        bit_depth = getattr(track, "bit_depth", None)
        sample_rate = getattr(track, "sample_rate", None)

        if bit_depth and sample_rate:
            return f"{bit_depth}-bit / {sample_rate / 1000:.1f} kHz"
        elif sample_rate:
            return f"{sample_rate / 1000:.1f} kHz"
        return "N/A"


class InfoTabWidget(QtCore.QObject):
    """Controller for the tabbed widget displaying rich media information.

    This class manages the logic for the info tabs but is not a widget itself.
    It binds to existing widgets created from a .ui file.
    """

    # Signals for cross-thread communication
    s_update_details: QtCore.Signal = QtCore.Signal(object)
    s_update_cover: QtCore.Signal = QtCore.Signal(str)
    s_spinner_start: QtCore.Signal = QtCore.Signal()
    s_spinner_stop: QtCore.Signal = QtCore.Signal()
    s_search_in_app: QtCore.Signal = QtCore.Signal(str, str)
    s_search_in_browser: QtCore.Signal = QtCore.Signal(str, str)

    def _setup_search_roots(self, parent_widget: QtWidgets.QTabWidget | None) -> list:
        """Setup list of widget roots to search for UI elements."""
        search_roots = [parent_widget]
        if hasattr(parent_widget, "parent") and parent_widget.parent() is not None:
            search_roots.append(parent_widget.parent())
        with suppress(Exception):
            root_window = parent_widget.window()
            if root_window is not None:
                search_roots.append(root_window)
        return search_roots

    def _find_widget_in_roots(self, objname: str, search_roots: list) -> QtWidgets.QLabel | None:
        """Find a QLabel widget by objectName in search roots."""
        for root in search_roots:
            with suppress(Exception):
                found = root.findChild(QtWidgets.QLabel, objname)
                if found is not None:
                    return found
        return None

    def _create_fallback_widget(self, desc: str, parent_widget: QtWidgets.QWidget) -> tuple[str, QtWidgets.QLabel]:
        """Create a fallback invisible widget for a missing UI element."""
        name = desc.split("(")[-1].rstrip(")") if "(" in desc and ")" in desc else f"fallback_{desc.replace(' ', '_')}"

        fallback = QtWidgets.QLabel("—", parent_widget)
        fallback.setObjectName(name)
        fallback.setVisible(False)
        return name, fallback

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        existing_tab_widget: QtWidgets.QTabWidget | None = None,
    ) -> None:
        """Initialize the InfoTabWidget controller.

        Args:
            parent (QWidget | None): Parent widget. Defaults to None.
            existing_tab_widget (QTabWidget | None): The tab widget from the UI to control.
        """
        super().__init__(parent)

        # State management
        self.current_media_hovered: Track | Video | Album | Mix | Playlist | Artist | None = None
        self.current_media_selected: Track | Video | Album | Mix | Playlist | Artist | None = None
        self.cover_url_current: str = ""
        self._track_extras_provider: Callable[[str], dict] | None = None

        # Bind to widgets created in the .ui by exact objectName.
        self.tab_widget = existing_tab_widget
        parent_widget = self.tab_widget

        # REQUIRED object names provided by main.ui
        required = {
            "lbl_title": "Title label (lbl_title)",
            "lbl_version": "Version label (lbl_version)",
            "lbl_artists": "Artists label (lbl_artists)",
            "lbl_album": "Album label (lbl_album)",
            "lbl_codec": "Codec label (lbl_codec)",
            "lbl_bitrate": "Bitrate label (lbl_bitrate)",
            "lbl_duration": "Duration label (lbl_duration)",
            "lbl_release_date": "Release date label (lbl_release_date)",
            "lbl_popularity": "Popularity label (lbl_popularity)",
            "lbl_bpm": "BPM label (lbl_bpm)",
            "lbl_isrc": "ISRC label (lbl_isrc)",
            "lbl_track_number": "Track number label (lbl_track_number)",
            "l_pm_cover": "Cover QLabel (l_pm_cover)",
        }

        # Lookup and assign
        search_roots = self._setup_search_roots(parent_widget)
        missing = []

        for objname, desc in required.items():
            found_widget = self._find_widget_in_roots(objname, search_roots)
            if not found_widget:
                missing.append(desc)
            else:
                attr_name = "cover_label" if objname == "l_pm_cover" else objname
                setattr(self, attr_name, found_widget)

        # Create fallback widgets for missing elements
        if missing:
            for desc in missing:
                name, fallback = self._create_fallback_widget(desc, parent_widget)
                if name == "l_pm_cover":
                    self.cover_label = fallback
                else:
                    setattr(self, name, fallback)

        # Ensure cover_label exists
        if not hasattr(self, "cover_label"):
            self.cover_label = QtWidgets.QLabel("", parent_widget)
            self.cover_label.setVisible(False)
            self.cover_label.setObjectName("cover_label_fallback")

        # connect signals
        self._connect_signals()

        # Make labels clickable using linkActivated signal
        clickable_labels = [self.lbl_title, self.lbl_artists, self.lbl_album]
        for label in clickable_labels:
            label.setTextFormat(QtCore.Qt.RichText)
            label.setOpenExternalLinks(False)  # We handle links manually
            label.linkActivated.connect(self._on_link_activated)
            label.installEventFilter(self)  # For right-click handling
            label.setToolTip("Left-click to search in app, Ctrl+click or right-click to search in browser.")

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """Filter events for clickable labels to handle right-clicks."""
        if event.type() == QtCore.QEvent.Type.MouseButtonPress and isinstance(watched, QtWidgets.QLabel):
            event: QtGui.QMouseEvent
            if event.button() == QtCore.Qt.MouseButton.RightButton:
                # On right-click, find the link under the cursor
                anchor = watched.anchorAt(event.pos())
                if anchor:
                    self._on_link_activated(anchor, right_click=True)
                    return True  # Event handled

        return super().eventFilter(watched, event)

    def _create_link(self, search_type: str, text: str) -> str:
        """Create an HTML link for search, using a specific color."""
        if not text or text == "—":
            return "—"
        # The link format is "search:type:text"
        link_target = f"search:{search_type}:{text}"
        # Use a standard link color; Qt will handle styling.
        return f"<a href='{link_target}' style='color:#367af6;'>{text}</a>"

    @QtCore.Slot(str)
    def _on_link_activated(self, link: str, right_click: bool = False) -> None:
        """Handle clicks on rich text links in labels."""
        if not link:
            return

        parts = link.split(":", 2)
        if len(parts) < 3 or parts[0] != "search":
            return

        search_type = parts[1]
        search_term = parts[2]
        modifiers = QtWidgets.QApplication.keyboardModifiers()

        is_browser_action = right_click or (modifiers & QtCore.Qt.KeyboardModifier.ControlModifier)

        if is_browser_action:
            # Ctrl+Click or Right-Click: Open in browser
            self.s_search_in_browser.emit(search_term, search_type)
        else:
            # Left-Click: Search in app
            self.s_search_in_app.emit(search_term, search_type)

    def _connect_signals(self) -> None:
        """Connect internal signals to slots."""
        self.s_update_details.connect(self._on_update_details)
        self.s_update_cover.connect(self._on_update_cover)
        self.s_spinner_start.connect(self._spin_start)
        self.s_spinner_stop.connect(self._spin_stop)

    def _on_update_cover(self, cover_url: str) -> None:
        """Update cover image from URL.

        Args:
            cover_url (str): URL or path to the cover image.
        """
        if cover_url and cover_url != self.cover_url_current:
            self.cover_url_current = cover_url
            with suppress(Exception):
                self.set_cover_pixmap(cover_url)

    def set_track_extras_provider(
        self, provider: Callable[[str, Callable[[str, dict | None], None]], dict | None] | None
    ) -> None:
        """Register a callable that fetches track extras asynchronously.

        The provider must accept ``track_id`` and a callback; it may return
        immediate extras synchronously. Passing ``None`` removes the provider.
        """
        self._track_extras_provider = provider

    def set_cover_pixmap(self, content: QtGui.QPixmap | str) -> None:
        """Set the cover image pixmap or path."""
        with suppress(Exception):
            if isinstance(content, QtGui.QPixmap):
                self.cover_label.setPixmap(content)
            elif isinstance(content, str) and content:
                pixmap = QtGui.QPixmap()
                if pixmap.load(content):
                    self.cover_label.setPixmap(pixmap)

    def _spin_start(self) -> None:
        """Track nested spinner requests so UI stays responsive."""
        count = getattr(self, "_spinner_depth", 0) + 1
        self._spinner_depth = count
        parent = self.parent()
        if count == 1 and parent and isinstance(parent, QtWidgets.QWidget):
            parent.setCursor(QtCore.Qt.CursorShape.BusyCursor)

    def _spin_stop(self) -> None:
        """Release spinner state when last request finishes."""
        count = max(getattr(self, "_spinner_depth", 1) - 1, 0)
        self._spinner_depth = count
        parent = self.parent()
        if count == 0 and parent and isinstance(parent, QtWidgets.QWidget):
            parent.setCursor(QtCore.Qt.CursorShape.ArrowCursor)

    def _request_track_extras_if_needed(self, media: object) -> None:
        track_id = getattr(media, "id", None)
        if not isinstance(track_id, int | str):
            return
        if not isinstance(media, Track):
            return
        if self._track_extras_provider is None:
            return
        self.s_spinner_start.emit()
        try:
            immediate = self._track_extras_provider(str(track_id), self._handle_track_extras_ready)
            if immediate:
                self._apply_track_extras(immediate)
                self.s_spinner_stop.emit()
        except Exception:
            self.s_spinner_stop.emit()

    def _handle_track_extras_ready(self, track_id: str, extras: dict | None) -> None:
        """Callback invoked by the provider when async extras are ready."""
        try:
            if extras:
                current = self.current_media_hovered or self.current_media_selected
                current_id = getattr(current, "id", None)
                if current_id is not None and str(current_id) == str(track_id):
                    self._apply_track_extras(extras)
        finally:
            self.s_spinner_stop.emit()

    def _apply_track_extras(self, extras: dict | None) -> None:
        """Apply the track extras to the UI.

        This method updates the details tab with additional information such as
        BPM if available.

        Note: Only BPM is available from TIDAL API extras. Genres, label, producers
        and composers are not reliably available.

        Args:
            extras (dict | None): A dictionary containing extra information
                about the track, or None if no extras are available.
        """
        if not isinstance(extras, dict):
            return
        with suppress(RuntimeError):
            self._update_extras_ui(extras)

    @QtCore.Slot(dict)
    def _update_extras_ui(self, extras: dict):
        """Safely update UI with extras from the main thread."""
        if not isinstance(extras, dict):
            return
        try:
            bpm_value = extras.get("bpm")
            display_value = "—" if bpm_value is None else str(bpm_value)
            self.lbl_bpm.setText(display_value)
        except RuntimeError:
            pass  # Widgets deleted, silently ignore

    def update_on_hover(self, media: Track | Video | Album | Mix | Playlist | Artist | None) -> None:
        """Update display based on hovered media item.

        This method is called when the user hovers over a track in the results list.
        It displays information from pre-loaded metadata without triggering API calls.

        Args:
            media (Track | Video | Album | Mix | Playlist | Artist | None): The hovered media item.
        """
        if not media:
            return

        self.current_media_hovered = media

        # Update details tab (from pre-loaded data)
        self.s_update_details.emit(media)

        # Cover is handled by MainWindow
        self._request_track_extras_if_needed(media)

    def update_on_selection(self, media: Track | Video | Album | Mix | Playlist | Artist | None) -> None:
        """Update display based on selected media item.

        This method is called when the user clicks on a track in the results list.
        It persists the selection so the UI can revert to it after hover leaves.

        Args:
            media (Track | Video | Album | Mix | Playlist | Artist | None): The selected media item.
        """
        if not media:
            return

        self.current_media_selected = media

        # Update both tabs
        self.s_update_details.emit(media)
        # Cover is handled by MainWindow
        self._request_track_extras_if_needed(media)

    def revert_to_selection(self) -> None:
        """Revert display to the currently selected media.

        Called when hover leaves the results list to prevent leaving the UI
        in an inconsistent state.
        """
        if self.current_media_selected:
            self.update_on_selection(self.current_media_selected)
        else:
            self._clear_display()

    def _clear_display(self) -> None:
        """Clear all displayed information and reset to default state."""
        self.current_media_hovered = None

        try:
            self.lbl_title.setText("—")
            self.lbl_version.setText("—")
            self.lbl_artists.setText("—")
            self.lbl_album.setText("—")
            self.lbl_codec.setText("—")
            self.lbl_bitrate.setText("—")
            self.lbl_duration.setText("—")
            self.lbl_release_date.setText("—")
            self.lbl_popularity.setText("—")
            self.lbl_bpm.setText("—")
            self.lbl_isrc.setText("—")
            self.lbl_track_number.setText("—")

            # Reset cover to default
            path_image: str = resource_path("tidal_dl_ng/ui/default_album_image.png")
            self.cover_label.setPixmap(QtGui.QPixmap(path_image))
            self.cover_url_current = ""
        except RuntimeError:
            pass  # Widgets deleted, silently ignore

    def _on_update_details(self, media: Track | Video | Album | Mix | Playlist | Artist) -> None:
        """Update details tab with media metadata.

        Args:
            media (Track | Video | Album | Mix | Playlist | Artist): The media item to display.
        """
        # Handle different media types
        if isinstance(media, Track):
            self._populate_track_details(media)
        elif isinstance(media, Video):
            self._populate_video_details(media)
        elif isinstance(media, Album):
            self._populate_album_details(media)
        elif isinstance(media, Playlist | Mix):
            self._populate_playlist_details(media)
        elif isinstance(media, Artist):
            self._populate_artist_details(media)

    def _populate_track_details(self, track: Track) -> None:
        """Populate details for a Track.

        Args:
            track (Track): The track object.
        """
        # Title and version
        title = name_builder_title(track)
        self.lbl_title.setText(self._create_link("track", title))
        version = getattr(track, "version", None)
        self.lbl_version.setText(safe_str(version))

        # Artists
        artist_parts = []
        if hasattr(track, "artists") and track.artists:
            for artist in track.artists:
                name = TrackInfoFormatter._get_artist_name(artist)
                roles = TrackInfoFormatter._format_artist_roles(artist)
                link = self._create_link("artist", name)
                if roles and roles[0] != "main":
                    artist_parts.append(f"{link} ({', '.join(roles)})")
                else:
                    artist_parts.append(link)
        self.lbl_artists.setText(", ".join(artist_parts) if artist_parts else "—")

        # Album name (prefer album object's name)
        album_name = None
        if hasattr(track, "album") and track.album:
            album_name = getattr(track.album, "name", None) or None
        self.lbl_album.setText(self._create_link("album", album_name))

        # Codec & Bitrate
        codec = TrackInfoFormatter.format_codec(track)
        self.lbl_codec.setText(safe_str(codec))
        bitrate = TrackInfoFormatter.format_bitrate(track)
        self.lbl_bitrate.setText(safe_str(bitrate))

        # Duration
        duration = TrackInfoFormatter.format_duration(getattr(track, "duration", None))
        self.lbl_duration.setText(safe_str(duration))

        # Release date (from album if exists)
        release_date = None
        if hasattr(track, "album") and track.album and hasattr(track.album, "release_date"):
            release_date = TrackInfoFormatter.format_date(track.album.release_date)
        self.lbl_release_date.setText(safe_str(release_date))

        # Popularity
        popularity = getattr(track, "popularity", None)
        self.lbl_popularity.setText(safe_str(popularity))

        # BPM: Show loading indicator, will be updated when extras are loaded
        self.lbl_bpm.setText("⏳ Loading...")

        # ISRC
        isrc = getattr(track, "isrc", None)
        self.lbl_isrc.setText(safe_str(isrc))

        # Track Number
        track_number = find_attr(track, "track_number", "tracknumber", "number", "position", "track") or None
        if track_number is None and hasattr(track, "album") and track.album:
            track_number = find_attr(track.album, "track_number", "tracknumber", "number") or None
        self.lbl_track_number.setText(safe_str(track_number))

    def _populate_video_details(self, video: Video) -> None:
        """Populate details for a Video.

        Args:
            video (Video): The video object.
        """
        # Title and version
        title = name_builder_title(video)
        self.lbl_title.setText(self._create_link("video", title))
        version = getattr(video, "version", None)
        self.lbl_version.setText(safe_str(version))

        # Artists
        artists_str = extract_names_from_mixed(
            getattr(video, "credits", None), match_types=("performer", "artist", "actor")
        )
        if not artists_str:
            artist_parts = []
            if hasattr(video, "artists") and video.artists:
                for artist in video.artists:
                    name = TrackInfoFormatter._get_artist_name(artist)
                    artist_parts.append(self._create_link("artist", name))
            self.lbl_artists.setText(", ".join(artist_parts) if artist_parts else "—")
        else:
            self.lbl_artists.setText(self._create_link("artist", artists_str))

        # Album name
        album_name = None
        if hasattr(video, "album") and video.album:
            album_name = getattr(video.album, "name", None) or None
        self.lbl_album.setText(self._create_link("album", album_name))

        # Codec & Bitrate
        codec = TrackInfoFormatter.format_codec(video)
        self.lbl_codec.setText(safe_str(codec))
        bitrate = TrackInfoFormatter.format_bitrate(video)
        self.lbl_bitrate.setText(safe_str(bitrate))

        # Duration
        duration = TrackInfoFormatter.format_duration(getattr(video, "duration", None))
        self.lbl_duration.setText(safe_str(duration))

        # Release date
        release_date = None
        if hasattr(video, "album") and video.album and hasattr(video.album, "release_date"):
            release_date = TrackInfoFormatter.format_date(video.album.release_date)
        self.lbl_release_date.setText(safe_str(release_date))

        # Popularity
        popularity = getattr(video, "popularity", None)
        self.lbl_popularity.setText(safe_str(popularity))

        # ISRC
        isrc = getattr(video, "isrc", None)
        if not isrc and hasattr(video, "track"):
            isrc = getattr(video.track, "isrc", None)
        self.lbl_isrc.setText(safe_str(isrc))

    def _populate_album_details(self, album: Album) -> None:
        """Populate details for an Album.

        Args:
            album (Album): The album object.
        """
        # Title and version
        title = name_builder_title(album)
        self.lbl_title.setText(self._create_link("album", title))
        version = getattr(album, "version", None)
        self.lbl_version.setText(safe_str(version))

        # Artists
        artist_parts = []
        if hasattr(album, "artists") and album.artists:
            for artist in album.artists:
                name = TrackInfoFormatter._get_artist_name(artist)
                artist_parts.append(self._create_link("artist", name))
        self.lbl_artists.setText(", ".join(artist_parts) if artist_parts else "—")

        # Album name (same as title for an album)
        self.lbl_album.setText(self._create_link("album", title))

        # Codec & Bitrate
        codec = TrackInfoFormatter.format_codec(album)
        self.lbl_codec.setText(safe_str(codec))
        bitrate = TrackInfoFormatter.format_bitrate(album)
        self.lbl_bitrate.setText(safe_str(bitrate))

        # Duration
        duration = TrackInfoFormatter.format_duration(getattr(album, "duration", None))
        self.lbl_duration.setText(safe_str(duration))

        # Release date
        release_date = TrackInfoFormatter.format_date(getattr(album, "release_date", None))
        self.lbl_release_date.setText(safe_str(release_date))

        # Popularity
        popularity = getattr(album, "popularity", None)
        self.lbl_popularity.setText(safe_str(popularity))

        self.lbl_isrc.setText("—")

    def _extract_playlist_artists(self, playlist: Playlist | Mix) -> str:
        """Extract and format artists from playlist tracks."""
        if not hasattr(playlist, "tracks") or not isinstance(playlist.tracks, list | Iterable):
            return "—"

        all_artists = set()
        for track in playlist.tracks:
            if isinstance(track, Track | Video | Album) and hasattr(track, "artists"):
                for artist in track.artists:
                    name = TrackInfoFormatter._get_artist_name(artist)
                    if name and name != "Unknown Artist":
                        all_artists.add(name)

        if all_artists:
            artist_links = [self._create_link("artist", name) for name in list(all_artists)[:5]]
            return ", ".join(artist_links)
        return "—"

    def _extract_playlist_release_date(self, playlist: Playlist | Mix) -> str:
        """Extract release date from playlist or its first track."""
        release_date = TrackInfoFormatter.format_date(getattr(playlist, "release_date", None))
        if release_date != "N/A":
            return release_date

        if hasattr(playlist, "tracks") and isinstance(playlist.tracks, list | Iterable):
            for track in playlist.tracks:
                if isinstance(track, Track | Video | Album) and hasattr(track, "album"):
                    release_date = TrackInfoFormatter.format_date(getattr(track.album, "release_date", None))
                    if release_date and release_date != "N/A":
                        return release_date
        return "N/A"

    def _populate_playlist_details(self, playlist: Playlist | Mix) -> None:
        """Populate details for a Playlist or Mix.

        Args:
            playlist (Playlist | Mix): The playlist or mix object.
        """
        # Title and version
        title = name_builder_title(playlist)
        self.lbl_title.setText(self._create_link("playlist", title))
        version = getattr(playlist, "version", None)
        self.lbl_version.setText(safe_str(version))

        # Artists
        artists_html = self._extract_playlist_artists(playlist)
        self.lbl_artists.setText(artists_html)

        # Album name (playlist title)
        album_name = getattr(playlist, "name", None)
        self.lbl_album.setText(self._create_link("playlist", album_name))

        # Codec & Bitrate
        self.lbl_codec.setText("—")
        self.lbl_bitrate.setText("—")

        # Duration
        duration = TrackInfoFormatter.format_duration(getattr(playlist, "duration", None))
        self.lbl_duration.setText(safe_str(duration))

        # Release date
        release_date = self._extract_playlist_release_date(playlist)
        self.lbl_release_date.setText(safe_str(release_date))

        # Popularity
        popularity = getattr(playlist, "popularity", None)
        self.lbl_popularity.setText(safe_str(popularity))

        self.lbl_isrc.setText("—")

    def _extract_artist_album_name(self, artist: Artist) -> str | None:
        """Extract first album name from artist's albums."""
        if not hasattr(artist, "albums") or not isinstance(artist.albums, list | Iterable):
            return None

        for album in artist.albums:
            if isinstance(album, Album) and hasattr(album, "name"):
                return getattr(album, "name", None)
        return None

    def _calculate_artist_total_duration(self, artist: Artist) -> int:
        """Calculate total duration of all artist's albums."""
        if not hasattr(artist, "albums") or not isinstance(artist.albums, list | Iterable):
            return 0

        total_duration = 0
        for album in artist.albums:
            if isinstance(album, Album) and hasattr(album, "duration"):
                album_duration = album.duration
                if isinstance(album_duration, int | float):
                    total_duration += album_duration
        return total_duration

    def _extract_artist_release_date(self, artist: Artist) -> str | None:
        """Extract release date from artist's first album."""
        if not hasattr(artist, "albums") or not isinstance(artist.albums, list | Iterable):
            return None

        for album in artist.albums:
            if isinstance(album, Album) and hasattr(album, "release_date"):
                release_date = TrackInfoFormatter.format_date(getattr(album, "release_date", None))
                if release_date and release_date != "N/A":
                    return release_date
        return None

    def _populate_artist_details(self, artist: Artist) -> None:
        """Populate details for an Artist.

        Args:
            artist (Artist): The artist object.
        """
        # Name
        name = getattr(artist, "name", None)
        self.lbl_title.setText(self._create_link("artist", name))

        # Version
        version = None
        if hasattr(artist, "type"):
            version = getattr(artist.type, "name", None)
        elif hasattr(artist, "role"):
            version = getattr(artist.role, "name", None)
        self.lbl_version.setText(safe_str(version))

        # Artists
        self.lbl_artists.setText("—")

        # Album name
        album_name = self._extract_artist_album_name(artist)
        self.lbl_album.setText(self._create_link("album", album_name))

        # Codec & Bitrate
        self.lbl_codec.setText("—")
        self.lbl_bitrate.setText("—")

        # Duration
        total_duration = self._calculate_artist_total_duration(artist)
        duration = TrackInfoFormatter.format_duration(total_duration)
        self.lbl_duration.setText(safe_str(duration))

        # Release date
        release_date = self._extract_artist_release_date(artist)
        self.lbl_release_date.setText(safe_str(release_date))

        # Popularity
        popularity = getattr(artist, "popularity", None)
        self.lbl_popularity.setText(safe_str(popularity))

        self.lbl_isrc.setText("—")
