#!/usr/bin/env python
from pathlib import Path
from typing import Annotated, Optional

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
from tidal_dl_ng.helper.tidal import get_tidal_media_id, get_tidal_media_type
from tidal_dl_ng.helper.wrapper import LoggerWrapped
from tidal_dl_ng.model.cfg import HelpSettings

app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]}, add_completion=False)


def version_callback(value: bool):
    if value:
        print(f"{__version__}")
        raise typer.Exit()


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
):
    if not urls:
        # Read the text file provided.
        if file_urls:
            text = file_urls.read_text()
            urls = text.splitlines()
        else:
            print("Provide either URLs, IDs or a file containing URLs (one per line).")

            raise typer.Abort()

    # Call login method to validate the token.
    ctx.invoke(login, ctx)

    # Create initial objects.
    settings: Settings = Settings()
    progress: Progress = Progress(
        "{task.description}",
        SpinnerColumn(),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
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

    # Style Progress display.
    progress_table.add_row(Panel.fit(progress, title="Download Progress", border_style="green", padding=(2, 2)))

    urls_pos_last = len(urls) - 1

    for item in urls:
        media_type: MediaType | bool = False

        # Extract media name and id from link.
        if "http" in item:
            media_type = get_tidal_media_type(item)
            item_id = get_tidal_media_id(item)
            file_template = get_format_template(media_type, settings)

        # If url is invalid skip to next url in list.
        if not media_type:
            print(f"It seems like that you have supplied an invalid URL: {item}")

            continue

        # Create Live display for Progress.
        with Live(progress_table, refresh_per_second=10):
            # Download media.
            if media_type in [MediaType.TRACK, MediaType.VIDEO]:
                download_delay: bool = bool(settings.data.download_delay and urls.index(item) < urls_pos_last)

                dl.item(
                    media_id=item_id, media_type=media_type, file_template=file_template, download_delay=download_delay
                )
            elif media_type in [MediaType.ALBUM, MediaType.PLAYLIST, MediaType.MIX]:
                dl.items(
                    media_id=item_id,
                    media_type=media_type,
                    file_template=file_template,
                    video_download=ctx.obj[CTX_TIDAL].settings.data.video_download,
                    download_delay=settings.data.download_delay,
                )

    # Stop Progress display.
    progress.stop()

    return True


@app.command()
def gui(ctx: typer.Context):
    from tidal_dl_ng.gui import gui_activate

    ctx.invoke(login, ctx)
    gui_activate(ctx.obj[CTX_TIDAL])


if __name__ == "__main__":
    app()
