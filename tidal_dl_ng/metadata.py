import pathlib

import mutagen
from mutagen import flac, id3, mp4
from mutagen.id3 import APIC, TALB, TCOM, TCOP, TDRC, TIT2, TOPE, TPE1, TRCK, TSRC, TXXX, USLT, WOAS


class Metadata:
    path_file: str | pathlib.Path
    title: str
    album: str
    albumartist: str
    artists: str
    copy_right: str
    tracknumber: int
    discnumber: int
    totaldisc: int
    totaltrack: int
    date: str
    composer: str
    isrc: str
    lyrics: str
    path_cover: str
    cover_data: bytes
    album_replay_gain: float
    album_peak_amplitude: float
    track_replay_gain: float
    track_peak_amplitude: float
    url_share: str
    replay_gain_write: bool
    upc: str
    m: mutagen.mp4.MP4 | mutagen.mp4.MP4 | mutagen.flac.FLAC

    def __init__(
        self,
        path_file: str | pathlib.Path,
        album: str = "",
        title: str = "",
        artists: str = "",
        copy_right: str = "",
        tracknumber: int = 0,
        discnumber: int = 0,
        totaltrack: int = 0,
        totaldisc: int = 0,
        composer: str = "",
        isrc: str = "",
        albumartist: str = "",
        date: str = "",
        lyrics: str = "",
        cover_data: bytes = None,
        album_replay_gain: float = 1.0,
        album_peak_amplitude: float = 1.0,
        track_replay_gain: float = 1.0,
        track_peak_amplitude: float = 1.0,
        url_share: str = "",
        replay_gain_write: bool = True,
        upc: str = "",
    ):
        self.path_file = path_file
        self.title = title
        self.album = album
        self.albumartist = albumartist
        self.artists = artists
        self.copy_right = copy_right
        self.tracknumber = tracknumber
        self.discnumber = discnumber
        self.totaldisc = totaldisc
        self.totaltrack = totaltrack
        self.date = date
        self.composer = composer
        self.isrc = isrc
        self.lyrics = lyrics
        self.cover_data = cover_data
        self.album_replay_gain = album_replay_gain
        self.album_peak_amplitude = album_peak_amplitude
        self.track_replay_gain = track_replay_gain
        self.track_peak_amplitude = track_peak_amplitude
        self.url_share = url_share
        self.replay_gain_write = replay_gain_write
        self.upc = upc
        self.m: mutagen.FileType = mutagen.File(self.path_file)

    def _cover(self) -> bool:
        result: bool = False

        if self.cover_data:
            if isinstance(self.m, mutagen.flac.FLAC):
                flac_cover = flac.Picture()
                flac_cover.type = id3.PictureType.COVER_FRONT
                flac_cover.data = self.cover_data
                flac_cover.mime = "image/jpeg"

                self.m.clear_pictures()
                self.m.add_picture(flac_cover)
            elif isinstance(self.m, mutagen.mp3.MP3):
                self.m.tags.add(APIC(encoding=3, data=self.cover_data))
            elif isinstance(self.m, mutagen.mp4.MP4):
                cover_mp4 = mp4.MP4Cover(self.cover_data)
                self.m.tags["covr"] = [cover_mp4]

            result = True

        return result

    def save(self):
        if not self.m.tags:
            self.m.add_tags()

        if isinstance(self.m, mutagen.flac.FLAC):
            self.set_flac()
        elif isinstance(self.m, mutagen.mp3.MP3):
            self.set_mp3()
        elif isinstance(self.m, mutagen.mp4.MP4):
            self.set_mp4()

        self._cover()
        self.cleanup_tags()
        self.m.save()

        return True

    def set_flac(self):
        self.m.tags["TITLE"] = self.title
        self.m.tags["ALBUM"] = self.album
        self.m.tags["ALBUMARTIST"] = self.albumartist
        self.m.tags["ARTIST"] = self.artists
        self.m.tags["COPYRIGHT"] = self.copy_right
        self.m.tags["TRACKNUMBER"] = str(self.tracknumber)
        self.m.tags["TRACKTOTAL"] = str(self.totaltrack)
        self.m.tags["DISCNUMBER"] = str(self.discnumber)
        self.m.tags["DISCTOTAL"] = str(self.totaldisc)
        self.m.tags["DATE"] = self.date
        self.m.tags["COMPOSER"] = self.composer
        self.m.tags["ISRC"] = self.isrc
        self.m.tags["LYRICS"] = self.lyrics
        self.m.tags["URL"] = self.url_share
        self.m.tags["UPC"] = self.upc

        if self.replay_gain_write:
            self.m.tags["REPLAYGAIN_ALBUM_GAIN"] = str(self.album_replay_gain)
            self.m.tags["REPLAYGAIN_ALBUM_PEAK"] = str(self.album_peak_amplitude)
            self.m.tags["REPLAYGAIN_TRACK_GAIN"] = str(self.track_replay_gain)
            self.m.tags["REPLAYGAIN_TRACK_PEAK"] = str(self.track_peak_amplitude)

    def set_mp3(self):
        # ID3 Frame (tags) overview: https://exiftool.org/TagNames/ID3.html / https://id3.org/id3v2.3.0
        # Mapping overview: https://docs.mp3tag.de/mapping/
        self.m.tags.add(TIT2(encoding=3, text=self.title))
        self.m.tags.add(TALB(encoding=3, text=self.album))
        self.m.tags.add(TOPE(encoding=3, text=self.albumartist))
        self.m.tags.add(TPE1(encoding=3, text=self.artists))
        self.m.tags.add(TCOP(encoding=3, text=self.copy_right))
        self.m.tags.add(TRCK(encoding=3, text=str(self.tracknumber)))
        self.m.tags.add(TRCK(encoding=3, text=self.discnumber))
        self.m.tags.add(TDRC(encoding=3, text=self.date))
        self.m.tags.add(TCOM(encoding=3, text=self.composer))
        self.m.tags.add(TSRC(encoding=3, text=self.isrc))
        self.m.tags.add(USLT(encoding=3, lang="eng", desc="desc", text=self.lyrics))
        self.m.tags.add(WOAS(encoding=3, text=self.isrc))
        self.m.tags.add(TXXX(encoding=3, desc="UPC", text=self.upc))

        if self.replay_gain_write:
            self.m.tags.add(TXXX(encoding=3, desc="REPLAYGAIN_ALBUM_GAIN", text=str(self.album_replay_gain)))
            self.m.tags.add(TXXX(encoding=3, desc="REPLAYGAIN_ALBUM_PEAK", text=str(self.album_peak_amplitude)))
            self.m.tags.add(TXXX(encoding=3, desc="REPLAYGAIN_TRACK_GAIN", text=str(self.track_replay_gain)))
            self.m.tags.add(TXXX(encoding=3, desc="REPLAYGAIN_TRACK_PEAK", text=str(self.track_peak_amplitude)))

    def set_mp4(self):
        self.m.tags["\xa9nam"] = self.title
        self.m.tags["\xa9alb"] = self.album
        self.m.tags["aART"] = self.albumartist
        self.m.tags["\xa9ART"] = self.artists
        self.m.tags["cprt"] = self.copy_right
        self.m.tags["trkn"] = [[self.tracknumber, self.totaltrack]]
        self.m.tags["disk"] = [[self.discnumber, self.totaldisc]]
        # self.m.tags['\xa9gen'] = self.genre
        self.m.tags["\xa9day"] = self.date
        self.m.tags["\xa9wrt"] = self.composer
        self.m.tags["\xa9lyr"] = self.lyrics
        self.m.tags["isrc"] = self.isrc
        self.m.tags["\xa9url"] = self.url_share
        self.m.tags["----:com.apple.iTunes:UPC"] = self.upc.encode("utf-8")

        if self.replay_gain_write:
            self.m.tags["----:com.apple.iTunes:REPLAYGAIN_ALBUM_GAIN"] = str(self.album_replay_gain).encode("utf-8")
            self.m.tags["----:com.apple.iTunes:REPLAYGAIN_ALBUM_PEAK"] = str(self.album_peak_amplitude).encode("utf-8")
            self.m.tags["----:com.apple.iTunes:REPLAYGAIN_TRACK_GAIN"] = str(self.track_replay_gain).encode("utf-8")
            self.m.tags["----:com.apple.iTunes:REPLAYGAIN_TRACK_PEAK"] = str(self.track_peak_amplitude).encode("utf-8")

    def cleanup_tags(self):
        for key, value in self.m.tags.items():
            if value == "" or value == [""]:
                del self.m.tags[key]
