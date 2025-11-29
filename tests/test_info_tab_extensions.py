from unittest.mock import patch


def test_new_fields_initial_state(info_tab_widget, qt_app):
    """New fields must exist and default to '—'."""
    assert hasattr(info_tab_widget, "lbl_track_number")
    assert info_tab_widget.lbl_track_number.text() == "—"
    assert hasattr(info_tab_widget, "lbl_bpm")
    assert info_tab_widget.lbl_bpm.text() == "—"
    # Note: lbl_label, lbl_genres, lbl_producers and lbl_composers are not available
    # as these fields cannot be retrieved from TIDAL API


def test_bpm_population(info_tab_widget, mock_track, qt_app):
    """Ensure BPM field is populated when present."""
    # Add BPM attribute to mock_track
    mock_track.bpm = 120

    with patch("tidal_dl_ng.ui.info_tab_widget.name_builder_title", return_value="Test Track"):
        info_tab_widget._populate_track_details(mock_track)
        qt_app.processEvents()

        # Expect loading indicator first due to async extras
        assert info_tab_widget.lbl_bpm.text() == "⏳ Loading..."
        # Simulate async arrival of extras
        info_tab_widget._update_extras_ui({"bpm": 120})
        qt_app.processEvents()
        assert info_tab_widget.lbl_bpm.text() == "120"
