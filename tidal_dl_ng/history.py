"""
history.py

Implements the download history tracking service with JSON persistence.

Classes:
    HistoryService: Main service for managing download history with atomic JSON operations.
"""

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from tidal_dl_ng.helper.decorator import SingletonMeta
from tidal_dl_ng.helper.path import path_config_base


class HistoryFormatError(TypeError):
    """Exception raised when history file format is invalid."""

    def __init__(self) -> None:
        """Initialize with predefined message."""
        super().__init__("Invalid history file format")


@dataclass
class DownloadHistoryEntry:
    """Represents a single entry in the download history.

    Attributes:
        source_type: Type of source (playlist, album, manual, mix).
        source_id: ID of the source (UUID or None for manual).
        source_name: Name of the source (playlist name, album name, etc.).
        download_date: ISO 8601 timestamp of download.
    """

    source_type: str
    source_id: str | None
    source_name: str | None
    download_date: str


class HistoryService(metaclass=SingletonMeta):
    """Service for managing download history with JSON persistence.

    This service provides thread-safe operations for tracking downloaded tracks.
    The history is stored in a track-centric JSON file (trackId -> metadata).
    All write operations are atomic to prevent corruption.

    Attributes:
        history_data: In-memory dictionary of track IDs to history entries.
        file_path: Path to the JSON history file.
        _lock: Thread lock for concurrent access safety.
    """

    SCHEMA_VERSION = 1

    def __init__(self):
        """Initialize the history service and load existing data."""
        self.file_path: Path = Path(path_config_base()) / "downloaded_history.json"
        self.history_data: dict[str, dict[str, Any]] = {}
        self.settings_data: dict[str, Any] = {"preventDuplicates": True}
        self._lock: Lock = Lock()
        self._load_history()

    def _load_history(self) -> None:
        """Load history from JSON file.

        If the file doesn't exist, creates a new empty history.
        If the file is corrupted, backs it up and starts fresh.
        Thread-safe operation.
        """
        with self._lock:
            try:
                if not self.file_path.exists():
                    # Create directory if needed
                    self.file_path.parent.mkdir(parents=True, exist_ok=True)
                    # Initialize with empty schema
                    self._save_history_internal()
                    return

                with open(self.file_path, encoding="utf-8") as f:
                    data = json.load(f)

                if not isinstance(data, dict):
                    raise HistoryFormatError

                settings = data.get("settings", {})
                self.settings_data = {"preventDuplicates": bool(settings.get("preventDuplicates", True))}

                tracks_section = data.get("tracks")
                if isinstance(tracks_section, dict):
                    self.history_data = tracks_section
                else:
                    self.history_data = {k: v for k, v in data.items() if not k.startswith("_") and k != "settings"}

            except (json.JSONDecodeError, ValueError, FileNotFoundError):
                # Backup corrupted file
                if self.file_path.exists():
                    backup_path = self.file_path.with_suffix(".json.bak")
                    counter = 1
                    while backup_path.exists():
                        backup_path = self.file_path.with_suffix(f".json.bak.{counter}")
                        counter += 1
                    shutil.copy2(self.file_path, backup_path)
                    print(f"Warning: Download history file was corrupted. Backup saved to: {backup_path}")

                # Start with empty history
                self.history_data = {}
                self.settings_data = {"preventDuplicates": True}
                self._save_history_internal()

    def _save_history_internal(self) -> None:
        """Internal method to save history to JSON file atomically.

        Uses atomic write (write to temp file, then rename) to prevent corruption.
        Assumes lock is already held by caller.
        """
        try:
            # Ensure directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            # Prepare data with metadata
            data_to_save = {
                "_schema_version": self.SCHEMA_VERSION,
                "_last_updated": datetime.now(UTC).isoformat(),
                "settings": self.settings_data,
                "tracks": self.history_data,
            }

            # Atomic write: write to temp file, then rename
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.file_path.parent, delete=False, suffix=".tmp"
            ) as tmp_file:
                json.dump(data_to_save, tmp_file, indent=2, ensure_ascii=False)
                tmp_path = tmp_file.name

            # Atomic rename (on Windows, need to remove target first if exists)
            if os.name == "nt" and self.file_path.exists():
                os.replace(tmp_path, self.file_path)
            else:
                os.rename(tmp_path, self.file_path)

        except Exception:
            # Clean up temp file if it exists
            if "tmp_path" in locals() and os.path.exists(tmp_path):
                from contextlib import suppress

                with suppress(OSError):
                    os.remove(tmp_path)
            raise

    def save_history(self) -> None:
        """Public method to save history (with lock acquisition)."""
        with self._lock:
            self._save_history_internal()

    def get_settings(self) -> dict[str, Any]:
        """Return a copy of history-related settings."""
        with self._lock:
            return dict(self.settings_data)

    def update_settings(self, **kwargs: Any) -> None:
        """Update history settings and persist immediately."""
        with self._lock:
            for key, value in kwargs.items():
                if key in self.settings_data:
                    self.settings_data[key] = bool(value)
            self._save_history_internal()

    def should_skip_download(self, track_id: str) -> bool:
        """Return True if track should be skipped based on history and settings."""
        with self._lock:
            prevent_duplicates = self.settings_data.get("preventDuplicates", True)
            return prevent_duplicates and track_id in self.history_data

    def is_downloaded(self, track_id: str) -> bool:
        """Check if a track has been downloaded.

        Args:
            track_id: The TIDAL track ID to check.

        Returns:
            True if track is in download history, False otherwise.
        """
        with self._lock:
            return track_id in self.history_data

    def add_track_to_history(
        self, track_id: str, source_type: str = "manual", source_id: str | None = None, source_name: str | None = None
    ) -> None:
        """Add a track to download history.

        Args:
            track_id: The TIDAL track ID.
            source_type: Type of source (playlist, album, manual, mix, track).
            source_id: ID of the source (UUID for playlist/album, None for manual).
            source_name: Name of the source (for display purposes).
        """
        with self._lock:
            self.history_data[track_id] = {
                "sourceType": source_type,
                "sourceId": source_id,
                "sourceName": source_name,
                "downloadDate": datetime.now(UTC).isoformat(),
            }
            # Save immediately to persist
            self._save_history_internal()

    def remove_track_from_history(self, track_id: str) -> bool:
        """Remove a track from download history.

        Args:
            track_id: The TIDAL track ID to remove.

        Returns:
            True if track was removed, False if not found.
        """
        with self._lock:
            if track_id in self.history_data:
                del self.history_data[track_id]
                self._save_history_internal()
                return True
            return False

    def get_history_by_source(self) -> dict[str, list[dict[str, Any]]]:
        """Transform track-centric history to source-centric view.

        Returns:
            Dictionary grouped by source with format:
            {
                "source_key": [
                    {
                        "track_id": "123",
                        "download_date": "2025-11-15T...",
                        ...
                    }
                ]
            }
            where source_key is "{sourceType}_{sourceId}" or "manual" for manual downloads.
        """
        with self._lock:
            grouped: dict[str, list[dict[str, Any]]] = {}

            for track_id, entry in self.history_data.items():
                source_type = entry.get("sourceType", "manual")
                source_id = entry.get("sourceId")
                source_name = entry.get("sourceName", "Unknown")

                # Create source key
                source_key = f"{source_type}_{source_id}" if source_id else f"{source_type}_manual"

                # Initialize list if needed
                if source_key not in grouped:
                    grouped[source_key] = []

                # Add track info
                grouped[source_key].append(
                    {
                        "track_id": track_id,
                        "source_type": source_type,
                        "source_id": source_id,
                        "source_name": source_name,
                        "download_date": entry.get("downloadDate", ""),
                    }
                )

            return grouped

    def get_track_info(self, track_id: str) -> dict[str, Any] | None:
        """Get download history info for a specific track.

        Args:
            track_id: The TIDAL track ID.

        Returns:
            Dictionary with history entry or None if not found.
        """
        with self._lock:
            return self.history_data.get(track_id)

    def get_history_file_path(self) -> str:
        """Get the absolute path to the history file.

        Returns:
            Absolute path as string.
        """
        return str(self.file_path.absolute())

    def _extract_tracks_from_data(self, data: dict) -> dict:
        """Extract tracks from import data.

        Args:
            data: Import data dictionary.

        Returns:
            Dictionary of tracks.
        """
        tracks_node = data.get("tracks")
        if isinstance(tracks_node, dict):
            return tracks_node
        return {k: v for k, v in data.items() if not k.startswith("_") and k != "settings"}

    def _validate_tracks(self, tracks: dict) -> tuple[bool, str]:
        """Validate track entries.

        Args:
            tracks: Dictionary of tracks to validate.

        Returns:
            Tuple of (valid, error_message).
        """
        required_keys = {"sourceType", "downloadDate"}
        for track_id, entry in tracks.items():
            if not isinstance(entry, dict):
                return False, f"Invalid entry format for track {track_id}"
            if not required_keys.issubset(entry.keys()):
                return False, f"Missing required fields for track {track_id}"
        return True, ""

    def import_history(self, file_path: str, merge: bool = True) -> tuple[bool, str]:
        """Import history from an external JSON file.

        Args:
            file_path: Path to the JSON file to import.
            merge: If True, merge with existing history. If False, replace.

        Returns:
            Tuple of (success: bool, message: str).
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON file: {e!s}"
        except Exception as e:
            return False, f"Import failed: {e!s}"
        else:
            # Validate format
            if not isinstance(data, dict):
                return False, "Invalid file format: expected JSON object"

            # Extract and validate
            imported_settings = data.get("settings", {})
            imported_tracks = self._extract_tracks_from_data(data)

            valid, error_msg = self._validate_tracks(imported_tracks)
            if not valid:
                return False, error_msg

            # Apply import
            with self._lock:
                if merge:
                    self.history_data.update(imported_tracks)
                    message = f"Successfully merged {len(imported_tracks)} tracks"
                else:
                    self.history_data = imported_tracks
                    message = f"Successfully imported {len(imported_tracks)} tracks (replaced existing)"

                if isinstance(imported_settings, dict) and "preventDuplicates" in imported_settings:
                    self.settings_data["preventDuplicates"] = bool(imported_settings.get("preventDuplicates", True))

                self._save_history_internal()

            return True, message

    def export_history(self, file_path: str) -> tuple[bool, str]:
        """Export history to an external JSON file.

        Args:
            file_path: Destination path for the exported JSON file.

        Returns:
            Tuple of (success: bool, message: str).
        """
        try:
            with self._lock:
                # Prepare export data (same format as internal storage)
                data_to_export = {
                    "_schema_version": self.SCHEMA_VERSION,
                    "_exported_date": datetime.now(UTC).isoformat(),
                    "_total_tracks": len(self.history_data),
                    "settings": self.settings_data,
                    "tracks": self.history_data,
                }

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data_to_export, f, indent=2, ensure_ascii=False)

                return True, f"Successfully exported {len(self.history_data)} tracks"

        except Exception as e:
            return False, f"Export failed: {e!s}"

    def clear_history(self) -> None:
        """Clear all download history.

        This is a destructive operation - use with caution.
        """
        with self._lock:
            self.history_data = {}
            self._save_history_internal()

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about the download history.

        Returns:
            Dictionary with statistics (total tracks, by source type, etc.).
        """
        with self._lock:
            stats = {
                "total_tracks": len(self.history_data),
                "by_source_type": {},
                "oldest_download": None,
                "newest_download": None,
            }

            dates = []
            for entry in self.history_data.values():
                source_type = entry.get("sourceType", "unknown")
                stats["by_source_type"][source_type] = stats["by_source_type"].get(source_type, 0) + 1

                download_date = entry.get("downloadDate")
                if download_date:
                    dates.append(download_date)

            if dates:
                stats["oldest_download"] = min(dates)
                stats["newest_download"] = max(dates)

            return stats
