# 🔰 TIDAL Downloader Next Generation! (tidal-dl-ng)

[![Release](https://img.shields.io/github/v/release/exislow/tidal-dl-ng)](https://img.shields.io/github/v/release/exislow/tidal-dl-ng)
[![Build status](https://img.shields.io/github/actions/workflow/status/exislow/tidal-dl-ng/on-release-master.yml)](https://github.com/exislow/tidal-dl-ng/actions/workflows/on-release-master.yml)
[![Commit activity](https://img.shields.io/github/commit-activity/m/exislow/tidal-dl-ng)](https://img.shields.io/github/commit-activity/m/exislow/tidal-dl-ng)
[![License](https://img.shields.io/github/license/exislow/tidal-dl-ng)](https://img.shields.io/github/license/exislow/tidal-dl-ng)

This tool allows to download songs and videos from TIDAL. Multithreaded and multi-chunked downloads are supported.

⚠️ **Windows** Defender / **Anti Virus** software / web browser alerts, while you try to download the app binary: This is a **false positive**. Please read [this issue](https://github.com/exislow/tidal-dl-ng/issues/231), [PyInstaller (used by this project) statement ](https://github.com/pyinstaller/pyinstaller/blob/develop/.github/ISSUE_TEMPLATE/antivirus.md) and [the alternative installation solution](https://github.com/exislow/tidal-dl-ng/?tab=readme-ov-file#-installation--upgrade). ⚠️

**A paid TIDAL plan is required!** Audio quality varies up to HiRes Lossless / TIDAL MAX 24-bit, 192 kHz depending on the song available. You can use the command line or GUI version of this tool.

![App Image](assets/app.png)

```bash
$ tidal-dl-ng --help

 Usage: tidal-dl-ng [OPTIONS] COMMAND [ARGS]...

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --version  -v                                                                │
│ --help     -h        Show this message and exit.                             │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ cfg    Print or set an option. If no arguments are given, all options will   │
│        be listed. If only one argument is given, the value will be printed   │
│        for this option. To set a value for an option simply pass the value   │
│        as the second argument                                                │
│ dl                                                                           │
│ dl_fav Download from a favorites collection.                                 │
│ gui                                                                          │
│ login                                                                        │
│ logout                                                                       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

If you like this projects and want to support it, feel free to buy me a coffee 🙃✌️

<a href="https://www.buymeacoffee.com/exislow" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/arial-orange.png" alt="Buy Me A Coffee" style="height: 51px !important;width: 217px !important;" ></a>
<a href="https://ko-fi.com/exislow" target="_blank" rel="noopener noreferrer"><img src="https://help.ko-fi.com/hc/article_attachments/11833788361117" alt="61e11d430afb112ea33c3aa5_Button-1-p-500"></a>

## 💻 Installation / Upgrade


### Using pip

**Requirements**: Python == 3.12 (other versions might work but are not tested!)

```bash
pip install --upgrade tidal-dl-ng
# If you like to have the GUI as well use this command instead
pip install --upgrade tidal-dl-ng[gui]
```

### Using Docker 
**Requirements**: Docker == 27.5.0 (other verions might work but are not tested!) 
All you need is the ```Dockerfile``` file from this repository and be in the same directory as it.
To build the image using ```docker build``` command: 
```bash
docker build -t <container-image-name> .
```
You can give any name you want to the container.


## ⌨️ Usage

### 🐍 Using pip
You can use the command line (CLI) version to download media by URL:

```bash
tidal-dl-ng dl https://tidal.com/browse/track/46755209
# OR
tdn dl https://tidal.com/browse/track/46755209
```

Or by your favorites collections:

```bash
tidal-dl-ng dl_fav tracks
tidal-dl-ng dl_fav artists
tidal-dl-ng dl_fav albums
tidal-dl-ng dl_fav videos
```

You can also use the GUI:

```bash
tidal-dl-ng-gui
# OR
tdng
# OR
tidal-dl-ng gui
```

If you like to have the GUI version only as a binary, have a look at the
[release page](https://github.com/exislow/tidal-dl-ng/releases) and download the correct version for your platform.

### 🐋 Using the Docker image
Simply create a music folder to mount to the container you will create, then run :
```bash
docker run -v "/path/to/host/music/folder:/home/appuser/music" -v tidal-dl-volume:/home/appuser/.config/tidal_dl_ng/ -it <container-image-name>:latest <command>
```
This command will also create a Docker volume to store your ```settings.json``` as well as your ```token.json``` when connected to Tidal.
The ```<command>``` is where you use tidal-dl-ng as described in the previous section when using pip.

⚠️ The folder from the host that you map in the container must exist, if Docker creates it it might be owned by ```root``` and tidal-dl-ng **will not have the rights** to write in this folder ⚠️

💡 You can also run a bash shell if you want to tinker in the container. Nano and ffmpeg are installed and the ffmpeg path is preconfigured in the ```settings.json```.
Currently, the Docker image does not support the GUI version.

## 🧁 Features

- Download tracks, videos, albums, playlists, your favorites etc.
- Multithreaded and multi-chunked downloads
- Metadata for songs
- Adjustable audio and video download quality.
- FLAC extraction from MP4 containers
- Lyrics and album art / cover download
- Creates playlist files
- Can symlink tracks instead of having several copies, if added to different playlist

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

After all changes are saved you need to translate the Qt Designer `*.ui` file into Python code, for instance:

```
pyside6-uic tidal_dl_ng/ui/main.ui -o tidal_dl_ng/ui/main.py
```

This needs to be done for each created / modified `*.ui` file accordingly.

### 🏗 Build the project

To build the project use this command:

```bash
make install
# OR
make gui-macos
```

See the `Makefile` for all available build commands.

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
