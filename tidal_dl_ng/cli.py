#!/usr/bin/env python
import signal
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

import typer
from rich.console import Console, Group
from rich.live import Live
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table

from tidal_dl_ng import __version__
from tidal_dl_ng.config import HandlingApp, Settings, Tidal
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
app_dl_fav = typer.Typer(
    context_settings={"help_option_names": ["-h", "--help"]},
    add_completion=True,
    help="Download from a favorites collection.",
)

app.add_typer(app_dl_fav, name="dl_fav")


def version_callback(value: bool):
    """Callback to print version and exit if version flag is set.

    Args:
        value (bool): If True, prints version and exits.
    """
    if value:
        print(f"{__version__}")

        raise typer.Exit()


@app.callback()
def callback_app(
    ctx: typer.Context,
    version: Annotated[bool | None, typer.Option("--version", "-v", callback=version_callback, is_eager=True)] = None,
):
    """App callback to initialize context and handle version option.

    Args:
        ctx (typer.Context): Typer context object.
        version (bool | None, optional): Version flag. Defaults to None.
    """
    ctx.obj = {"tidal": None}


def _handle_track_or_video(
    dl: Download, ctx: typer.Context, item: str, media: object, file_template: str, idx: int, urls_pos_last: int
) -> None:
    """Handle downloading a track or video item.

    Args:
        dl (Download): The Download instance.
        ctx (typer.Context): Typer context object.
        item (str): The URL or identifier of the item.
        media: The media object to download.
        file_template (str): The file template for saving the media.
        idx (int): The index of the item in the list.
        urls_pos_last (int): The last index in the URLs list.
    """
    settings = ctx.obj[CTX_TIDAL].settings
    download_delay: bool = bool(settings.data.download_delay and idx < urls_pos_last)

    dl.item(
        media=media,
        file_template=file_template,
        download_delay=download_delay,
        quality_audio=settings.data.quality_audio,
        quality_video=settings.data.quality_video,
    )


def _handle_album_playlist_mix_artist(
    ctx: typer.Context,
    dl: Download,
    handling_app: HandlingApp,
    media_type: MediaType,
    media: object,
    item_id: str,
    file_template: str,
) -> bool:
    """Handle downloading albums, playlists, mixes, or artist collections.

    Args:
        ctx (typer.Context): Typer context object.
        dl (Download): The Download instance.
        handling_app (HandlingApp): The HandlingApp instance.
        media_type (MediaType): The type of media (album, playlist, mix, or artist).
        media: The media object to download.
        item_id (str): The ID of the media item.
        file_template (str): The file template for saving the media.

    Returns:
        bool: False if aborted, True otherwise.
    """
    item_ids: list[str] = []
    settings = ctx.obj[CTX_TIDAL].settings

    if media_type == MediaType.ARTIST:
        media_type = MediaType.ALBUM
        item_ids += all_artist_album_ids(media)
    else:
        item_ids.append(item_id)

    for _item_id in item_ids:
        if handling_app.event_abort.is_set():
            return False

        dl.items(
            media_id=_item_id,
            media_type=media_type,
            file_template=file_template,
            video_download=settings.data.video_download,
            download_delay=settings.data.download_delay,
            quality_audio=settings.data.quality_audio,
            quality_video=settings.data.quality_video,
        )

    return True


def _process_url(
    dl: Download,
    ctx: typer.Context,
    handling_app: HandlingApp,
    item: str,
    idx: int,
    urls_pos_last: int,
) -> bool:
    """Process a single URL or ID for download.

    Args:
        dl (Download): The Download instance.
        ctx (typer.Context): Typer context object.
        handling_app (HandlingApp): The HandlingApp instance.
        item (str): The URL or identifier to process.
        idx (int): The index of the item in the list.
        urls_pos_last (int): The last index in the URLs list.

    Returns:
        bool: False if aborted, True otherwise.
    """
    settings = ctx.obj[CTX_TIDAL].settings

    if handling_app.event_abort.is_set():
        return False

    if "http" not in item:
        print(f"It seems like that you have supplied an invalid URL: {item}")
        return True

    media_type = get_tidal_media_type(item)
    if not isinstance(media_type, MediaType):
        print(f"Could not determine media type for: {item}")
        return True

    item_id = get_tidal_media_id(item)
    if not isinstance(item_id, str):
        print(f"Could not determine media id for: {item}")
        return True

    file_template = get_format_template(media_type, settings)
    if not isinstance(file_template, str):
        print(f"Could not determine file template for: {item}")
        return True

    try:
        media = instantiate_media(ctx.obj[CTX_TIDAL].session, media_type, item_id)
    except Exception:
        print(f"Media not found (ID: {item_id}). Maybe it is not available anymore.")
        return True

    if media_type in [MediaType.TRACK, MediaType.VIDEO]:
        _handle_track_or_video(dl, ctx, item, media, file_template, idx, urls_pos_last)
    elif media_type in [MediaType.ALBUM, MediaType.PLAYLIST, MediaType.MIX, MediaType.ARTIST]:
        return _handle_album_playlist_mix_artist(ctx, dl, handling_app, media_type, media, item_id, file_template)
    return True


def _download(ctx: typer.Context, urls: list[str], try_login: bool = True) -> bool:
    """Invokes download function and tracks progress.

    Args:
        ctx (typer.Context): The typer context object.
        urls (list[str]): The list of URLs to download.
        try_login (bool, optional): If true, attempts to login to TIDAL. Defaults to True.

    Returns:
        bool: True if ran successfully.
    """
    if try_login:
        ctx.invoke(login, ctx)

    settings: Settings = ctx.obj[CTX_TIDAL].settings
    handling_app: HandlingApp = HandlingApp()

    progress: Progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        SpinnerColumn(),
        BarColumn(),
        TaskProgressColumn(),
        refresh_per_second=20,
        auto_refresh=True,
        expand=True,
        transient=False,
    )

    progress_overall = Progress(
        TextColumn("[progress.description]{task.description}"),
        SpinnerColumn(),
        BarColumn(),
        TaskProgressColumn(),
        refresh_per_second=20,
        auto_refresh=True,
        expand=True,
        transient=False,
    )

    fn_logger = LoggerWrapped(progress.print)

    dl = Download(
        session=ctx.obj[CTX_TIDAL].session,
        skip_existing=settings.data.skip_existing,
        path_base=settings.data.download_base_path,
        fn_logger=fn_logger,
        progress=progress,
        progress_overall=progress_overall,
        event_abort=handling_app.event_abort,
        event_run=handling_app.event_run,
    )

    progress_table = Table.grid()
    progress_table.add_row(progress)
    progress_table.add_row(progress_overall)
    progress_group = Group(progress_table)

    urls_pos_last = len(urls) - 1

    with Live(progress_group, refresh_per_second=20, vertical_overflow="visible"):
        try:
            for idx, item in enumerate(urls):
                if _process_url(dl, ctx, handling_app, item, idx, urls_pos_last) is False:
                    return False
        finally:
            progress.refresh()
            progress.stop()

    return True


@app.command(name="cfg")
def settings_management(
    names: Annotated[list[str] | None, typer.Argument()] = None,
    editor: Annotated[
        bool, typer.Option("--editor", "-e", help="Open the settings file in your default editor.")
    ] = False,
) -> None:
    """Print or set an option, or open the settings file in an editor.

    Args:
        names (list[str] | None, optional): None (list all options), one (list the value only for this option) or two arguments (set the value for the option). Defaults to None.
        editor (bool, optional): If set, your favorite system editor will be opened. Defaults to False.
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
            elif len(names) == 1:
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

            for key, value in sorted(d_settings.items()):
                table.add_row(key, str(value), help_settings[key])

            console = Console()
            console.print(table)


@app.command(name="login")
def login(ctx: typer.Context) -> bool:
    """Login to TIDAL and update context object.

    Args:
        ctx (typer.Context): Typer context object.

    Returns:
        bool: True if login was successful, False otherwise.
    """
    print("Let us check, if you are already logged in... ", end="")

    settings = Settings()
    tidal = Tidal(settings)
    result = tidal.login(fn_print=print)
    ctx.obj[CTX_TIDAL] = tidal

    return result


@app.command(name="logout")
def logout() -> bool:
    """Logout from TIDAL.

    Returns:
        bool: True if logout was successful, False otherwise.
    """
    settings = Settings()
    tidal = Tidal(settings)
    result = tidal.logout()

    if result:
        print("You have been successfully logged out.")

    return result


@app.command(name="dl")
def download(
    ctx: typer.Context,
    urls: Annotated[list[str] | None, typer.Argument()] = None,
    file_urls: Annotated[
        Path | None,
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
    """Download media from provided URLs or a file containing URLs.

    Args:
        ctx (typer.Context): Typer context object.
        urls (list[str] | None, optional): List of URLs to download. Defaults to None.
        file_urls (Path | None, optional): Path to file containing URLs. Defaults to None.

    Returns:
        bool: True if download was successful, False otherwise.
    """
    if not urls:
        # Read the text file provided.
        if file_urls:
            text: str = file_urls.read_text()
            urls = text.splitlines()
        else:
            print("Provide either URLs, IDs or a file containing URLs (one per line).")

            raise typer.Abort()

    return _download(ctx, urls)


@app_dl_fav.command(
    name="tracks",
    help="Download your favorite track collection.",
)
def download_fav_tracks(ctx: typer.Context) -> bool:
    """Download your favorite track collection.

    Args:
        ctx (typer.Context): Typer context object.

    Returns:
        bool: Download result.
    """
    # Method name
    func_name_favorites: str = "tracks"

    return _download_fav_factory(ctx, func_name_favorites)


@app_dl_fav.command(
    name="artists",
    help="Download your favorite artist collection.",
)
def download_fav_artists(ctx: typer.Context) -> bool:
    """Download your favorite artist collection.

    Args:
        ctx (typer.Context): Typer context object.

    Returns:
        bool: Download result.
    """
    # Method name
    func_name_favorites: str = "artists"

    return _download_fav_factory(ctx, func_name_favorites)


@app_dl_fav.command(
    name="albums",
    help="Download your favorite album collection.",
)
def download_fav_albums(ctx: typer.Context) -> bool:
    """Download your favorite album collection.

    Args:
        ctx (typer.Context): Typer context object.

    Returns:
        bool: Download result.
    """
    # Method name
    func_name_favorites: str = "albums"

    return _download_fav_factory(ctx, func_name_favorites)


@app_dl_fav.command(
    name="videos",
    help="Download your favorite video collection.",
)
def download_fav_videos(ctx: typer.Context) -> bool:
    """Download your favorite video collection.

    Args:
        ctx (typer.Context): Typer context object.

    Returns:
        bool: Download result.
    """
    # Method name
    func_name_favorites: str = "videos"

    return _download_fav_factory(ctx, func_name_favorites)


def _download_fav_factory(ctx: typer.Context, func_name_favorites: str) -> bool:
    """Factory which helps to download items from the favorites collections.

    Args:
        ctx (typer.Context): Typer context object.
        func_name_favorites (str): Method name to call from `tidalapi` favorites object.

    Returns:
        bool: Download result.
    """
    ctx.invoke(login, ctx)
    func_favorites: Callable = getattr(ctx.obj[CTX_TIDAL].session.user.favorites, func_name_favorites)
    media_urls: list[str] = [media.share_url for media in func_favorites()]
    return _download(ctx, media_urls, try_login=False)


@app.command()
def gui(ctx: typer.Context):
    """Launch the GUI for the application.

    Args:
        ctx (typer.Context): Typer context object.
    """
    from tidal_dl_ng.gui import gui_activate

    ctx.invoke(login, ctx)
    gui_activate(ctx.obj[CTX_TIDAL])


def handle_sigint_term(signum, frame):
    """Set app abort event, so threads can check it and shutdown.

    Args:
        signum: Signal number.
        frame: Current stack frame.
    """
    handling_app: HandlingApp = HandlingApp()

    handling_app.event_abort.set()


if __name__ == "__main__":
    # Catch CTRL+C
    signal.signal(signal.SIGINT, handle_sigint_term)
    signal.signal(signal.SIGTERM, handle_sigint_term)

    # Check if the first argument is a URL. Hacky solution, since Typer does not support positional arguments without options / commands.
    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        parsed_url = urlparse(first_arg)

        if parsed_url.scheme in ["http", "https"] and parsed_url.netloc:
            # Rewrite sys.argv to simulate `dl <URL>`
            sys.argv.insert(1, "dl")

    app()
