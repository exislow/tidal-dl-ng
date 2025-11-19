import json
import os
import shutil
from collections.abc import Callable
from json import JSONDecodeError
from pathlib import Path
from threading import Event, Lock
from typing import Any

import tidalapi

from tidal_dl_ng.constants import (
    ATMOS_CLIENT_ID,
    ATMOS_CLIENT_SECRET,
    ATMOS_REQUEST_QUALITY,
)
from tidal_dl_ng.helper.decorator import SingletonMeta
from tidal_dl_ng.helper.path import path_config_base, path_file_settings, path_file_token
from tidal_dl_ng.model.cfg import Settings as ModelSettings
from tidal_dl_ng.model.cfg import Token as ModelToken


class BaseConfig:
    data: ModelSettings | ModelToken
    file_path: str
    cls_model: ModelSettings | ModelToken
    path_base: str = path_config_base()

    def save(self, config_to_compare: str = None) -> None:
        data_json = self.data.to_json()

        # If old and current config is equal, skip the write operation.
        if config_to_compare == data_json:
            return

        # Try to create the base folder.
        os.makedirs(self.path_base, exist_ok=True)

        with open(self.file_path, encoding="utf-8", mode="w") as f:
            # Save it in a pretty format
            obj_json_config = json.loads(data_json)
            json.dump(obj_json_config, f, indent=4)

    def set_option(self, key: str, value: Any) -> None:
        value_old: Any = getattr(self.data, key)

        if type(value_old) == bool:  # noqa: E721
            value = True if value.lower() in ("true", "1", "yes", "y") else False  # noqa: SIM210
        elif type(value_old) == int and type(value) != int:  # noqa: E721
            value = int(value)

        setattr(self.data, key, value)

    def read(self, path: str) -> bool:
        result: bool = False
        settings_json: str = ""

        try:
            with open(path, encoding="utf-8") as f:
                settings_json = f.read()

            self.data = self.cls_model.from_json(settings_json)
            result = True
        except (JSONDecodeError, TypeError, FileNotFoundError, ValueError) as e:
            if isinstance(e, ValueError):
                path_bak = path + ".bak"

                # First check if a backup file already exists. If yes, remove it.
                if os.path.exists(path_bak):
                    os.remove(path_bak)

                # Move the invalid config file to the backup location.
                shutil.move(path, path_bak)
                # TODO: Implement better global logger.
                print(
                    "Something is wrong with your config. Maybe it is not compatible anymore due to a new app version."
                    f" You can find a backup of your old config here: '{path_bak}'. A new default config was created."
                )

            self.data = self.cls_model()

        # Call save in case of we need to update the saved config, due to changes in code.
        self.save(settings_json)

        return result


class Settings(BaseConfig, metaclass=SingletonMeta):
    def __init__(self):
        self.cls_model = ModelSettings
        self.file_path = path_file_settings()
        self.read(self.file_path)
        # Migrate legacy delimiter fields to new atomic parameters if needed
        self._migrate_legacy_delimiters()
        # Save after migration to persist the new atomic parameters
        self.save()

    def _sync_legacy_delimiters(self) -> None:
        """Synchronize legacy delimiter fields from atomic parameters.

        This ensures that the legacy fields are always up-to-date with the
        atomic parameters when saving configuration.
        """
        # Sync legacy fields from atomic parameters
        self.data.metadata_delimiter_artist = self.get_metadata_artist_delimiter()
        self.data.metadata_delimiter_album_artist = self.get_metadata_album_artist_delimiter()
        self.data.filename_delimiter_artist = self.get_filename_artist_delimiter()
        self.data.filename_delimiter_album_artist = self.get_filename_album_artist_delimiter()

    def save(self, config_to_compare: str = None) -> None:
        """Save settings to file, ensuring legacy fields are synchronized.

        Args:
            config_to_compare (str, optional): Previous config to compare against.
        """
        # Sync legacy delimiter fields before saving
        self._sync_legacy_delimiters()
        # Call parent save method
        super().save(config_to_compare)

    def _migrate_legacy_delimiters(self) -> None:
        """Migrate old delimiter format to new atomic parameters.

        This ensures backward compatibility when loading old configuration files
        that only have the legacy `metadata_delimiter_artist` style fields.
        """

        # Always sync legacy fields to new fields if they differ from computed values
        # This handles both fresh installs and migrations from old configs

        # Metadata Artist
        computed: str = self._build_delimiter(
            self.data.metadata_artist_separator,
            self.data.metadata_artist_space_before,
            self.data.metadata_artist_space_after,
        )
        if self.data.metadata_delimiter_artist != computed:
            self._parse_legacy_delimiter(
                self.data.metadata_delimiter_artist,
                "metadata_artist_separator",
                "metadata_artist_space_before",
                "metadata_artist_space_after",
            )

        # Metadata Album Artist
        computed = self._build_delimiter(
            self.data.metadata_album_artist_separator,
            self.data.metadata_album_artist_space_before,
            self.data.metadata_album_artist_space_after,
        )
        if self.data.metadata_delimiter_album_artist != computed:
            self._parse_legacy_delimiter(
                self.data.metadata_delimiter_album_artist,
                "metadata_album_artist_separator",
                "metadata_album_artist_space_before",
                "metadata_album_artist_space_after",
            )

        # Filename Artist
        computed = self._build_delimiter(
            self.data.filename_artist_separator,
            self.data.filename_artist_space_before,
            self.data.filename_artist_space_after,
        )
        if self.data.filename_delimiter_artist != computed:
            self._parse_legacy_delimiter(
                self.data.filename_delimiter_artist,
                "filename_artist_separator",
                "filename_artist_space_before",
                "filename_artist_space_after",
            )

        # Filename Album Artist
        computed = self._build_delimiter(
            self.data.filename_album_artist_separator,
            self.data.filename_album_artist_space_before,
            self.data.filename_album_artist_space_after,
        )
        if self.data.filename_delimiter_album_artist != computed:
            self._parse_legacy_delimiter(
                self.data.filename_delimiter_album_artist,
                "filename_album_artist_separator",
                "filename_album_artist_space_before",
                "filename_album_artist_space_after",
            )

    def _parse_legacy_delimiter(
        self, legacy_value: str, sep_attr: str, space_before_attr: str, space_after_attr: str
    ) -> None:
        """Parse a legacy delimiter string into atomic components.

        Args:
            legacy_value: The old delimiter string (e.g., " ; ", ", ", "/")
            sep_attr: Attribute name for separator symbol
            space_before_attr: Attribute name for space_before boolean
            space_after_attr: Attribute name for space_after boolean
        """
        import logging

        from tidal_dl_ng.constants import ArtistSeparator

        logger = logging.getLogger(__name__)

        # Detect space before
        space_before: bool = legacy_value.startswith(" ") if legacy_value else False
        # Detect space after
        space_after: bool = legacy_value.endswith(" ") if legacy_value else False
        # Extract core symbol
        core_symbol: str = legacy_value.strip() if legacy_value else ","

        # Validate against whitelist
        try:
            separator_enum = ArtistSeparator(core_symbol)
        except ValueError:
            # Invalid separator, fallback to comma with warning
            logger.warning(f"Invalid separator '{core_symbol}' found in legacy config. Falling back to comma.")
            separator_enum = ArtistSeparator.COMMA

        # Apply parsed values
        setattr(self.data, sep_attr, separator_enum)
        setattr(self.data, space_before_attr, space_before)
        setattr(self.data, space_after_attr, space_after)

    def get_metadata_artist_delimiter(self) -> str:
        """Construct the metadata artist delimiter from atomic parameters.

        Returns:
            str: The complete delimiter string (e.g., " ; ", ", ", "/")
        """
        return self._build_delimiter(
            self.data.metadata_artist_separator,
            self.data.metadata_artist_space_before,
            self.data.metadata_artist_space_after,
        )

    def get_metadata_album_artist_delimiter(self) -> str:
        """Construct the metadata album artist delimiter from atomic parameters.

        Returns:
            str: The complete delimiter string (e.g., " ; ", ", ", "/")
        """
        return self._build_delimiter(
            self.data.metadata_album_artist_separator,
            self.data.metadata_album_artist_space_before,
            self.data.metadata_album_artist_space_after,
        )

    def get_filename_artist_delimiter(self) -> str:
        """Construct the filename artist delimiter from atomic parameters.

        Returns:
            str: The complete delimiter string (e.g., " ; ", ", ", "/")
        """
        return self._build_delimiter(
            self.data.filename_artist_separator,
            self.data.filename_artist_space_before,
            self.data.filename_artist_space_after,
        )

    def get_filename_album_artist_delimiter(self) -> str:
        """Construct the filename album artist delimiter from atomic parameters.

        Returns:
            str: The complete delimiter string (e.g., " ; ", ", ", "/")
        """
        return self._build_delimiter(
            self.data.filename_album_artist_separator,
            self.data.filename_album_artist_space_before,
            self.data.filename_album_artist_space_after,
        )

    @staticmethod
    def _build_delimiter(separator: str, space_before: bool, space_after: bool) -> str:
        """Build a delimiter string from atomic components.

        Constructs the final delimiter string by combining the separator symbol
        with optional leading and/or trailing spaces based on configuration.

        Args:
            separator (str): The core separator symbol (e.g., ',', ';', '/').
            space_before (bool): Whether to add a space before the separator.
            space_after (bool): Whether to add a space after the separator.

        Returns:
            str: The complete delimiter string (e.g., " ; ", ", ", "/").

        Examples:
            >>> Settings._build_delimiter(",", False, True)
            ', '
            >>> Settings._build_delimiter(";", True, True)
            ' ; '
            >>> Settings._build_delimiter("/", False, False)
            '/'
        """
        space_prefix: str = " " if space_before else ""
        space_suffix: str = " " if space_after else ""
        return f"{space_prefix}{separator}{space_suffix}"


class Tidal(BaseConfig, metaclass=SingletonMeta):
    session: tidalapi.Session
    token_from_storage: bool = False
    settings: Settings
    is_pkce: bool

    def __init__(self, settings: Settings = None):
        self.cls_model = ModelToken
        tidal_config: tidalapi.Config = tidalapi.Config(item_limit=10000)
        self.session = tidalapi.Session(tidal_config)
        self.original_client_id = self.session.config.client_id
        self.original_client_secret = self.session.config.client_secret
        # Lock to ensure session-switching is thread-safe.
        # This lock protects against a race condition where one thread
        # changes the session credentials while another is using them.
        # It is intentionally held by Download._get_stream_info
        # for the *entire* duration of the credential switch AND
        # the get_stream() call.
        self.stream_lock = Lock()
        # State-tracking flag to prevent redundant, expensive
        # session re-authentication when the session is already in the
        # correct mode (Atmos or Normal).
        self.is_atmos_session = False
        # self.session.config.client_id = "km8T1xS355y7dd3H"
        # self.session.config.client_secret = "vcmeGW1OuZ0fWYMCSZ6vNvSLJlT3XEpW0ambgYt5ZuI="
        self.file_path = path_file_token()
        self.token_from_storage = self.read(self.file_path)

        if settings:
            self.settings = settings
            self.settings_apply()

    def settings_apply(self, settings: Settings = None) -> bool:
        if settings:
            self.settings = settings

        if not self.is_atmos_session:
            self.session.audio_quality = tidalapi.Quality(self.settings.data.quality_audio)
        self.session.video_quality = tidalapi.VideoQuality.high

        return True

    def login_token(self, do_pkce: bool = False) -> bool:
        """Attempt to login using stored token.

        Args:
            do_pkce (bool): Whether to use PKCE authorization. Defaults to False.

        Returns:
            bool: True if login successful, False otherwise.
        """
        import logging

        logger = logging.getLogger(__name__)
        result = False
        self.is_pkce = do_pkce

        if self.token_from_storage:
            try:
                logger.debug(f"Attempting to load OAuth session from stored token (PKCE: {do_pkce})")
                result = self.session.load_oauth_session(
                    self.data.token_type,
                    self.data.access_token,
                    self.data.refresh_token,
                    self.data.expiry_time,
                    is_pkce=do_pkce,
                )

                if result:
                    logger.info("Successfully loaded OAuth session from stored token")
                else:
                    logger.warning("Failed to load OAuth session - token might be expired")

            except Exception:
                result = False
                logger.exception("Exception during token login")

                # Remove token file. Probably corrupt or invalid.
                if os.path.exists(self.file_path):
                    logger.info(f"Removing potentially corrupt token file: {self.file_path}")
                    os.remove(self.file_path)

                print(
                    "Either there is something wrong with your credentials / account or some server problems on TIDALs "
                    "side. Anyway... Try to login again by re-starting this app."
                )
        else:
            logger.debug("No stored token found, fresh login required")

        return result

    def login_finalize(self) -> bool:
        """Finalize login by checking session and persisting token.

        Returns:
            bool: True if login check successful, False otherwise.
        """
        import logging

        logger = logging.getLogger(__name__)

        logger.debug("Checking login status...")
        result = self.session.check_login()

        if result:
            logger.info("Login check successful, persisting token")
            self.token_persist()
        else:
            logger.warning("Login check failed - session not authenticated")

        return result

    def token_persist(self) -> None:
        self.set_option("token_type", self.session.token_type)
        self.set_option("access_token", self.session.access_token)
        self.set_option("refresh_token", self.session.refresh_token)
        self.set_option("expiry_time", self.session.expiry_time)
        self.save()

    def switch_to_atmos_session(self) -> bool:
        """
        Switches the shared session to Dolby Atmos credentials.
        Only re-authenticates if not already in Atmos mode.

        Returns:
            bool: True if successful or already in Atmos mode, False otherwise.
        """
        # If we are already in Atmos mode, do nothing.
        if self.is_atmos_session:
            return True

        print("Switching session context to Dolby Atmos...")
        self.session.config.client_id = ATMOS_CLIENT_ID
        self.session.config.client_secret = ATMOS_CLIENT_SECRET
        self.session.audio_quality = ATMOS_REQUEST_QUALITY

        # Re-login with new credentials
        if not self.login_token(do_pkce=self.is_pkce):
            print("Warning: Atmos session authentication failed.")
            # Try to switch back to normal to be safe
            self.restore_normal_session(force=True)
            return False

        self.is_atmos_session = True  # Set the flag
        print("Session is now in Atmos mode.")
        return True

    def restore_normal_session(self, force: bool = False) -> bool:
        """
        Restores the shared session to the original user credentials.
        Only re-authenticates if not already in Normal mode.

        Args:
            force: If True, forces restoration even if already in Normal mode.

        Returns:
            bool: True if successful or already in Normal mode, False otherwise.
        """
        # If we are already in Normal mode (and not forced), do nothing.
        if not self.is_atmos_session and not force:
            return True

        print("Restoring session context to Normal...")
        self.session.config.client_id = self.original_client_id
        self.session.config.client_secret = self.original_client_secret

        # Explicitly restore audio quality to user's configured setting
        self.session.audio_quality = tidalapi.Quality(self.settings.data.quality_audio)

        # Re-login with original credentials
        if not self.login_token(do_pkce=self.is_pkce):
            print("Warning: Restoring the original session context failed. Please restart the application.")
            return False

        self.is_atmos_session = False  # Set the flag
        print("Session is now in Normal mode.")
        return True

    def login(self, fn_print: Callable) -> bool:
        is_token = self.login_token()
        result = False

        if is_token:
            fn_print("Yep, looks good! You are logged in.")

            result = True
        elif not is_token:
            fn_print("You either do not have a token or your token is invalid.")
            fn_print("No worries, we will handle this...")
            # Login method: Device linking
            self.session.login_oauth_simple(fn_print)
            # Login method: PKCE authorization (was necessary for HI_RES_LOSSLESS streaming earlier)
            # self.session.login_pkce(fn_print)

            is_login = self.login_finalize()

            if is_login:
                fn_print("The login was successful. I have stored your credentials (token).")

                result = True
            else:
                fn_print("Something went wrong. Did you login using your browser correctly? May try again...")

        return result

    def logout(self):
        Path(self.file_path).unlink(missing_ok=True)
        self.token_from_storage = False
        del self.session

        return True

    def is_authentication_error(self, error: Exception) -> bool:
        """Check if an error is related to authentication/OAuth issues.

        Args:
            error (Exception): The exception to check.

        Returns:
            bool: True if the error is authentication-related, False otherwise.
        """
        error_msg = str(error)
        return "401" in error_msg or "OAuth" in error_msg or "token" in error_msg.lower()


class HandlingApp(metaclass=SingletonMeta):
    event_abort: Event = Event()
    event_run: Event = Event()

    def __init__(self):
        self.event_run.set()
