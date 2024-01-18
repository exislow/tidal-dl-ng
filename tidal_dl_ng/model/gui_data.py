from dataclasses import dataclass

try:
    from PySide6 import QtCore

    @dataclass
    class ProgressBars:
        item: QtCore.Signal
        item_name: QtCore.Signal
        list_item: QtCore.Signal

except ModuleNotFoundError:

    class ProgressBars:
        pass


@dataclass
class ResultSearch:
    position: int
    artist: str
    title: str
    album: str
    duration_sec: int
    obj: object
