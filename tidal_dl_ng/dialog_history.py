"""
dialog_history.py

Dialog for viewing and managing download history.
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from tidal_dl_ng.history import HistoryService
from tidal_dl_ng.logger import logger_gui


class DialogHistory(QtWidgets.QDialog):
    """Dialog for managing download history.

    Displays tracks grouped by source (album, playlist, mix) with ability to:
    - View download dates and source information
    - Export/Import history
    - Clear history or remove selected items
    - View statistics
    """

    def __init__(self, history_service: HistoryService, parent=None):
        """Initialize the history dialog.

        Args:
            history_service: The HistoryService instance.
            parent: Parent widget.
        """
        super().__init__(parent)

        # Import the generated UI
        from tidal_dl_ng.ui.dialog_history import Ui_DialogHistory

        self.ui = Ui_DialogHistory()
        self.ui.setupUi(self)
        self.history_service = history_service

        self._init_ui()
        self._connect_signals()
        self._load_history()

        self.exec()

    def _init_ui(self):
        """Initialize UI elements."""
        # Set file path
        file_path = self.history_service.get_history_file_path()
        self.ui.le_file_path.setText(file_path)

        # Configure tree widget
        self.ui.tw_history.setColumnWidth(0, 400)
        self.ui.tw_history.setColumnWidth(1, 100)
        self.ui.tw_history.setColumnWidth(2, 180)
        self.ui.tw_history.setColumnWidth(3, 100)

        # Set window size
        self.resize(900, 600)

    def _connect_signals(self):
        """Connect UI signals to handlers."""
        self.ui.pb_refresh.clicked.connect(self._load_history)
        self.ui.pb_export.clicked.connect(self._on_export)
        self.ui.pb_import.clicked.connect(self._on_import)
        self.ui.pb_clear_history.clicked.connect(self._on_clear_history)
        self.ui.pb_remove_selected.clicked.connect(self._on_remove_selected)
        self.ui.pb_close.clicked.connect(self.close)
        self.ui.pb_open_folder.clicked.connect(self._on_open_folder)

    def _load_history(self):
        """Load and display the download history."""
        # Clear existing items
        self.ui.tw_history.clear()

        # Get history grouped by source
        grouped_history = self.history_service.get_history_by_source()

        # Get statistics
        stats = self.history_service.get_statistics()
        self._update_statistics(stats)

        # Sort sources by name
        sorted_sources = sorted(grouped_history.items(), key=lambda x: x[0])

        # Populate tree
        for _, tracks in sorted_sources:
            if not tracks:
                continue

            # Create parent item for source
            source_item = self._create_source_item(tracks)
            self.ui.tw_history.addTopLevelItem(source_item)

            # Add tracks as children
            for track_data in sorted(tracks, key=lambda x: x.get("download_date", ""), reverse=True):
                track_item = self._create_track_item(track_data)
                source_item.addChild(track_item)

        # Expand all top-level items
        self.ui.tw_history.expandAll()

        logger_gui.info(f"Loaded {stats['total_tracks']} tracks from history")

    def _create_source_item(self, tracks: list) -> QtWidgets.QTreeWidgetItem:
        """Create a tree widget item for a source.

        Args:
            tracks: List of track data dictionaries.

        Returns:
            QTreeWidgetItem for the source.
        """
        if not tracks:
            return QtWidgets.QTreeWidgetItem()

        first_track = tracks[0]
        source_type = first_track.get("source_type", "unknown")
        source_name = first_track.get("source_name", "Unknown")
        source_id = first_track.get("source_id", "")

        # Format source name
        if source_type == "manual" or not source_name:
            display_name = f"📝 Manual Downloads ({len(tracks)} tracks)"
        elif source_type == "album":
            display_name = f"💿 {source_name} ({len(tracks)} tracks)"
        elif source_type == "playlist":
            display_name = f"📋 {source_name} ({len(tracks)} tracks)"
        elif source_type == "mix":
            display_name = f"🎵 {source_name} ({len(tracks)} tracks)"
        elif source_type == "track":
            display_name = f"🎼 Individual Tracks ({len(tracks)} tracks)"
        else:
            display_name = f"{source_name} ({len(tracks)} tracks)"

        item = QtWidgets.QTreeWidgetItem()
        item.setText(0, display_name)
        item.setText(1, source_type.capitalize())
        item.setText(2, "")
        item.setText(3, source_id or "")

        # Make it bold
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)

        return item

    def _create_track_item(self, track_data: dict) -> QtWidgets.QTreeWidgetItem:
        """Create a tree widget item for a track.

        Args:
            track_data: Dictionary with track information.

        Returns:
            QTreeWidgetItem for the track.
        """
        track_id = track_data.get("track_id", "")
        download_date = track_data.get("download_date", "")

        # Format date
        try:
            if download_date:
                dt = datetime.fromisoformat(download_date.replace("Z", "+00:00"))
                formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                formatted_date = "Unknown"
        except:
            formatted_date = download_date

        item = QtWidgets.QTreeWidgetItem()
        item.setText(0, f"   Track {track_id}")
        item.setText(1, "Track")
        item.setText(2, formatted_date)
        item.setText(3, track_id)

        # Store track ID for later use
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, track_id)

        return item

    def _update_statistics(self, stats: dict):
        """Update statistics labels.

        Args:
            stats: Dictionary with statistics.
        """
        total = stats.get("total_tracks", 0)
        by_type = stats.get("by_source_type", {})

        self.ui.l_total_tracks.setText(f"Total Tracks: {total}")
        self.ui.l_by_albums.setText(f"Albums: {by_type.get('album', 0)}")
        self.ui.l_by_playlists.setText(f"Playlists: {by_type.get('playlist', 0)}")
        self.ui.l_by_mixes.setText(f"Mixes: {by_type.get('mix', 0)}")
        self.ui.l_by_manual.setText(f"Manual: {by_type.get('manual', 0)}")

    def _on_export(self):
        """Handle export button click."""
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Download History", "download_history_export.json", "JSON Files (*.json)"
        )

        if file_path:
            success, message = self.history_service.export_history(file_path)

            if success:
                QtWidgets.QMessageBox.information(self, "Export Successful", message)
                logger_gui.info(f"Exported history to: {file_path}")
            else:
                QtWidgets.QMessageBox.critical(self, "Export Failed", f"Failed to export history:\n{message}")
                logger_gui.error(f"Export failed: {message}")

    def _on_import(self):
        """Handle import button click."""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import Download History", "", "JSON Files (*.json)")

        if not file_path:
            return

        # Ask merge or replace
        reply = QtWidgets.QMessageBox.question(
            self,
            "Import Mode",
            "Do you want to MERGE with existing history?\n\n"
            "Yes = Merge (add new tracks, keep existing)\n"
            "No = Replace (delete all existing, import only new)\n"
            "Cancel = Abort import",
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No
            | QtWidgets.QMessageBox.StandardButton.Cancel,
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Cancel:
            return

        merge = reply == QtWidgets.QMessageBox.StandardButton.Yes

        # Perform import
        success, message = self.history_service.import_history(file_path, merge=merge)

        if success:
            QtWidgets.QMessageBox.information(self, "Import Successful", message)
            logger_gui.info(f"Imported history from: {file_path}")
            self._load_history()  # Refresh display
        else:
            QtWidgets.QMessageBox.critical(self, "Import Failed", f"Failed to import history:\n{message}")
            logger_gui.error(f"Import failed: {message}")

    def _on_clear_history(self):
        """Handle clear history button click."""
        reply = QtWidgets.QMessageBox.warning(
            self,
            "Clear Download History",
            "Are you sure you want to clear ALL download history?\n\n" "This action cannot be undone!",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.history_service.clear_history()
            QtWidgets.QMessageBox.information(self, "History Cleared", "Download history has been cleared.")
            logger_gui.info("Download history cleared")
            self._load_history()  # Refresh display

    def _on_remove_selected(self):
        """Handle remove selected button click."""
        selected_items = self.ui.tw_history.selectedItems()

        if not selected_items:
            QtWidgets.QMessageBox.warning(self, "No Selection", "Please select one or more tracks to remove.")
            return

        # Collect track IDs from selected items (only child items, not parents)
        track_ids = []
        for item in selected_items:
            # Check if it's a track (child item) by checking if it has a parent
            if item.parent() is not None:
                track_id = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
                if track_id:
                    track_ids.append(track_id)

        if not track_ids:
            QtWidgets.QMessageBox.warning(
                self, "No Tracks Selected", "Please select individual tracks (not source groups) to remove."
            )
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "Remove Tracks",
            f"Are you sure you want to remove {len(track_ids)} track(s) from history?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            removed_count = 0
            for track_id in track_ids:
                if self.history_service.remove_track_from_history(track_id):
                    removed_count += 1

            QtWidgets.QMessageBox.information(self, "Tracks Removed", f"Removed {removed_count} track(s) from history.")
            logger_gui.info(f"Removed {removed_count} tracks from history")
            self._load_history()  # Refresh display

    def _on_open_folder(self):
        """Open the folder containing the history file."""
        file_path = Path(self.history_service.get_history_file_path())
        folder_path = file_path.parent

        try:
            if sys.platform == "win32":
                os.startfile(folder_path)  # noqa: S606
            elif sys.platform == "darwin":
                # Security: folder_path is from config, not user input
                subprocess.run(["open", str(folder_path)], check=False)  # noqa: S603, S607
            else:
                # Security: folder_path is from config, not user input
                subprocess.run(["xdg-open", str(folder_path)], check=False)  # noqa: S603, S607

            logger_gui.info(f"Opened folder: {folder_path}")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Cannot Open Folder", f"Failed to open folder:\n{e!s}")
            logger_gui.error(f"Failed to open folder: {e}")
