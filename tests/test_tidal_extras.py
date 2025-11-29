import mutagen
import pytest

from tidal_dl_ng.helper.tidal import (
    _normalize_contributors,
    extract_contributor_names,
    parse_track_and_album_extras,
)
from tidal_dl_ng.metadata import Metadata


def test_normalize_contributors_dict_shape():
    raw = {
        "producer": [{"name": "Prod A"}, {"name": "Prod B", "foo": "bar"}],
        "composer": [{"name": "Comp 1"}],
        "invalid": ["x", {"no_name": True}],
    }

    result = _normalize_contributors(raw)

    assert set(result.keys()) == {"producer", "composer"}
    assert result["producer"] == ["Prod A", "Prod B"]
    assert result["composer"] == ["Comp 1"]


def test_normalize_contributors_list_shape():
    raw = [
        {"name": "Prod A", "role": "producer"},
        {"name": "Comp 1", "role": "composer"},
        {"name": "Bad", "role": ""},
        "oops",
    ]

    result = _normalize_contributors(raw)

    assert set(result.keys()) == {"producer", "composer"}
    assert result["producer"] == ["Prod A"]
    assert result["composer"] == ["Comp 1"]


def test_parse_track_and_album_extras_full():
    track_json = {
        "bpm": 123,
        "contributors": {
            "producer": [{"name": "Prod A"}],
            "composer": [{"name": "Comp 1"}],
            "lyricist": [{"name": "Writer"}],
        },
    }
    album_json = {
        "label": "Test Label",
        "genres": [{"name": "Rock"}, {"name": "Indie"}],
    }

    extras = parse_track_and_album_extras(track_json, album_json)

    assert extras["bpm"] == 123
    assert extras["label"] == "Test Label"
    assert extras["genres"] == ["Rock", "Indie"]
    assert extras["contributors_by_role"]["producer"] == ["Prod A"]


def test_parse_track_and_album_extras_missing_fields():
    extras = parse_track_and_album_extras({}, {})

    assert extras["bpm"] is None
    assert extras["label"] == ""
    assert extras["genres"] == []
    assert extras["contributors_by_role"] == {}


@pytest.mark.parametrize(
    "role,expected",
    [
        ("producer", "Prod A, Prod B"),
        ("composer", "Comp 1"),
        ("lyricist", ""),
    ],
)
def test_extract_contributor_names(role, expected):
    contributors = {
        "producer": ["Prod A", "Prod B"],
        "composer": ["Comp 1"],
    }

    names = extract_contributor_names(contributors, role, delimiter=", ")

    assert names == expected


def test_metadata_enriched_tags_flac(tmp_path):
    # Create a valid minimal FLAC file using soundfile
    path = tmp_path / "test.flac"

    # Import numpy and soundfile to create a minimal valid FLAC
    try:
        import numpy as np
        import soundfile as sf

        # Create 1 second of silence at 44100 Hz
        silence = np.zeros((44100, 2), dtype=np.float32)
        sf.write(str(path), silence, 44100, format="FLAC")
    except ImportError:
        # Fallback: skip this test if soundfile not available
        import pytest

        pytest.skip("soundfile required for FLAC test")

    m = Metadata(
        path_file=path,
        target_upc={"FLAC": "UPC", "MP3": "UPC", "MP4": "UPC"},
        title="Title",
        album="Album",
        artists="Artist1, Artist2",
        albumartist="AlbumArtist",
        genre="Rock, Indie",
        label="Test Label",
        bpm=120,
        producers="Prod A, Prod B",
        composers_detailed="Comp 1, Comp 2",
        lyricists="Writer 1, Writer 2",
    )

    m.save()

    audio_out = mutagen.flac.FLAC(path)

    assert audio_out["TITLE"][0] == "Title"
    assert audio_out["ALBUM"][0] == "Album"
    assert audio_out["ARTIST"][0] == "Artist1, Artist2"
    assert audio_out["ALBUMARTIST"][0] == "AlbumArtist"
    assert audio_out["GENRE"][0] == "Rock, Indie"
    assert audio_out["LABEL"][0] == "Test Label"
    assert audio_out["BPM"][0] == "120"
    assert audio_out["PRODUCER"][0] == "Prod A, Prod B"
    assert audio_out["LYRICIST"][0] == "Writer 1, Writer 2"
    assert audio_out["COMPOSER"][0] == "Comp 1, Comp 2"
