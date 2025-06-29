#!/usr/bin/env python
import importlib.metadata
from pathlib import Path
from urllib.parse import urlparse

import requests
import toml

from tidal_dl_ng.constants import REQUESTS_TIMEOUT_SEC
from tidal_dl_ng.model.meta import ProjectInformation, ReleaseLatest


def metadata_project() -> ProjectInformation:
    result: ProjectInformation
    file_path: Path = Path(__file__)
    tmp_result: dict = {}

    paths: [Path] = [
        file_path.parent,
        file_path.parent.parent,
        file_path.parent.parent.parent,
    ]

    for pyproject_toml_dir in paths:
        pyproject_toml_file: Path = pyproject_toml_dir / "pyproject.toml"

        if pyproject_toml_file.exists() and pyproject_toml_file.is_file():
            tmp_result = toml.load(pyproject_toml_file)

            break

    if tmp_result:
        result = ProjectInformation(
            version=tmp_result["project"]["version"], repository_url=tmp_result["project"]["urls"]["repository"]
        )
    else:
        try:
            meta_info = importlib.metadata.metadata(name_package())
            result = ProjectInformation(version=meta_info["Version"], repository_url=meta_info["Home-page"])
        except:
            result = ProjectInformation(version="0.0.0", repository_url="https://anerroroccur.ed/sorry/for/that")

    return result


def version_app() -> str:
    metadata: ProjectInformation = metadata_project()
    version: str = metadata.version

    return version


def repository_url() -> str:
    metadata: ProjectInformation = metadata_project()
    url_repo: str = metadata.repository_url

    return url_repo


def repository_path() -> str:
    url_repo: str = repository_url()
    url_path: str = urlparse(url_repo).path

    return url_path


def latest_version_information() -> ReleaseLatest:
    release_info: ReleaseLatest
    repo_path: str = repository_path()
    url: str = f"https://api.github.com/repos{repo_path}/releases/latest"

    try:
        response = requests.get(url, timeout=REQUESTS_TIMEOUT_SEC)
        release_info: str = response.json()

        release_info = ReleaseLatest(
            version=release_info["tag_name"], url=release_info["html_url"], release_info=release_info["body"]
        )
    except:
        release_info = ReleaseLatest(
            version="v0.0.0",
            url=url,
            release_info=f"Something went wrong calling {url}. Check your internet connection.",
        )

    return release_info


def name_package() -> str:
    package_name: str = __package__ or __name__

    return package_name


def is_dev_env() -> bool:
    package_name: str = name_package()
    result: bool = False

    # Check if package is running from source code == dev mode
    # If package is not running in Nuitka environment, try to import it from pip libraries.
    # If this also fails, it is dev mode.
    if "__compiled__" not in globals():
        try:
            importlib.metadata.version(package_name)
        except:
            # If package is not installed
            result = True

    return result


def name_app() -> str:
    app_name: str = name_package()
    is_dev: bool = is_dev_env()

    if is_dev:
        app_name = app_name + "-dev"

    return app_name


__name_display__ = name_app()
__version__ = version_app()


def update_available() -> (bool, ReleaseLatest):
    latest_info: ReleaseLatest = latest_version_information()
    result: bool = False
    version_current: str = "v" + __version__

    if version_current != latest_info.version and version_current != "v0.0.0":
        result = True

    return result, latest_info
