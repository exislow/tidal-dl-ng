#!/usr/bin/env python
import importlib.metadata
import sys
from pathlib import Path

import toml


def get_version_app() -> str:
    file_path: Path = Path(__file__)

    paths: [Path] = [
        file_path.parent,
        file_path.parent.parent,
        file_path.parent.parent.parent,
    ]
    version: str = "0.0.0"

    for pyproject_toml_dir in paths:
        pyproject_toml_file: Path = pyproject_toml_dir / "pyproject.toml"

        if pyproject_toml_file.exists() and pyproject_toml_file.is_file():
            package_version: str = toml.load(pyproject_toml_file)["tool"]["poetry"]["version"]

            version = package_version

            break

    return version


def get_name_app() -> str:
    name_app: str = __package__ or __name__

    # Check if package is running from source code  == dev mode
    # If package is not running in PyInstaller environment.
    if getattr(sys, "frozen", True) and not hasattr(sys, "_MEIPASS"):
        try:
            importlib.metadata.version(name_app)
        except:
            # If package is not installed
            name_app = name_app + "-dev"

    return name_app


__name_display__ = get_name_app()
__version__ = get_version_app()
