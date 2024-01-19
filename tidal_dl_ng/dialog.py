from PySide6.QtWidgets import QDialog

from tidal_dl_ng import __version__
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

        self.exec()
