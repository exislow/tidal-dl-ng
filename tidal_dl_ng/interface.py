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

charCount = 0 # must cool down before every search
lastSearch = 0
tidal: Optional[Tidal] = None
settings: Settings = Settings() # starts at default
logger = LoggerWrapped(print)

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

def getSession(vault=False) -> Optional[Tidal]:
    """Initiate session from Tidal-dl-ng. Additionally, returns a reference to TidalObj if needed"""
    global tidal, settings
    if tidal is not None:
        return None # ignore subsequent requests
    
    TidalObj = Tidal(settings)
    TidalObj.login(fn_print=print) # TODO: change to logger
    logger.info(f"Logged in, with credentials at {TidalObj.file_path}")
    logger.info(f"{TidalObj.session.expiry_time.timestamp() - time()} seconds before expiration")
    tidal = TidalObj
    return tidal

def endSession():
    """Delete session, but save oauth tokens for later"""
    global tidal, usingVault
    if tidal is None:
        print("Maybe you haven't started a session.")
        return None
    del tidal.session
    del tidal

def logout():
    """Delete session and your refresh token"""
    global tidal
    if tidal is None:
        print("Maybe you haven't started a session.")
    else:
        tidal.logout()

def download(uri,
             typeName: Literal["artist", "album", "track"],
             folder: Path,
             fn_print=print
             ) -> Optional[bool]:
    if tidal is None:
        fn_print("Maybe you haven't started a session.")
        return None
    global settings

    dl = Download(tidal.session, folder.absolute().as_posix(), auxLogger) # type: ignore # loggers aren't class Callable
    match typeName:
        case "track":
            template = tidal.data.format_track # type: ignore
            logger.info(f"Downloading song {uri}")
            dl.item(template, Track(tidal.session, uri))
            return True
        case "album":
            template = tidal.data.format_album # type: ignore
            logger.info(f"Downloading songs from album {uri}")
            dl.items(template, Album(tidal.session, uri))
            return True
        case "artist":
            template = tidal.data.format_album # type: ignore
            albums = getChildren(uri, "artist")
            if isinstance(albums, list):
                for album in albums:
                    logger.info(f"Downloading album {album.name}")
                    dl.items(template, album)
                return True
    return False

def search(terms: str, 
           typeName: Literal["artist", "album", "track"],
           extensiveSearch=False,
           monitored=False,
           fn_print=print) -> Optional[List[Artist] | List[Album] | List[Track]]:
    
    if tidal is None:
        fn_print("You're not logged in!")
        return None

    if not monitored and extensiveSearch is True:
        # Basic restriction
        global charCount, lastSearch
        auxLogger.info("Checking against human writing speed")
        expectedTime = lastSearch + charCount/5 + random() # based on 60 words per minute
        auxLogger.debug(f"{time()} expecting {expectedTime}")
        while expectedTime > time():
            sleep(0.1)
        charCount = len(terms)
    # exhaustive search is essentially just search_results_all with a lower limit
    if extensiveSearch:
        itemLimit = 150 # You probably won't need 150 artists/albums to find the correct one
        # max is 300
        results: SearchResults = tidal.session.search(terms, [f".{typeName.capitalize()}"], limit=itemLimit)
    else:
        results: SearchResults = tidal.session.search(terms, [f".{typeName.capitalize()}"]) # limit=50
    lastSearch = time()
    key = typeName + "s"
    return results[key]

def searchOne(terms: str, 
           typeName: Literal["artist", "album", "track"], 
           extensiveSearch=False, 
           verifyMeta: Optional[Callable[[Any, Union[Artist, Album, Track], Literal["artist", "album", "track"]], bool]] = None, 
           metadata: Optional[Any]=None, 
           monitored=False,
           fn_print=print) -> Union[Artist, Album, Track, None]:
    """Search for an artist, album, or track.
    :param terms: what to search
    :param typeName: which to search for
    :param exhaustiveSearch: keeps searching until it finds a match or reaches the last page
    :param verifyMeta: Optional user provided function to double-check it's the correct item
    :param metadata: user provided data structure to be passed to their verifyMeta function
    :param monitored: whether the user wants the responsibility of managing the api limit"""
    # Be sure to verify the session expiration time
    
    results = search(terms, typeName, extensiveSearch, monitored, fn_print)
    if results is None:
        return None
    items: List[tuple] = []
    
    for result in results:
        longEnough = len(terms) > 5
        if longEnough:
            closeness = SequenceMatcher(None, result.name.lower(), terms.lower()).ratio() # type: ignore # name is not optional
            # *should* still work if you include the artist name,
            # unless it's the name of a different item
            items.append( (closeness, result) )
        else:
            if result == terms:
                items.append( (1, result) )
    matches = [item[1] for item in sorted(items, key=lambda item: item[0], reverse=True)] # sort top matching
    if verifyMeta is not None:
        # Check first 10
        amount = min(len(matches), 10)
        for item in matches[:amount]: # slice from 0 to 10 or the lowest amount
            if verifyMeta(metadata, item, typeName):
                return item
    return matches[0]

def getChildren(uri, typeName: Literal["artist", "album", "playlist", "mix"], includeVideos=False) -> Optional[List]:
    if tidal is None:
        print("Maybe you haven't started a session.")
        return None
    children: Optional[List] = None
    match typeName:
        case "artist": 
            item = Artist(tidal.session, uri)
            children = items_results_all(item, includeVideos) # returns albums
        case "album": 
            item = Album(tidal.session, uri)
            children = items_results_all(item, includeVideos) # returns tracks+videos or just tracks
        case "playlist": 
            item = Playlist(tidal.session, uri)
            children = items_results_all(item, includeVideos) # returns tracks+videos or just tracks
        case "mix": 
            item = Mix(tidal.session, uri)
            children = items_results_all(item, includeVideos) # returns tracks
    return children