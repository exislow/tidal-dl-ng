#!/usr/bin/env python
import signal
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

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
    Album,
    Artist,
    Mix,
    Playlist,
    Track,
    Video,
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
    handling_app: HandlingApp = HandlingApp()
    progress: Progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        SpinnerColumn(),
        BarColumn(),
        TaskProgressColumn(),
        refresh_per_second=20,
        auto_refresh=True,
        expand=True,
        transient=False,  # Prevent progress from disappearing
    )
    progress_overall = Progress(
        TextColumn("[progress.description]{task.description}"),
        SpinnerColumn(),
        BarColumn(),
        TaskProgressColumn(),
        refresh_per_second=20,
        auto_refresh=True,
        expand=True,
        transient=False,  # Prevent progress from disappearing
    )
    fn_logger = LoggerWrapped(progress.print)
    dl = Download(
        session=ctx.obj[CTX_TIDAL].session,
        skip_existing=ctx.obj[CTX_TIDAL].settings.data.skip_existing,
        path_base=settings.data.download_base_path,
        fn_logger=fn_logger,
        progress=progress,
        progress_overall=progress_overall,
        event_abort=handling_app.event_abort,
        event_run=handling_app.event_run,
    )
    progress_table = Table.grid()

    # Style Progress display.
    progress_table.add_row(progress)
    progress_table.add_row(progress_overall)

    progress_group = Group(
        progress_table,
    )

    urls_pos_last = len(urls) - 1

    # Use a single Live display for both progress and table
    with Live(progress_group, refresh_per_second=20, vertical_overflow="visible"):
        try:
            for item in urls:
                media_type: MediaType | bool = False

                # Exit loop if abort signal is set.
                if handling_app.event_abort.is_set():
                    return False

                # Extract media name and id from link.
                if "http" in item:
                    media_type = get_tidal_media_type(item)
                    item_id = get_tidal_media_id(item)
                    file_template = get_format_template(media_type, settings)
                else:
                    print(f"It seems like that you have supplied an invalid URL: {item}")

                    continue

                try:
                    media: Track | Video | Album | Playlist | Mix | Artist = instantiate_media(
                        ctx.obj[CTX_TIDAL].session, media_type, item_id
                    )
                except Exception:
                    print(f"Media not found (ID: {item_id}). Maybe it is not available anymore.")
                    continue

                # Download media.
                if media_type in [MediaType.TRACK, MediaType.VIDEO]:
                    download_delay: bool = bool(settings.data.download_delay and urls.index(item) < urls_pos_last)

                    dl.item(
                        media=media,
                        file_template=file_template,
                        download_delay=download_delay,
                        quality_audio=settings.data.quality_audio,
                        quality_video=settings.data.quality_video,
                    )
                elif media_type in [MediaType.ALBUM, MediaType.PLAYLIST, MediaType.MIX, MediaType.ARTIST]:
                    item_ids: [int] = []

                    if media_type == MediaType.ARTIST:
                        media_type = MediaType.ALBUM
                        item_ids = item_ids + all_artist_album_ids(media)
                    else:
                        item_ids.append(item_id)

                    for item_id in item_ids:
                        # Exit loop if abort signal is set.
                        if handling_app.event_abort.is_set():
                            return False

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

    return True


@app.callback()
def callback_app(
    ctx: typer.Context,
    version: Annotated[bool | None, typer.Option("--version", "-v", callback=version_callback, is_eager=True)] = None,
):
    ctx.obj = {"tidal": None}


@app.command(name="cfg")
def settings_management(
    names: Annotated[list[str] | None, typer.Argument()] = None,
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


@app.command()
def gui(ctx: typer.Context):
    from tidal_dl_ng.gui import gui_activate

    ctx.invoke(login, ctx)
    gui_activate(ctx.obj[CTX_TIDAL])


def handle_sigint_term(signum, frame):
    """Set app abort event, so threads can check it and shutdown.

    :param signum:
    :param frame:
    :return:
    """
    handling_app: HandlingApp = HandlingApp()

    handling_app.event_abort.set()


if __name__ == "__main__":
    # Catch CTRL+C
    signal.signal(signal.SIGINT, handle_sigint_term)
    signal.signal(signal.SIGTERM, handle_sigint_term)

    app()
