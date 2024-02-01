from PySide6.QtWidgets import QDialog

from tidal_dl_ng import __version__
from tidal_dl_ng.ui.dialog_login import Ui_DialogLogin
from tidal_dl_ng.ui.dialog_version import Ui_DialogVersion


class DialogVersion(QDialog):
    """Version dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Create an instance of the GUI
        self.ui = Ui_DialogVersion()

        # Run the .setupUi() method to show the GUI
        self.ui.setupUi(self)
        # Set the version.
        self.ui.l_version.setText("v" + __version__)
        # Show
        self.exec()


class DialogLogin(QDialog):
    """Version dialog."""

    url_redirect: str
    return_code: int

    def __init__(self, url_login: str, hint: str, parent=None):
        super().__init__(parent)

        # Create an instance of the GUI
        self.ui = Ui_DialogLogin()

        # Run the .setupUi() method to show the GUI
        self.ui.setupUi(self)
        # Set data.
        self.ui.l_url_login.setText(f'<a href="{url_login}">{url_login}</a>')
        self.ui.l_hint.setText(hint)
        # Show
        self.return_code = self.exec()

        self.url_redirect = self.ui.te_url_redirect.toPlainText()

    def accept1(self):
        pass
