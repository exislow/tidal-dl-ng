from dataclasses import dataclass

from dataclasses_json import dataclass_json
from tidalapi import Quality

from tidal_dl_ng.constants import CoverDimensions, QualityVideo, SkipExisting


@dataclass_json
@dataclass
class Settings:
    skip_existing: SkipExisting = SkipExisting.Disabled
    # TODO: Implement cover download to a separate file.
    # album_cover_save: bool = True
    lyrics_embed: bool = False
    lyrics_file: bool = False
    # TODO: Implement API KEY selection.
    # api_key_index: bool = 0
    # TODO: Implement album info download to separate file.
    # album_info_save: bool = False
    video_download: bool = True
    # TODO: Implement multi threading for downloads.
    # multi_thread: bool = False
    download_delay: bool = True
    download_base_path: str = "~/download"
    quality_audio: Quality = Quality.low_320k
    quality_video: QualityVideo = QualityVideo.P480
    format_album: str = "Albums/{artist_name} - {album_title}/{track_num}. {artist_name} - {track_title}"
    format_playlist: str = "Playlists/{playlist_name}/{artist_name} - {track_title}"
    format_mix: str = "Mix/{mix_name}/{artist_name} - {track_title}"
    format_track: str = "Tracks/{artist_name} - {track_title}"
    format_video: str = "Videos/{artist_name} - {track_title}"
    video_convert_mp4: bool = True
    metadata_cover_dimension: CoverDimensions = CoverDimensions.Px320


@dataclass_json
@dataclass
class HelpSettings:
    skip_existing: str = (
        "Do not download, if file already exists. Possible option false = do not skip, "
        "'exact' = if filename already exists, 'extension_ignore' = skip even if a file with a "
        "different file extension exists."
    )
    album_cover_save: str = "Safe cover to album folder."
    lyrics_embed: str = "Embed lyrics in audio file."
    lyrics_file: str = "Save lyrics to separate *.lrc file."
    api_key_index: str = "Set the device API KEY."
    album_info_save: str = "Save album info to track?"
    video_download: str = "Allow download of videos."
    multi_thread: str = "Download several tracks in parallel."
    download_delay: str = "Activate randomized download delay to mimic human behaviour."
    download_base_path: str = "Where to store the downloaded media."
    quality_audio: str = (
        'Desired audio download quality: "LOW" (96kbps), "HIGH" (320kbps), '
        '"LOSSLESS" (16 Bit, 44,1 kHz), '
        '"HI_RES" (MQA 24 Bit, 96 kHz), "HI_RES_LOSSLESS" (up to 24 Bit, 192 kHz)'
    )
    quality_video: str = 'Desired video download quality: "360", "480", "720", "1080"'
    # TODO: Describe possible variables.
    format_album: str = "Where to download albums and how to name the items."
    format_playlist: str = "Where to download playlists and how to name the items."
    format_mix: str = "Where to download mixes and how to name the items."
    format_track: str = "Where to download tracks and how to name the items."
    format_video: str = "Where to download videos and how to name the items."
    video_convert_mp4: str = (
        "Videos are downloaded as MPEG Transport Stream (TS) files. With this option each video "
        "will be converted to MP4. FFMPEG must be installed and added to your 'PATH' variable."
    )
    metadata_cover_dimension: str = (
        "The dimensions of the cover image embedded into the track. Possible values: 320x320, 640x640x 1280x1280."
    )


@dataclass_json
@dataclass
class Token:
    token_type: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    expiry_time: float = 0.0
