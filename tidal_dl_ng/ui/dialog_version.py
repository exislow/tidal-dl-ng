################################################################################
## Form generated from reading UI file 'dialog_version.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QSpacerItem, QVBoxLayout


class Ui_DialogVersion:
    def setupUi(self, DialogVersion):
        if not DialogVersion.objectName():
            DialogVersion.setObjectName("DialogVersion")
        DialogVersion.resize(436, 235)
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(DialogVersion.sizePolicy().hasHeightForWidth())
        DialogVersion.setSizePolicy(sizePolicy)
        DialogVersion.setMaximumSize(QSize(436, 235))
        self.verticalLayout = QVBoxLayout(DialogVersion)
        self.verticalLayout.setObjectName("verticalLayout")
        self.l_name_app = QLabel(DialogVersion)
        self.l_name_app.setObjectName("l_name_app")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.l_name_app.sizePolicy().hasHeightForWidth())
        self.l_name_app.setSizePolicy(sizePolicy1)
        font = QFont()
        font.setBold(True)
        self.l_name_app.setFont(font)
        self.l_name_app.setAlignment(Qt.AlignCenter)
        self.l_name_app.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.TextSelectableByMouse)

        self.verticalLayout.addWidget(self.l_name_app)

        self.lv_version = QVBoxLayout()
        self.lv_version.setObjectName("lv_version")
        self.lh_version = QHBoxLayout()
        self.lh_version.setObjectName("lh_version")
        self.l_h_version = QLabel(DialogVersion)
        self.l_h_version.setObjectName("l_h_version")
        self.l_h_version.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.TextSelectableByMouse)

        self.lh_version.addWidget(self.l_h_version)

        self.l_version = QLabel(DialogVersion)
        self.l_version.setObjectName("l_version")
        self.l_version.setFont(font)
        self.l_version.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.TextSelectableByMouse)

        self.lh_version.addWidget(self.l_version)

        self.lv_version.addLayout(self.lh_version)

        self.verticalLayout.addLayout(self.lv_version)

        self.lv_update = QVBoxLayout()
        self.lv_update.setObjectName("lv_update")
        self.l_error = QLabel(DialogVersion)
        self.l_error.setObjectName("l_error")
        self.l_error.setFont(font)
        self.l_error.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.TextSelectableByMouse)

        self.lv_update.addWidget(self.l_error)

        self.l_error_details = QLabel(DialogVersion)
        self.l_error_details.setObjectName("l_error_details")
        self.l_error_details.setFont(font)
        self.l_error_details.setAlignment(Qt.AlignCenter)
        self.l_error_details.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.TextSelectableByMouse)

        self.lv_update.addWidget(self.l_error_details)

        self.lh_update_version = QHBoxLayout()
        self.lh_update_version.setObjectName("lh_update_version")
        self.l_h_version_new = QLabel(DialogVersion)
        self.l_h_version_new.setObjectName("l_h_version_new")
        self.l_h_version_new.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.TextSelectableByMouse)

        self.lh_update_version.addWidget(self.l_h_version_new)

        self.l_version_new = QLabel(DialogVersion)
        self.l_version_new.setObjectName("l_version_new")
        self.l_version_new.setFont(font)
        self.l_version_new.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.TextSelectableByMouse)

        self.lh_update_version.addWidget(self.l_version_new)

        self.lv_update.addLayout(self.lh_update_version)

        self.l_changelog = QLabel(DialogVersion)
        self.l_changelog.setObjectName("l_changelog")
        self.l_changelog.setFont(font)
        self.l_changelog.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.TextSelectableByMouse)

        self.lv_update.addWidget(self.l_changelog)

        self.l_changelog_details = QLabel(DialogVersion)
        self.l_changelog_details.setObjectName("l_changelog_details")
        self.l_changelog_details.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.TextSelectableByMouse)

        self.lv_update.addWidget(self.l_changelog_details)

        self.lv_download = QHBoxLayout()
        self.lv_download.setObjectName("lv_download")
        self.lv_download.setContentsMargins(-1, 20, -1, -1)
        self.pb_download = QPushButton(DialogVersion)
        self.pb_download.setObjectName("pb_download")
        self.pb_download.setFlat(False)

        self.lv_download.addWidget(self.pb_download)

        self.sh_download = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.lv_download.addItem(self.sh_download)

        self.lv_update.addLayout(self.lv_download)

        self.verticalLayout.addLayout(self.lv_update)

        self.l_url_github = QLabel(DialogVersion)
        self.l_url_github.setObjectName("l_url_github")
        self.l_url_github.setAlignment(Qt.AlignRight | Qt.AlignTrailing | Qt.AlignVCenter)
        self.l_url_github.setOpenExternalLinks(True)
        self.l_url_github.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.TextSelectableByMouse)

        self.verticalLayout.addWidget(self.l_url_github)

        self.retranslateUi(DialogVersion)

        QMetaObject.connectSlotsByName(DialogVersion)

    # setupUi

    def retranslateUi(self, DialogVersion):
        DialogVersion.setWindowTitle(QCoreApplication.translate("DialogVersion", "Version", None))
        self.l_name_app.setText(QCoreApplication.translate("DialogVersion", "TIDAL Downloader Next Generation!", None))
        self.l_h_version.setText(QCoreApplication.translate("DialogVersion", "Installed Version:", None))
        self.l_version.setText(QCoreApplication.translate("DialogVersion", "v1.2.3", None))
        self.l_error.setText(QCoreApplication.translate("DialogVersion", "ERROR", None))
        self.l_error_details.setText(QCoreApplication.translate("DialogVersion", "<ERROR>", None))
        self.l_h_version_new.setText(QCoreApplication.translate("DialogVersion", "New Version Available:", None))
        self.l_version_new.setText(QCoreApplication.translate("DialogVersion", "v0.0.0", None))
        self.l_changelog.setText(QCoreApplication.translate("DialogVersion", "Changelog", None))
        self.l_changelog_details.setText(QCoreApplication.translate("DialogVersion", "<CHANGELOG>", None))
        self.pb_download.setText(QCoreApplication.translate("DialogVersion", "Download", None))
        self.l_url_github.setText(
            QCoreApplication.translate(
                "DialogVersion",
                '<a href="https://github.com/exislow/tidal-dl-ng/">https://github.com/exislow/tidal-dl-ng/</a>',
                None,
            )
        )

    # retranslateUi
