import pathlib

import mutagen
import requests
from mutagen import flac, mp4
from mutagen.id3 import APIC, TALB, TCOM, TCOP, TDRC, TIT2, TOPE, TPE1, TRCK, TSRC, USLT


class Metadata:
    path_file: str = None
    type_audio: str = None
    title: str = None
    album: str = None
    albumartist: str = None
    artists: [str] = None
    copy_right: str = None
    tracknumber: int = None
    discnumber: int = None
    totaldisc: int = None
    totaltrack: int = None
    date: str = None
    composer: [str] = None
    isrc: str = None
    lyrics: str = None
    path_cover: str = None
    url_cover: str = None
    m: mutagen.mp4.MP4 | mutagen.mp4.MP4 | mutagen.flac.FLAC = None

    # TODO: What about videos?
    def __init__(
        self,
        path_file: str,
        type_audio: str = "",
        album: str = "",
        title: str = "",
        artists: [str] = [""],
        copy_right: str = "",
        tracknumber: int = 0,
        discnumber: int = 0,
        totaltrack: int = 0,
        totaldisc: int = 0,
        composer: [str] = [""],
        isrc: str = "",
        albumartist: str = "",
        date: str = "",
        lyrics: str = "",
        path_cover: str = "",
        url_cover: str = "",
    ):
        self.path_file = path_file

        if type_audio:
            self.type_audio = type_audio
        else:
            self.type_audio = pathlib.Path(self.path_file).suffix[1:]

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
        self.path_cover = path_cover
        self.url_cover = url_cover
        self.m: mutagen.MP4.MP4 | mutagen.m4a.M4A | mutagen.flac.FLAC | mutagen.mp3.MP3 = mutagen.File(self.path_file)

    def _cover(self) -> bool:
        result = False
        data_cover = None

        if self.url_cover:
            try:
                data_cover = requests.get(self.url_cover).content
            except:
                data_cover = ""
        elif self.path_cover:
            with open(self.path_cover, "rb") as f:
                data_cover = f.read()

        if data_cover:
            if self.type_audio == "flac":
                flac_cover = flac.Picture()
                flac_cover.data = data_cover
                flac_cover.mime = "image/jpeg"

                self.m.clear_pictures()
                self.m.add_picture(flac_cover)
            elif self.type_audio == "mp3":
                self.m.tags.add(APIC(encoding=3, data=data_cover))
            elif self.type_audio in ["mp4", "m4a"]:
                cover_mp4 = mp4.MP4Cover(data_cover)
                self.m.tags["covr"] = [cover_mp4]

            result = True

        return result

    def save(self):
        if self.type_audio == "flac":
            self.set_flac()
        elif self.type_audio in ["mp3", "ts"]:
            self.set_mp3()
        elif self.type_audio in ["mp4", "m4a"]:
            self.set_mp4()

        self._cover()
        self.m.save()

        return True

    def set_flac(self):
        if not self.m.tags:
            self.m.add_tags()

        self.m.tags["title"] = self.title
        self.m.tags["album"] = self.album
        self.m.tags["albumartist"] = self.albumartist
        self.m.tags["artist"] = ", ".join(self.artists)
        self.m.tags["copyright"] = self.copy_right
        self.m.tags["tracknumber"] = str(self.tracknumber)
        self.m.tags["tracktotal"] = str(self.totaltrack)
        self.m.tags["discnumber"] = str(self.discnumber)
        self.m.tags["disctotal"] = str(self.totaldisc)
        self.m.tags["date"] = self.date
        self.m.tags["composer"] = ", ".join(self.composer)
        self.m.tags["isrc"] = self.isrc
        self.m.tags["lyrics"] = self.lyrics

    def set_mp3(self):
        if not self.m.tags:
            self.m.add_tags()

        self.m.tags.add(TIT2(encoding=3, text=self.title))
        self.m.tags.add(TALB(encoding=3, text=self.album))
        self.m.tags.add(TOPE(encoding=3, text=self.albumartist))
        self.m.tags.add(TPE1(encoding=3, text=", ".join(self.artists)))
        self.m.tags.add(TCOP(encoding=3, text=self.copy_right))
        self.m.tags.add(TRCK(encoding=3, text=str(self.tracknumber)))
        self.m.tags.add(TRCK(encoding=3, text=self.discnumber))
        self.m.tags.add(TDRC(encoding=3, text=self.date))
        self.m.tags.add(TCOM(encoding=3, text=", ".join(self.composer)))
        self.m.tags.add(TSRC(encoding=3, text=self.isrc))
        self.m.tags.add(USLT(encoding=3, lang="eng", desc="desc", text=self.lyrics))

    def set_mp4(self):
        self.m.tags["\xa9nam"] = self.title
        self.m.tags["\xa9alb"] = self.album
        self.m.tags["aART"] = self.albumartist
        self.m.tags["\xa9ART"] = ", ".join(self.artists)
        self.m.tags["cprt"] = self.copy_right
        self.m.tags["trkn"] = [[self.tracknumber, self.totaltrack]]
        self.m.tags["disk"] = [[self.discnumber, self.totaldisc]]
        # self.m.tags['\xa9gen'] = self.genre
        self.m.tags["\xa9day"] = self.date
        self.m.tags["\xa9wrt"] = ", ".join(self.composer)
        self.m.tags["\xa9lyr"] = self.lyrics
