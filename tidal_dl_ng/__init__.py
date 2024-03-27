#!/usr/bin/env python
import importlib.metadata
import sys
from pathlib import Path

import requests
import toml

from tidal_dl_ng.constants import REQUESTS_TIMEOUT_SEC


def metadata_project() -> dict:
    file_path: Path = Path(__file__)
    result: dict = {}

    paths: [Path] = [
        file_path.parent,
        file_path.parent.parent,
        file_path.parent.parent.parent,
    ]

    for pyproject_toml_dir in paths:
        pyproject_toml_file: Path = pyproject_toml_dir / "pyproject.toml"

        if pyproject_toml_file.exists() and pyproject_toml_file.is_file():
            result: str = toml.load(pyproject_toml_file)

            break

    return result


def version_app() -> str:
    metadata: dict = metadata_project()
    version: str = "0.0.0"

    if metadata:
        package_version: str = metadata["tool"]["poetry"]["version"]

        version = package_version

    return version


def latest_version_available():
    response = requests.get(
        "https://api.github.com/repos/v2ray/v2ray-core/releases/latest", timeout=REQUESTS_TIMEOUT_SEC
    )

    a = response.json()["name"]
    print(a)


def name_package() -> str:
    package_name: str = __package__ or __name__

    return package_name


def is_dev_env() -> bool:
    package_name: str = name_package()
    result: bool = False

    # Check if package is running from source code  == dev mode
    # If package is not running in PyInstaller environment.
    if getattr(sys, "frozen", True) and not hasattr(sys, "_MEIPASS"):
        try:
            importlib.metadata.version(package_name)
        except:
            # If package is not installed
            result = False

    return result


def name_app() -> str:
    app_name: str = name_package()
    is_dev: bool = is_dev_env()

    if is_dev:
        app_name = app_name + "-dev"

    return app_name


__name_display__ = name_app()
__version__ = version_app()
