################################################################################
## Form generated from reading UI file 'dialog_version.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QRect
from PySide6.QtWidgets import QLabel


class Ui_DialogVersion:
    def setupUi(self, DialogVersion):
        if not DialogVersion.objectName():
            DialogVersion.setObjectName("DialogVersion")
        DialogVersion.resize(436, 235)
        self.l_version = QLabel(DialogVersion)
        self.l_version.setObjectName("l_version")
        self.l_version.setGeometry(QRect(190, 100, 61, 16))
        self.l_url_github = QLabel(DialogVersion)
        self.l_url_github.setObjectName("l_url_github")
        self.l_url_github.setGeometry(QRect(160, 200, 251, 20))
        self.l_url_github.setOpenExternalLinks(True)
        self.l_name_app = QLabel(DialogVersion)
        self.l_name_app.setObjectName("l_name_app")
        self.l_name_app.setGeometry(QRect(110, 30, 231, 16))

        self.retranslateUi(DialogVersion)

        QMetaObject.connectSlotsByName(DialogVersion)

    # setupUi

    def retranslateUi(self, DialogVersion):
        DialogVersion.setWindowTitle(QCoreApplication.translate("DialogVersion", "Version", None))
        self.l_version.setText(QCoreApplication.translate("DialogVersion", "v1.2.3", None))
        self.l_url_github.setText(
            QCoreApplication.translate(
                "DialogVersion",
                '<a href="https://github.com/exislow/tidal-dl-ng/">https://github.com/exislow/tidal-dl-ng/</a>',
                None,
            )
        )
        self.l_name_app.setText(QCoreApplication.translate("DialogVersion", "TIDAL Downloader Next Generation", None))

    # retranslateUi
