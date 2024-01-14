#!/usr/bin/env python
import importlib.metadata

try:
    # __package__ allows for the case where __name__ is "__main__"
    __version__ = importlib.metadata.version(__package__ or __name__)
    __name_display__ = importlib.metadata.metadata(__package__ or __name__).json["name"]
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"
    __name_display__ = __package__ or __name__
