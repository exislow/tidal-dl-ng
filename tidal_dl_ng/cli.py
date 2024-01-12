#!/usr/bin/env python
from typing import Annotated, Optional

from pathlib import Path

import typer
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Console, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from tidal_dl_ng import __version__
from tidal_dl_ng.config import Settings, Tidal
from tidal_dl_ng.constants import CTX_TIDAL, MediaType
from tidal_dl_ng.download import Download
from tidal_dl_ng.helper.path import path_file_settings
from tidal_dl_ng.helper.url import get_tidal_media_id, get_tidal_media_type
from tidal_dl_ng.helper.wrapper import WrapperLogger
from tidal_dl_ng.model.cfg import HelpSettings

app = typer.Typer()


def version_callback(value: bool):
    if value:
        print(f"{__version__}")
        raise typer.Exit()


@app.callback()
def callback_app(
    ctx: typer.Context,
    version: Annotated[Optional[bool], typer.Option("--version", "-v", callback=version_callback, is_eager=True)] = None,
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
    result = tidal.login(print)
    ctx.obj[CTX_TIDAL] = tidal

    return result


@app.command(name="dl")
def download(
    ctx: typer.Context,
    urls_or_ids: Annotated[Optional[list[str]], typer.Argument()] = None,
    list_urls: Annotated[
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
):
    if not urls_or_ids:
        if list_urls:
            text = list_urls.read_text()
            urls_or_ids = text.splitlines()
        else:
            print("Provide either URLs, IDs or a file containing URLs (one per line).")

            raise typer.Abort()

    ctx.invoke(login, ctx)

    dl = Download(ctx.obj[CTX_TIDAL].session, ctx.obj[CTX_TIDAL].settings.data.skip_existing)
    settings: Settings = Settings()
    media_type: MediaType = None
    progress: Progress = Progress(
        "{task.description}",
        SpinnerColumn(),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    )
    progress_table = Table.grid()
    fn_logger = WrapperLogger(progress.print)

    progress_table.add_row(Panel.fit(progress, title="Download Progress", border_style="green", padding=(2, 2)))

    for item in urls_or_ids:
        if "http" in item:
            media_name = get_tidal_media_type(item)
            id_item = get_tidal_media_id(item)
        else:
            media_name = False
            id_item = item

        if not media_name:
            print(f"It seems like that you have supplied an invalid URL: {item}")

            continue

        with Live(progress_table, refresh_per_second=10):
            # TODO: Fix media type
            if media_name in ["track", "video"]:
                if media_name == "track":
                    file_template = settings.data.format_track
                    media_type = MediaType.Track
                elif media_name == "video":
                    file_template = settings.data.format_video
                    media_type = MediaType.Video

                dl.item(
                    id_media=id_item,
                    media_type=media_type,
                    path_base=settings.data.download_base_path,
                    file_template=file_template,
                    progress=progress,
                    fn_logger=fn_logger
                )
            elif media_name in ["album", "playlist", "mix"]:
                # TODO: Handle mixes.
                file_template: str | bool = False

                if media_name == "album":
                    file_template = settings.data.format_album
                    media_type = MediaType.Album
                elif media_name == "playlist":
                    file_template = settings.data.format_playlist
                    media_type = MediaType.Playlist
                elif media_name == "mix":
                    file_template = settings.data.format_mix
                    media_type = MediaType.Mix

                dl.items(
                    id_media=id_item,
                    media_type=media_type,
                    path_base=settings.data.download_base_path,
                    file_template=file_template,
                    video_download=ctx.obj[CTX_TIDAL].settings.data.video_download,
                    progress=progress,
                    download_delay=settings.data.download_delay,
                    fn_logger=fn_logger,
                )

    progress.stop()

    return True


@app.command()
def gui(ctx: typer.Context):
    from tidal_dl_ng.gui import gui_activate

    ctx.invoke(login, ctx)
    gui_activate(ctx.obj[CTX_TIDAL])


if __name__ == "__main__":
    app()
