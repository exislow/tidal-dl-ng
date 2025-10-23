import pathlib
import subprocess
import sys

from tidal_dl_ng.logger import logger_gui


class FileSystemHelper:
    """Helper class for file system operations with proper error handling."""

    @staticmethod
    def normalize_path(path: str) -> pathlib.Path:
        """
        Normalize and validate a file system path.

        Args:
            path: The raw string path.

        Returns:
            A resolved pathlib.Path object.

        Raises:
            ValueError: If the path is empty or invalid.
        """
        if not path:
            raise ValueError("Path cannot be empty")
            
        try:
            normalized = pathlib.Path(path)
            # Resolve to catch issues early (optional, depends on use case)
            # normalized.resolve(strict=False)
            return normalized
            
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid path format: {path}") from e


    @staticmethod
    def path_exists(path: pathlib.Path) -> bool:
        """
        Check if path exists.

        Args:
            path: The path to check.

        Returns:
            True if the path exists, False otherwise.
        """
        try:
            return path.exists()
        except (OSError, PermissionError):
            logger_gui.exception("Permission error checking path", extra={"path": path})
            return False

    @staticmethod
    def open_in_explorer(path: pathlib.Path, logger) -> bool:
        """
        Open file explorer at the given path with platform-specific handling.

        Args:
            path: The pathlib.Path object to open.
            logger: The logger instance to use for reporting errors.

        Returns:
            True if the operation was successful, False otherwise.
        """
        try:
            # Validate path exists
            if not FileSystemHelper.path_exists(path):
                # No log error here; path_exists already logged exception if one occurred
                return False

            # Determine if path is file or directory
            is_file = path.is_file()

            # Platform-specific handling
            if sys.platform == "win32":
                return FileSystemHelper._open_windows(path, is_file, logger)
            elif sys.platform == "darwin":
                return FileSystemHelper._open_macos(path, is_file, logger)
            else:
                return FileSystemHelper._open_linux(path, is_file, logger)

        except Exception:
            logger.exception("Could not open explorer")
            return False

    @staticmethod
    def _open_windows(path: pathlib.Path, is_file: bool, logger) -> bool:
        """
        Open Windows Explorer to the specified path.

        Args:
            path: The path to open.
            is_file: True if the path is a file, False if a directory.
            logger: The logger instance.

        Returns:
            True on success, False on failure.
        """
        try:
            if is_file:
                # Select the file in Explorer
                subprocess.Popen(["explorer", "/select,", str(path)])
            else:
                # Open the directory
                subprocess.Popen(["explorer", str(path)])
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.exception("Windows Explorer failed")
            return False
        else:
            return True

    @staticmethod
    def _open_macos(path: pathlib.Path, is_file: bool, logger) -> bool:
        """
        Open macOS Finder to the specified path.

        Args:
            path: The path to open.
            is_file: True if the path is a file, False if a directory.
            logger: The logger instance.

        Returns:
            True on success, False on failure.
        """
        try:
            if is_file:
                # Reveal the file in Finder
                subprocess.run(["open", "-R", str(path)], check=True)
            else:
                # Open the directory
                subprocess.run(["open", str(path)], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.exception("macOS Finder failed")
            return False
        else:
            return True

    @staticmethod
    def _open_linux(path: pathlib.Path, is_file: bool, logger) -> bool:
        """
        Open Linux file manager to the specified path.

        Args:
            path: The path to open.
            is_file: True if the path is a file, False if a directory.
            logger: The logger instance.

        Returns:
            True on success, False on failure.
        """
        try:
            # Most Linux file managers prefer opening the directory
            dir_path = path.parent if is_file else path

            # Try xdg-open first (standard)
            subprocess.run(["xdg-open", str(dir_path)], check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback
            file_managers = ["nautilus", "dolphin", "thunar", "nemo", "pcmanfm"]
            for manager in file_managers:
                try:
                    subprocess.run([manager, str(dir_path)], check=True)
                    return True
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue

            logger.exception("No compatible file manager found on Linux")
            return False