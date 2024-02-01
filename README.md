# 🔰 TIDAL Downloader Next Generation! (tidal-dl-ng)

[![Release](https://img.shields.io/github/v/release/exislow/tidal-dl-ng)](https://img.shields.io/github/v/release/exislow/tidal-dl-ng)
[![Build status](https://img.shields.io/github/actions/workflow/status/exislow/tidal-dl-ng/main.yml?branch=main)](https://github.com/exislow/tidal-dl-ng/actions/workflows/main.yml?query=branch%3Amain)
[![Commit activity](https://img.shields.io/github/commit-activity/m/exislow/tidal-dl-ng)](https://img.shields.io/github/commit-activity/m/exislow/tidal-dl-ng)
[![License](https://img.shields.io/github/license/exislow/tidal-dl-ng)](https://img.shields.io/github/license/exislow/tidal-dl-ng)

This tool allows to download songs and videos from TIDAL. A paid plan is required! Audio quality varies up to HiRes / TIDAL MAX 24 Bit, 192 kHz depending on the song and your TIDAL plan. You can use the command line or GUI version of this tool.

![App Image](assets/app.png)

```bash
$ tidal-dl-ng --help

 Usage: tidal-dl-ng [OPTIONS] COMMAND [ARGS]...

╭─ Options ────────────────────────────────────────────────────────────────────────────────────╮
│ --version  -v                                                                                │
│ --help     -h        Show this message and exit.                                             │
╰──────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────╮
│ cfg    Print or set an option. If no arguments are given, all options will be listed. If     │
│        only one argument is given, the value will be printed for this option. To set a value │
│        for an option simply pass the value as the second argument                            │
│ dl                                                                                           │
│ gui                                                                                          │
│ login                                                                                        │
╰──────────────────────────────────────────────────────────────────────────────────────────────╯
```

If you like this projects and want to support it, you can buy me a coffee :-)

<a href="https://www.buymeacoffee.com/exislow" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/arial-orange.png" alt="Buy Me A Coffee" style="height: 51px !important;width: 217px !important;" ></a>
<a href="https://ko-fi.com/exislow" target="_blank" rel="noopener noreferrer"><img src="https://help.ko-fi.com/hc/article_attachments/11833788361117" alt="61e11d430afb112ea33c3aa5_Button-1-p-500"></a>

## 💻 Installation / Upgrade

**Requirements**: Python 3.11 (other versions might work but are not tested!)

```bash
pip install --upgrade tidal-dl-ng
# AND if you like to have the GUI as well
pip install --upgrade tidal-dl-ng[gui]
```

You can use the command line (CLI) version to download media:

```bash
tidal-dl-ng dl https://tidal.com/browse/track/46755209
# OR
tdn dl https://tidal.com/browse/track/46755209
```

But also the GUI:

```bash
tidal-dl-ng-gui
# OR
tdng
# OR
tidal-dl-ng gui
```

If you like to have the GUI version only, have a look at the
[release page](https://github.com/exislow/tidal-dl-ng/releases) and download the correct version for your platform.

## 🧁 Features

- Download Tracks, Videos, Albums, Playlists
- Metadata for songs
- Adjustable audio and video download quality.

## ▶️ Getting started with development

### 🚰 Install dependencies

Clone this repository and install the dependencies:

```bash
poetry install --all-extras --with dev,docs
```

The main entry points are:

```bash
tidal_ng_dl/cli.py
tidal_ng_dl/gui.py
```

### 📺 GUI Builder

The GUI is build with `PySide6` using the [Qt Designer](https://doc.qt.io/qt-6/qtdesigner-manual.html):

```bash
PYSIDE_DESIGNER_PLUGINS=tidal_dl_ng/ui pyside6-designer
```

After all changes are saved you need to translate the Qt Designer `*.ui` file into Python code:

```
pyside6-uic tidal_dl_ng/ui/main.ui -o tidal_dl_ng/ui/main.py
```

### 🏗 Build the project

To build the project use this command:

```bash
make install
```

The CI/CD pipeline will be triggered when you open a pull request, merge to main, or when you create a new release.

To finalize the set-up for publishing to PyPi or Artifactory, see [here](https://fpgmaas.github.io/cookiecutter-poetry/features/publishing/#set-up-for-pypi).
For activating the automatic documentation with MkDocs, see [here](https://fpgmaas.github.io/cookiecutter-poetry/features/mkdocs/#enabling-the-documentation-on-github).
To enable the code coverage reports, see [here](https://fpgmaas.github.io/cookiecutter-poetry/features/codecov/).

## ‼️ Disclaimer

- For educational purposes only. I am not liable and responsible for any damage that happens.
- You should not use this method to distribute or pirate music.
- It may be illegal to use this app in your country.

## 🫂 Contributors

Thanks to all, who have contributed to this project!

This project is based on:

- https://fpgmaas.github.io/cookiecutter-poetry/

<a href="https://github.com/exislow/tidal-dl-ng/graphs/contributors"><img src="https://contributors-img.web.app/image?repo=exislow/tidal-dl-ng" /></a>
