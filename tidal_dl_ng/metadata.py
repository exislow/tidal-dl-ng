import mutagen
import requests
from mutagen import flac, id3, mp4
from mutagen.id3 import APIC, TALB, TCOM, TCOP, TDRC, TIT2, TOPE, TPE1, TRCK, TSRC, USLT

from tidal_dl_ng.constants import REQUESTS_TIMEOUT_SEC


class Metadata:
    path_file: str
    title: str
    album: str
    albumartist: str
    artists: [str]
    copy_right: str
    tracknumber: int
    discnumber: int
    totaldisc: int
    totaltrack: int
    date: str
    composer: [str]
    isrc: str
    lyrics: str
    path_cover: str
    url_cover: str
    m: mutagen.mp4.MP4 | mutagen.mp4.MP4 | mutagen.flac.FLAC

    def __init__(
        self,
        path_file: str,
        album: str = "",
        title: str = "",
        artists: list[str] | None = None,
        copy_right: str = "",
        tracknumber: int = 0,
        discnumber: int = 0,
        totaltrack: int = 0,
        totaldisc: int = 0,
        composer: list[str] | None = None,
        isrc: str = "",
        albumartist: str = "",
        date: str = "",
        lyrics: str = "",
        path_cover: str = "",
        url_cover: str = "",
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
        self.path_cover = path_cover
        self.url_cover = url_cover
        self.m: mutagen.mp4.MP4 | mutagen.flac.FLAC | mutagen.mp3.MP3 = mutagen.File(self.path_file)

    def _cover(self) -> bool:
        result: bool = False
        data_cover: str | bytes = self.cover_data(url=self.url_cover, path_file=self.path_cover)

        if data_cover:
            if isinstance(self.m, mutagen.flac.FLAC):
                flac_cover = flac.Picture()
                flac_cover.type = id3.PictureType.COVER_FRONT
                flac_cover.data = data_cover
                flac_cover.mime = "image/jpeg"

                self.m.clear_pictures()
                self.m.add_picture(flac_cover)
            elif isinstance(self.m, mutagen.mp3.MP3):
                self.m.tags.add(APIC(encoding=3, data=data_cover))
            elif isinstance(self.m, mutagen.mp4.MP4):
                cover_mp4 = mp4.MP4Cover(data_cover)
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
        self.m.save()

        return True

    def set_flac(self):
        self.m.tags["title"] = self.title
        self.m.tags["album"] = self.album
        self.m.tags["albumartist"] = self.albumartist
        self.m.tags["artist"] = ", ".join(self.artists) if self.artists else ""
        self.m.tags["copyright"] = self.copy_right
        self.m.tags["tracknumber"] = str(self.tracknumber)
        self.m.tags["tracktotal"] = str(self.totaltrack)
        self.m.tags["discnumber"] = str(self.discnumber)
        self.m.tags["disctotal"] = str(self.totaldisc)
        self.m.tags["date"] = self.date
        self.m.tags["composer"] = ", ".join(self.composer) if self.composer else ""
        self.m.tags["isrc"] = self.isrc
        self.m.tags["lyrics"] = self.lyrics

    def set_mp3(self):
        self.m.tags.add(TIT2(encoding=3, text=self.title))
        self.m.tags.add(TALB(encoding=3, text=self.album))
        self.m.tags.add(TOPE(encoding=3, text=self.albumartist))
        self.m.tags.add(TPE1(encoding=3, text=", ".join(self.artists) if self.artists else ""))
        self.m.tags.add(TCOP(encoding=3, text=self.copy_right))
        self.m.tags.add(TRCK(encoding=3, text=str(self.tracknumber)))
        self.m.tags.add(TRCK(encoding=3, text=self.discnumber))
        self.m.tags.add(TDRC(encoding=3, text=self.date))
        self.m.tags.add(TCOM(encoding=3, text=", ".join(self.composer) if self.composer else ""))
        self.m.tags.add(TSRC(encoding=3, text=self.isrc))
        self.m.tags.add(USLT(encoding=3, lang="eng", desc="desc", text=self.lyrics))

    def set_mp4(self):
        self.m.tags["\xa9nam"] = self.title
        self.m.tags["\xa9alb"] = self.album
        self.m.tags["aART"] = self.albumartist
        self.m.tags["\xa9ART"] = ", ".join(self.artists) if self.artists else ""
        self.m.tags["cprt"] = self.copy_right
        self.m.tags["trkn"] = [[self.tracknumber, self.totaltrack]]
        self.m.tags["disk"] = [[self.discnumber, self.totaldisc]]
        # self.m.tags['\xa9gen'] = self.genre
        self.m.tags["\xa9day"] = self.date
        self.m.tags["\xa9wrt"] = ", ".join(self.composer) if self.composer else ""
        self.m.tags["\xa9lyr"] = self.lyrics

    def cover_data(self, url: str = None, path_file: str = None) -> str | bytes:
        result: str | bytes = ""

        if url:
            try:
                result = requests.get(url, timeout=REQUESTS_TIMEOUT_SEC).content
            except Exception as e:
                # TODO: Implement propper logging.
                print(e)
        elif path_file:
            try:
                with open(path_file, "rb") as f:
                    result = f.read()
            except OSError as e:
                # TODO: Implement propper logging.
                print(e)

        return result
