#!/usr/bin/env python
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Optional
import re
import spotipy
import tidalapi
from spotipy.oauth2 import SpotifyClientCredentials
import typer
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Console, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from tidal_dl_ng import __version__
from tidal_dl_ng.config import Settings, Tidal
from tidal_dl_ng.constants import CTX_TIDAL, MediaType
from tidal_dl_ng.download import Download
from tidal_dl_ng.helper.path import get_format_template, path_file_settings
from tidal_dl_ng.helper.tidal import (
    all_artist_album_ids,
    get_tidal_media_id,
    get_tidal_media_type,
    instantiate_media,
)
from tidal_dl_ng.helper.wrapper import LoggerWrapped
from tidal_dl_ng.model.cfg import HelpSettings

app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]}, add_completion=False)
dl_fav_group = typer.Typer(
    context_settings={"help_option_names": ["-h", "--help"]},
    add_completion=True,
    help="Download from a favorites collection.",
)

app.add_typer(dl_fav_group, name="dl_fav")


def version_callback(value: bool):
    if value:
        print(f"{__version__}")
        raise typer.Exit()


def _download(ctx: typer.Context, urls: list[str], try_login: bool = True) -> bool:
    """Invokes download function and tracks progress.

    :param ctx: The typer context object.
    :type ctx: typer.Context
    :param urls: The list of URLs to download.
    :type urls: list[str]
    :param try_login: If true, attempts to login to TIDAL.
    :type try_login: bool
    :return: True if ran successfully.
    :rtype: bool
    """
    if try_login:
        # Call login method to validate the token.
        ctx.invoke(login, ctx)

    # Create initial objects.
    settings: Settings = Settings()
    
    # Create a single persistent progress display
    progress = Progress(
        "{task.description}",
        SpinnerColumn(),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        refresh_per_second=20,
        auto_refresh=True,
        expand=True,
        transient=False  # Prevent progress from disappearing
    )
        
    fn_logger = LoggerWrapped(progress.print)
    dl = Download(
        session=ctx.obj[CTX_TIDAL].session,
        skip_existing=ctx.obj[CTX_TIDAL].settings.data.skip_existing,
        path_base=settings.data.download_base_path,
        fn_logger=fn_logger,
        progress=progress,
    )

    progress_table = Table.grid()
    progress_table.add_row(
        Panel.fit(progress, title="Download Progress", border_style="green", padding=(2, 2))
    )

    urls_pos_last = len(urls) - 1

    # Start the progress display
    progress.start()
    
    try:
        for item in urls:
            media_type: MediaType | bool = False

            # Extract media name and id from link.
            if "http" in item:
                media_type = get_tidal_media_type(item)
                item_id = get_tidal_media_id(item)
                file_template = get_format_template(media_type, settings)
            else:
                print(f"It seems like that you have supplied an invalid URL: {item}")
                continue

            # Download media.
            if media_type in [MediaType.TRACK, MediaType.VIDEO]:
                download_delay: bool = bool(settings.data.download_delay and urls.index(item) < urls_pos_last)

                dl.item(
                    media_id=item_id, media_type=media_type, file_template=file_template, download_delay=download_delay
                )
            elif media_type in [MediaType.ALBUM, MediaType.PLAYLIST, MediaType.MIX, MediaType.ARTIST]:
                item_ids: [int] = []

                if media_type == MediaType.ARTIST:
                    media = instantiate_media(ctx.obj[CTX_TIDAL].session, media_type, item_id)
                    media_type = MediaType.ALBUM
                    item_ids = item_ids + all_artist_album_ids(media)
                else:
                    item_ids.append(item_id)

                for item_id in item_ids:
                    dl.items(
                        media_id=item_id,
                        media_type=media_type,
                        file_template=file_template,
                        video_download=ctx.obj[CTX_TIDAL].settings.data.video_download,
                        download_delay=settings.data.download_delay,
                    )
    finally:
        # Clear and stop progress display
        progress.refresh()
        progress.stop()
        print("\nDownloads completed!")

    return True


@app.callback()
def callback_app(
    ctx: typer.Context,
    version: Annotated[
        Optional[bool], typer.Option("--version", "-v", callback=version_callback, is_eager=True)
    ] = None,
):
    ctx.obj = {"tidal": None}


@app.command(name="cfg")
def settings_management(
    names: Annotated[Optional[list[str]], typer.Argument()] = None,
    editor: Annotated[
        bool, typer.Option("--editor", "-e", help="Open the settings file in your default editor.")
    ] = False,
):
    """
    Print or set an option.
    If no arguments are given, all options will be listed.
    If only one argument is given, the value will be printed for this option.
    To set a value for an option simply pass the value as the second argument

    :param editor: If set, your favorite system editor will be opened.
    :param names: (Optional) None (list all options), one (list the value only for this option) or two arguments
        (set the value for the option).
    """
    if editor:
        config_path: Path = Path(path_file_settings())

        if not config_path.is_file():
            config_path.write_text('{"version": "1.0.0"}')

        config_file_str = str(config_path)

        typer.launch(config_file_str)
    else:
        settings = Settings()
        d_settings = settings.data.to_dict()

        if names:
            if names[0] not in d_settings:
                print(f'Option "{names[0]}" is not valid!')
            else:
                if len(names) == 1:
                    print(f'{names[0]}: "{d_settings[names[0]]}"')
                elif len(names) > 1:
                    settings.set_option(names[0], names[1])
                    settings.save()
        else:
            help_settings: dict = HelpSettings().to_dict()
            table = Table(title=f"Config: {path_file_settings()}")
            table.add_column("Key", style="cyan", no_wrap=True)
            table.add_column("Value", style="magenta")
            table.add_column("Description", style="green")

            # Iterate over the attributes of the dataclass
            for key, value in sorted(d_settings.items()):
                table.add_row(key, str(value), help_settings[key])

            console = Console()
            console.print(table)


@app.command(name="login")
def login(ctx: typer.Context) -> bool:
    print("Let us check, if you are already logged in... ", end="")

    settings = Settings()
    tidal = Tidal(settings)
    result = tidal.login(fn_print=print)
    ctx.obj[CTX_TIDAL] = tidal

    return result


@app.command(name="logout")
def logout() -> bool:
    settings = Settings()
    tidal = Tidal(settings)
    result = tidal.logout()

    if result:
        print("You have been successfully logged out.")

    return result


@app.command(name="dl")
def download(
    ctx: typer.Context,
    urls: Annotated[Optional[list[str]], typer.Argument()] = None,
    file_urls: Annotated[
        Optional[Path],
        typer.Option(
            "--list",
            "-l",
            exists=True,
            file_okay=True,
            dir_okay=False,
            writable=False,
            readable=True,
            resolve_path=True,
            help="List with URLs to download. One per line",
        ),
    ] = None,
) -> bool:
    if not urls:
        # Read the text file provided.
        if file_urls:
            text: str = file_urls.read_text()
            urls = text.splitlines()
        else:
            print("Provide either URLs, IDs or a file containing URLs (one per line).")

            raise typer.Abort()

    return _download(ctx, urls)


@dl_fav_group.command(
    name="tracks",
    help="Download your favorite track collection.",
)
def download_fav_tracks(ctx: typer.Context) -> bool:
    """Download your favorite track collection.

    :param ctx: Typer context object.
    :type ctx: typer.Context
    :return: Download result.
    :rtype: bool
    """
    # Method name
    func_name_favorites: str = "tracks"

    return _download_fav_factory(ctx, func_name_favorites)


@dl_fav_group.command(
    name="artists",
    help="Download your favorite artist collection.",
)
def download_fav_artists(ctx: typer.Context) -> bool:
    """Download your favorite artist collection.

    :param ctx: Typer context object.
    :type ctx: typer.Context
    :return: Download result.
    :rtype: bool
    """
    # Method name
    func_name_favorites: str = "artists"

    return _download_fav_factory(ctx, func_name_favorites)


@dl_fav_group.command(
    name="albums",
    help="Download your favorite album collection.",
)
def download_fav_albums(ctx: typer.Context) -> bool:
    """Download your favorite album collection.

    :param ctx: Typer context object.
    :type ctx: typer.Context
    :return: Download result.
    :rtype: bool
    """
    # Method name
    func_name_favorites: str = "albums"

    return _download_fav_factory(ctx, func_name_favorites)


@dl_fav_group.command(
    name="videos",
    help="Download your favorite video collection.",
)
def download_fav_videos(ctx: typer.Context) -> bool:
    """Download your favorite video collection.

    :param ctx: Typer context object.
    :type ctx: typer.Context
    :return: Download result.
    :rtype: bool
    """
    # Method name
    func_name_favorites: str = "videos"

    return _download_fav_factory(ctx, func_name_favorites)


def _download_fav_factory(ctx: typer.Context, func_name_favorites: str) -> bool:
    """Factory which helps to download items from the favorites collections.

    :param ctx: Typer context object.
    :type ctx: typer.Context
    :param func_name_favorites: Method name to call from `tidalapi` favorites object.
    :type func_name_favorites: str
    :return: Download result.
    :rtype: bool
    """
    # Call login method to validate the token.
    ctx.invoke(login, ctx)

    # Get the method from the module
    func_favorites: Callable = getattr(ctx.obj[CTX_TIDAL].session.user.favorites, func_name_favorites)
    # Get favorite videos
    media_urls: [str] = [media.share_url for media in func_favorites()]

    return _download(ctx, media_urls, try_login=False)


def _validate_spotify_credentials(settings: Settings) -> None:
    """Validate that Spotify API credentials are configured.
    
    :param settings: The application settings.
    :type settings: Settings
    :raises typer.Exit: If credentials are not configured.
    """
    if not settings.data.spotify_client_id or not settings.data.spotify_client_secret:
        print("Please set Spotify API credentials in config using:")
        print("tidal-dl-ng cfg spotify_client_id YOUR_CLIENT_ID")
        print("tidal-dl-ng cfg spotify_client_secret YOUR_CLIENT_SECRET")
        raise typer.Exit(1)


def _extract_spotify_id(spotify_url: str) -> tuple[str, str]:
    """Extract ID and type from a Spotify URL.
    
    :param spotify_url: The Spotify URL to parse.
    :type spotify_url: str
    :return: A tuple containing the content type and ID.
    :rtype: tuple[str, str]
    :raises typer.Exit: If the URL is invalid.
    """
    playlist_match = re.search(r'playlist/([a-zA-Z0-9]+)', spotify_url)
    album_match = re.search(r'album/([a-zA-Z0-9]+)', spotify_url)
    track_match = re.search(r'track/([a-zA-Z0-9]+)', spotify_url)
    
    if playlist_match:
        return "playlist", playlist_match.group(1)
    elif album_match:
        return "album", album_match.group(1)
    elif track_match:
        return "track", track_match.group(1)
    else:
        print("Invalid Spotify URL. Please provide a valid Spotify playlist, album, or track URL.")
        raise typer.Exit(1)


def _fetch_spotify_tracks(sp: spotipy.Spotify, content_type: str, content_id: str) -> list:
    """Fetch tracks from Spotify based on content type and ID.
    
    :param sp: The Spotify client.
    :type sp: spotipy.Spotify
    :param content_type: The type of content ('playlist', 'album', or 'track').
    :type content_type: str
    :param content_id: The Spotify ID of the content.
    :type content_id: str
    :return: A list of tracks.
    :rtype: list
    """
    tracks = []
    
    if content_type == "playlist":
        print(f"Fetching Spotify playlist: {content_id}")
        
        # Get all playlist tracks with pagination
        results = sp.playlist_tracks(content_id)
        tracks.extend(results['items'])
        
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])
    elif content_type == "album":
        print(f"Fetching Spotify album: {content_id}")
        
        # Get album information
        album = sp.album(content_id)
        
        # Get all album tracks with pagination
        results = sp.album_tracks(content_id)
        
        # Convert album tracks to the same format as playlist tracks
        for track in results['items']:
            tracks.append({'track': track})
        
        # Handle pagination for albums with more than 50 tracks
        while results['next']:
            results = sp.next(results)
            for track in results['items']:
                tracks.append({'track': track})
    elif content_type == "track":
        print(f"Fetching Spotify track: {content_id}")
        
        # Get track information
        track = sp.track(content_id)
        
        # Add the track to the list in the same format as playlist tracks
        tracks.append({'track': track})
                
    return tracks


def _search_tracks_on_tidal(ctx: typer.Context, tracks: list) -> tuple[list, list]:
    """Search for Spotify tracks on TIDAL.
    
    :param ctx: The typer context.
    :type ctx: typer.Context
    :param tracks: The list of Spotify tracks.
    :type tracks: list
    :return: A tuple containing lists of found URLs and not found tracks.
    :rtype: tuple[list, list]
    """
    urls = []
    not_found = []
    
    for track in tracks:
        # Handle different track structures between playlist and album responses
        if 'track' in track:
            # Playlist track structure
            track_info = track['track']
        else:
            # Album track structure (already at the track level)
            track_info = track
            
        artist = track_info['artists'][0]['name']
        title = track_info['name']
        
        # Extract ISRC if available
        isrc = None
        if 'external_ids' in track_info and 'isrc' in track_info['external_ids']:
            isrc = track_info['external_ids']['isrc']
        
        # Call login method to validate the token
        if not ctx.obj[CTX_TIDAL]:
            ctx.invoke(login, ctx)
        
        # First try to find by ISRC if available
        found_by_isrc = False
        if isrc:
            # Search on TIDAL using text search
            results = ctx.obj[CTX_TIDAL].session.search(f"{artist} {title}", models=[tidalapi.media.Track])
            if results and len(results['tracks']) > 0:
                # Check if any of the results have a matching ISRC
                for tidal_track in results['tracks']:
                    if hasattr(tidal_track, 'isrc') and tidal_track.isrc == isrc:
                        track_url = tidal_track.share_url
                        urls.append(track_url)
                        found_by_isrc = True
                        print(f"Found exact match by ISRC for: {artist} - {title}")
                        break
        
        # If not found by ISRC, fall back to text search
        if not isrc or not found_by_isrc:
            # Search on TIDAL
            results = ctx.obj[CTX_TIDAL].session.search(f"{artist} {title}", models=[tidalapi.media.Track])
            if results and len(results['tracks']) > 0:
                track_url = results['tracks'][0].share_url
                urls.append(track_url)
            else:
                not_found.append(f"{artist} - {title}")
                
    return urls, not_found


@app.command(name="spotify")
def download_spotify(
    ctx: typer.Context,
    spotify_url: Annotated[str, typer.Argument(help="Spotify URL (playlist, album, or track)")],  # noqa: UP007
) -> bool:
    """Download tracks from a Spotify playlist, album, or individual track by searching for them on TIDAL.
    
    The matching process first attempts to find tracks by ISRC (International Standard
    Recording Code) for exact matching between services. If no match is found by ISRC
    or if the ISRC is not available, it falls back to text search using artist and title.
    
    Requires Spotify API credentials to be configured:
    1. Create an app at https://developer.spotify.com/dashboard
    2. Set the client ID: tidal-dl-ng cfg spotify_client_id YOUR_CLIENT_ID
    3. Set the client secret: tidal-dl-ng cfg spotify_client_secret YOUR_CLIENT_SECRET
    """
    settings = Settings()
    
    # Validate Spotify credentials
    _validate_spotify_credentials(settings)

    # Initialize Spotify client
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=settings.data.spotify_client_id,
        client_secret=settings.data.spotify_client_secret
    ))

    # Extract ID and type from URL
    content_type, content_id = _extract_spotify_id(spotify_url)
    
    # Fetch tracks from Spotify
    tracks = _fetch_spotify_tracks(sp, content_type, content_id)
    total_tracks = len(tracks)
    
    # Search for tracks on TIDAL
    urls, not_found = _search_tracks_on_tidal(ctx, tracks)
    
    # Print summary of found tracks
    if urls:
        print(f"\nFound {len(urls)} of {total_tracks} tracks on TIDAL")
    else:
        print("\nNo tracks found to download")
        
    # Print not found tracks
    if not_found:
        print("\nSongs not found on TIDAL:")
        for song in not_found:
            print(song)
    
    # Use the existing download function if we have URLs
    if urls:
        return _download(ctx, urls, try_login=False)
    else:
        return False

@app.command()
def gui(ctx: typer.Context):
    from tidal_dl_ng.gui import gui_activate

    ctx.invoke(login, ctx)
    gui_activate(ctx.obj[CTX_TIDAL])


if __name__ == "__main__":
    app()
