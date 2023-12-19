from typing import Any

from collections.abc import Callable
from json import JSONDecodeError

import tidalapi
from tidal_dl_ng.helper.decorator import SingletonMeta
from tidal_dl_ng.helper.path import path_file_settings, path_file_token
from tidal_dl_ng.model.cfg import Settings as ModelSettings
from tidal_dl_ng.model.cfg import Token as ModelToken
from requests import HTTPError


class BaseConfig:
    data: ModelSettings | ModelToken = None
    file_path: str = None
    cls_model: object = None

    def save(self) -> None:
        data_json = self.data.to_json()

        with open(self.file_path, encoding="utf-8", mode="w") as f:
            f.write(data_json)

    def set_option(self, key: str, value: Any) -> None:
        setattr(self.data, key, value)

    def read(self, path: str) -> bool:
        result = False

        try:
            with open(path, encoding="utf-8") as f:
                settings_json = f.read()

            self.data = self.cls_model.from_json(settings_json)
            result = True
        except (JSONDecodeError, TypeError, FileNotFoundError):
            self.data = self.cls_model()
            self.save()

        return result


class Settings(BaseConfig, metaclass=SingletonMeta):
    cls_model = ModelSettings
    data = None

    def __init__(self):
        self.file_path = path_file_settings()
        self.read(self.file_path)


class Tidal(BaseConfig, metaclass=SingletonMeta):
    cls_model = ModelToken
    session: tidalapi.Session = None
    data: ModelToken = None
    token_from_storage: bool = False
    settings: Settings = None

    def __init__(self, settings: Settings = None):
        self.session = tidalapi.Session()
        self.session.video_quality = tidalapi.VideoQuality.high
        self.file_path = path_file_token()
        self.token_from_storage = self.read(self.file_path)
        self.login_token()

        if settings:
            self.settings = settings
            self.settings_apply()

    def settings_apply(self, settings: Settings = None) -> bool:
        if settings:
            self.settings = settings

        self.session.audio_quality = self.settings.data.quality_audio

        return True

    def login_token(self) -> bool:
        result = False

        if self.token_from_storage:
            try:
                result = self.session.load_oauth_session(
                    self.data.token_type, self.data.access_token, self.data.refresh_token, self.data.expiry_time
                )
            except HTTPError:
                result = False

        return result

    def login_oauth_start(self, function=print) -> None:
        self.session.login_oauth_simple(function)

    def login_oauth_finish(self) -> bool:
        result = self.session.check_login()

        if result:
            self.token_persist()

        return result

    def token_persist(self) -> None:
        self.set_option("token_type", self.session.token_type)
        self.set_option("access_token", self.session.access_token)
        self.set_option("refresh_token", self.session.refresh_token)
        self.set_option("expiry_time", self.session.expiry_time)
        self.save()

    def login(self, fn_print: Callable) -> bool:
        is_token = self.login_token()
        result = False

        if is_token:
            fn_print("Yep, looks good! You are logged in.")

            result = True
        elif not is_token:
            fn_print("You either do not have a token or your token is invalid.")
            fn_print("No worries, we will handle this...")
            self.login_oauth_start(fn_print)

            is_login = self.login_oauth_finish()

            if is_login:
                fn_print("The login was successful. I have stored your credentials (token).")

                result = True
            else:
                fn_print("Something went wrong. Did you login using your browser correctly? May try again...")

        return result
