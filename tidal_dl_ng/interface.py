import tomllib
from difflib import SequenceMatcher
from pathlib import Path
from random import random
from time import sleep, time
from typing import Any, Callable, List, Literal, Optional, Union
from tidal_dl_ng.config import Settings, Tidal
from tidal_dl_ng.download import Download
from tidal_dl_ng.helper.tidal import items_results_all
from tidal_dl_ng.helper.wrapper import LoggerWrapped
from tidal_dl_ng.model.cfg import Settings as ModelSettings
from tidalapi import Album, Artist, Mix, Playlist, Track
from tidalapi.session import SearchResults

def initConfig(config: Path):
    # Config must use the same key value pairs shown in /model/cfg.py
    extIndex = config.name.rfind('.') + 1
    fileExt = config.name[extIndex::]
    assert fileExt == "toml", f".{fileExt} is not TOML"
    with open(config, "rb") as f:
        try:
            myConfig = tomllib.load(f)
        except tomllib.TOMLDecodeError as err:
            err.add_note("TOML could not be loaded. Is your file written according to https://toml.io/en/v1.0.0 ?")
            raise err
    global settings
    settings.data = ModelSettings(**myConfig["config"]["tidal-dl"])
    return myConfig