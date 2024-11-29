################################################################################
## Form generated from reading UI file 'dialog_login.ui'
##
## Created by: Qt User Interface Compiler version 6.8.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QRect, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QDialogButtonBox, QHBoxLayout, QLabel, QSizePolicy, QTextBrowser, QVBoxLayout, QWidget


class Ui_DialogLogin:
    def setupUi(self, DialogLogin):
        if not DialogLogin.objectName():
            DialogLogin.setObjectName("DialogLogin")
        DialogLogin.resize(451, 400)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(DialogLogin.sizePolicy().hasHeightForWidth())
        DialogLogin.setSizePolicy(sizePolicy)
        self.bb_dialog = QDialogButtonBox(DialogLogin)
        self.bb_dialog.setObjectName("bb_dialog")
        self.bb_dialog.setGeometry(QRect(20, 350, 411, 32))
        sizePolicy.setHeightForWidth(self.bb_dialog.sizePolicy().hasHeightForWidth())
        self.bb_dialog.setSizePolicy(sizePolicy)
        self.bb_dialog.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.bb_dialog.setStyleSheet("")
        self.bb_dialog.setOrientation(Qt.Orientation.Horizontal)
        self.bb_dialog.setStandardButtons(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        self.verticalLayoutWidget = QWidget(DialogLogin)
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayoutWidget.setGeometry(QRect(20, 20, 411, 325))
        self.lv_main = QVBoxLayout(self.verticalLayoutWidget)
        self.lv_main.setObjectName("lv_main")
        self.lv_main.setContentsMargins(0, 0, 0, 0)
        self.l_header = QLabel(self.verticalLayoutWidget)
        self.l_header.setObjectName("l_header")
        sizePolicy.setHeightForWidth(self.l_header.sizePolicy().hasHeightForWidth())
        self.l_header.setSizePolicy(sizePolicy)
        font = QFont()
        font.setPointSize(23)
        font.setBold(True)
        self.l_header.setFont(font)

        self.lv_main.addWidget(self.l_header)

        self.l_description = QLabel(self.verticalLayoutWidget)
        self.l_description.setObjectName("l_description")
        sizePolicy.setHeightForWidth(self.l_description.sizePolicy().hasHeightForWidth())
        self.l_description.setSizePolicy(sizePolicy)
        font1 = QFont()
        font1.setItalic(True)
        self.l_description.setFont(font1)
        self.l_description.setWordWrap(True)

        self.lv_main.addWidget(self.l_description)

        self.tb_url_login = QTextBrowser(self.verticalLayoutWidget)
        self.tb_url_login.setObjectName("tb_url_login")
        self.tb_url_login.setOpenExternalLinks(True)

        self.lv_main.addWidget(self.tb_url_login)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.l_expires_description = QLabel(self.verticalLayoutWidget)
        self.l_expires_description.setObjectName("l_expires_description")

        self.horizontalLayout.addWidget(self.l_expires_description)

        self.l_expires_date_time = QLabel(self.verticalLayoutWidget)
        self.l_expires_date_time.setObjectName("l_expires_date_time")
        font2 = QFont()
        font2.setBold(True)
        self.l_expires_date_time.setFont(font2)
        self.l_expires_date_time.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTrailing | Qt.AlignmentFlag.AlignVCenter
        )

        self.horizontalLayout.addWidget(self.l_expires_date_time)

        self.lv_main.addLayout(self.horizontalLayout)

        self.l_hint = QLabel(self.verticalLayoutWidget)
        self.l_hint.setObjectName("l_hint")
        sizePolicy.setHeightForWidth(self.l_hint.sizePolicy().hasHeightForWidth())
        self.l_hint.setSizePolicy(sizePolicy)
        self.l_hint.setFont(font1)
        self.l_hint.setWordWrap(True)

        self.lv_main.addWidget(self.l_hint)

        self.retranslateUi(DialogLogin)
        self.bb_dialog.accepted.connect(DialogLogin.accept)
        self.bb_dialog.rejected.connect(DialogLogin.reject)

        QMetaObject.connectSlotsByName(DialogLogin)

    # setupUi

    def retranslateUi(self, DialogLogin):
        DialogLogin.setWindowTitle(QCoreApplication.translate("DialogLogin", "Dialog", None))
        self.l_header.setText(QCoreApplication.translate("DialogLogin", "TIDAL Login (as Device)", None))
        self.l_description.setText(
            QCoreApplication.translate(
                "DialogLogin",
                "Click the link below and login with your TIDAL credentials. TIDAL will ask you, if you like to add this app as a new device. You need to confirm this.",
                None,
            )
        )
        self.tb_url_login.setPlaceholderText(QCoreApplication.translate("DialogLogin", "Copy this login URL...", None))
        self.l_expires_description.setText(QCoreApplication.translate("DialogLogin", "This link expires at:", None))
        self.l_expires_date_time.setText(QCoreApplication.translate("DialogLogin", "COMPUTING", None))
        self.l_hint.setText(QCoreApplication.translate("DialogLogin", "Waiting...", None))

    # retranslateUi
