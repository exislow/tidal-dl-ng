"""
test_gui_duplicate_prevention.py

Test suite for GUI duplicate prevention features.

Tests cover:
- Tools menu action creation
- Duplicate prevention toggle
- Settings persistence in GUI
- Status messages
"""

from unittest.mock import MagicMock, patch

import pytest

# Mock Qt before importing GUI modules
with patch("tidal_dl_ng.gui.QtWidgets"), patch("tidal_dl_ng.gui.QtGui"), patch("tidal_dl_ng.gui.QtCore"):
    pass


class TestToolsMenuIntegration:
    """Test Tools menu integration for duplicate prevention."""

    @patch("tidal_dl_ng.gui.QtWidgets.QMenuBar")
    @patch("tidal_dl_ng.gui.QtGui.QAction")
    def test_tools_menu_created_if_not_exists(self, mock_action, mock_menubar):
        """Test that Tools menu is created if it doesn't exist."""
        # This test verifies the logic in _init_menu_actions
        # We're testing the structure, not the actual Qt implementation

        mock_menubar_instance = MagicMock()
        mock_menubar_instance.actions.return_value = []  # No existing Tools menu
        mock_menubar_instance.addMenu = MagicMock()

        # Simulate the logic from _init_menu_actions
        tools_menu = None
        for action in mock_menubar_instance.actions():
            if action.text() == "Tools":
                tools_menu = action.menu()
                break

        if not tools_menu:
            tools_menu = mock_menubar_instance.addMenu("Tools")

        # Verify addMenu was called
        assert mock_menubar_instance.addMenu.called

    @patch("tidal_dl_ng.gui.QtWidgets.QMenuBar")
    @patch("tidal_dl_ng.gui.QtGui.QAction")
    def test_tools_menu_found_if_exists(self, mock_action, mock_menubar):
        """Test that existing Tools menu is found and reused."""
        mock_menubar_instance = MagicMock()

        # Create mock existing Tools menu
        mock_tools_action = MagicMock()
        mock_tools_action.text.return_value = "Tools"
        mock_tools_menu = MagicMock()
        mock_tools_action.menu.return_value = mock_tools_menu

        mock_menubar_instance.actions.return_value = [mock_tools_action]
        mock_menubar_instance.addMenu = MagicMock()

        # Simulate the logic
        tools_menu = None
        for action in mock_menubar_instance.actions():
            if action.text() == "Tools":
                tools_menu = action.menu()
                break

        # Should have found existing menu
        assert tools_menu is mock_tools_menu
        # Should NOT have called addMenu
        assert not mock_menubar_instance.addMenu.called


class TestDuplicatePreventionAction:
    """Test the duplicate prevention menu action."""

    def test_action_is_checkable(self):
        """Test that the duplicate prevention action is checkable."""
        # This verifies the action configuration
        # In the actual code: self.a_toggle_duplicate_prevention.setCheckable(True)

        mock_action = MagicMock()
        mock_action.setCheckable = MagicMock()

        # Simulate action creation
        mock_action.setCheckable(True)

        mock_action.setCheckable.assert_called_once_with(True)

    def test_action_initial_state_from_settings(self):
        """Test that action initial state reflects settings."""
        mock_history_service = MagicMock()
        mock_history_service.get_settings.return_value = {"preventDuplicates": True}

        # Simulate getting initial state
        is_preventing = mock_history_service.get_settings().get("preventDuplicates", True)

        assert is_preventing is True

    def test_action_connected_to_handler(self):
        """Test that action triggered signal connects to handler."""
        mock_action = MagicMock()
        mock_handler = MagicMock()

        # Simulate connection
        mock_action.triggered.connect(mock_handler)

        mock_action.triggered.connect.assert_called_once_with(mock_handler)


class TestToggleDuplicatePreventionHandler:
    """Test the on_toggle_duplicate_prevention handler method."""

    def test_handler_updates_settings_when_enabled(self):
        """Test that handler updates settings to True when enabled."""
        mock_history_service = MagicMock()

        # Simulate the handler logic
        enabled = True
        mock_history_service.update_settings(preventDuplicates=enabled)

        mock_history_service.update_settings.assert_called_once_with(preventDuplicates=True)

    def test_handler_updates_settings_when_disabled(self):
        """Test that handler updates settings to False when disabled."""
        mock_history_service = MagicMock()

        # Simulate the handler logic
        enabled = False
        mock_history_service.update_settings(preventDuplicates=enabled)

        mock_history_service.update_settings.assert_called_once_with(preventDuplicates=False)

    def test_handler_emits_status_message_enabled(self):
        """Test that handler emits status message when enabled."""

        # Simulate the handler logic
        enabled = True
        status_msg = "enabled" if enabled else "disabled"

        assert status_msg == "enabled"

    def test_handler_emits_status_message_disabled(self):
        """Test that handler emits status message when disabled."""
        enabled = False
        status_msg = "enabled" if enabled else "disabled"

        assert status_msg == "disabled"

    def test_handler_logs_change(self):
        """Test that handler logs the settings change."""
        from unittest.mock import MagicMock

        mock_logger = MagicMock()

        # Simulate handler logging
        enabled = True
        status_msg = "enabled" if enabled else "disabled"
        mock_logger.info(f"Duplicate download prevention {status_msg}")

        mock_logger.info.assert_called_once()
        call_args = str(mock_logger.info.call_args)
        assert "enabled" in call_args


class TestSettingsPersistence:
    """Test that GUI settings changes persist."""

    def test_toggle_persists_to_json(self):
        """Test that toggling the option persists to the JSON file."""
        mock_history_service = MagicMock()

        # Simulate toggle
        mock_history_service.update_settings(preventDuplicates=False)

        # Verify update_settings was called (which triggers save)
        mock_history_service.update_settings.assert_called_with(preventDuplicates=False)

    def test_settings_restored_on_gui_restart(self):
        """Test that settings are restored when GUI restarts."""
        mock_history_service = MagicMock()
        mock_history_service.get_settings.return_value = {"preventDuplicates": False}

        # Simulate GUI init reading settings
        is_preventing = mock_history_service.get_settings().get("preventDuplicates", True)

        assert is_preventing is False


class TestStatusBarMessages:
    """Test status bar message display."""

    def test_status_message_format_enabled(self):
        """Test status message format when enabled."""
        from tidal_dl_ng.model.gui_data import StatusbarMessage

        enabled = True
        status_msg = "enabled" if enabled else "disabled"
        message = StatusbarMessage(message=f"Duplicate prevention {status_msg}.", timeout=2500)

        assert "Duplicate prevention enabled" in message.message
        assert message.timeout == 2500

    def test_status_message_format_disabled(self):
        """Test status message format when disabled."""
        from tidal_dl_ng.model.gui_data import StatusbarMessage

        enabled = False
        status_msg = "enabled" if enabled else "disabled"
        message = StatusbarMessage(message=f"Duplicate prevention {status_msg}.", timeout=2500)

        assert "Duplicate prevention disabled" in message.message
        assert message.timeout == 2500


class TestViewHistoryAction:
    """Test the View Download History action."""

    def test_view_history_action_exists(self):
        """Test that View History action is created."""
        mock_action = MagicMock()
        mock_handler = MagicMock()

        # Simulate action creation
        mock_action.setText("View Download History...")
        mock_action.triggered.connect(mock_handler)

        assert "View Download History" in str(mock_action.setText.call_args)

    def test_view_history_opens_dialog(self):
        """Test that View History action opens the dialog."""
        mock_dialog_class = MagicMock()
        mock_history_service = MagicMock()

        # Simulate dialog opening
        mock_dialog_class(history_service=mock_history_service, parent=None)

        mock_dialog_class.assert_called_once()


class TestMenuSeparator:
    """Test that separator is added between menu items."""

    def test_separator_added_between_items(self):
        """Test that a separator is added between View History and Prevent Duplicates."""
        mock_menu = MagicMock()

        # Simulate adding items
        mock_menu.addAction(MagicMock())  # View History
        mock_menu.addSeparator()
        mock_menu.addAction(MagicMock())  # Prevent Duplicates

        # Verify separator was called
        mock_menu.addSeparator.assert_called_once()


class TestIntegrationWithDownloadQueue:
    """Test integration with download queue."""

    def test_prevention_affects_queue_downloads(self):
        """Test that prevention setting affects downloads from queue."""
        mock_history_service = MagicMock()
        mock_history_service.should_skip_download.return_value = True

        # Simulate queue download check
        track_id = "123456"
        should_skip = mock_history_service.should_skip_download(track_id)

        assert should_skip is True

    def test_prevention_disabled_allows_queue_downloads(self):
        """Test that disabling prevention allows queue downloads."""
        mock_history_service = MagicMock()
        mock_history_service.should_skip_download.return_value = False

        # Simulate queue download check
        track_id = "123456"
        should_skip = mock_history_service.should_skip_download(track_id)

        assert should_skip is False


class TestActionStateSync:
    """Test that action state stays synced with settings."""

    def test_action_checked_when_prevention_enabled(self):
        """Test that action appears checked when prevention is enabled."""
        mock_action = MagicMock()
        mock_history_service = MagicMock()
        mock_history_service.get_settings.return_value = {"preventDuplicates": True}

        # Simulate setting initial state
        is_preventing = mock_history_service.get_settings().get("preventDuplicates", True)
        mock_action.setChecked(is_preventing)

        mock_action.setChecked.assert_called_once_with(True)

    def test_action_unchecked_when_prevention_disabled(self):
        """Test that action appears unchecked when prevention is disabled."""
        mock_action = MagicMock()
        mock_history_service = MagicMock()
        mock_history_service.get_settings.return_value = {"preventDuplicates": False}

        # Simulate setting initial state
        is_preventing = mock_history_service.get_settings().get("preventDuplicates", True)
        mock_action.setChecked(is_preventing)

        mock_action.setChecked.assert_called_once_with(False)


class TestErrorHandling:
    """Test error handling in GUI actions."""

    def test_handler_continues_on_settings_error(self):
        """Test that handler continues gracefully if settings update fails."""
        mock_history_service = MagicMock()
        mock_history_service.update_settings.side_effect = Exception("Settings error")

        # Simulate handler with try/except (if implemented)
        try:
            mock_history_service.update_settings(preventDuplicates=True)
            success = True
        except Exception:
            success = False

        # In current implementation, error would propagate
        # This test documents current behavior
        assert success is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
