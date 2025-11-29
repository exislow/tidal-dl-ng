################################################################################
## Form generated from reading UI file 'dialog_history.ui'
##
## Created by: Qt User Interface Compiler version 6.10.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QTreeWidget,
    QVBoxLayout,
)


class Ui_DialogHistory:
    def setupUi(self, DialogHistory):
        if not DialogHistory.objectName():
            DialogHistory.setObjectName("DialogHistory")
        DialogHistory.resize(900, 600)
        self.verticalLayout = QVBoxLayout(DialogHistory)
        self.verticalLayout.setObjectName("verticalLayout")
        self.l_info = QLabel(DialogHistory)
        self.l_info.setObjectName("l_info")
        self.l_info.setWordWrap(True)

        self.verticalLayout.addWidget(self.l_info)

        self.gb_file_info = QGroupBox(DialogHistory)
        self.gb_file_info.setObjectName("gb_file_info")
        self.horizontalLayout = QHBoxLayout(self.gb_file_info)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.le_file_path = QLineEdit(self.gb_file_info)
        self.le_file_path.setObjectName("le_file_path")
        self.le_file_path.setReadOnly(True)

        self.horizontalLayout.addWidget(self.le_file_path)

        self.pb_open_folder = QPushButton(self.gb_file_info)
        self.pb_open_folder.setObjectName("pb_open_folder")

        self.horizontalLayout.addWidget(self.pb_open_folder)

        self.verticalLayout.addWidget(self.gb_file_info)

        self.gb_statistics = QGroupBox(DialogHistory)
        self.gb_statistics.setObjectName("gb_statistics")
        self.horizontalLayout_2 = QHBoxLayout(self.gb_statistics)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.l_total_tracks = QLabel(self.gb_statistics)
        self.l_total_tracks.setObjectName("l_total_tracks")

        self.horizontalLayout_2.addWidget(self.l_total_tracks)

        self.l_by_albums = QLabel(self.gb_statistics)
        self.l_by_albums.setObjectName("l_by_albums")

        self.horizontalLayout_2.addWidget(self.l_by_albums)

        self.l_by_playlists = QLabel(self.gb_statistics)
        self.l_by_playlists.setObjectName("l_by_playlists")

        self.horizontalLayout_2.addWidget(self.l_by_playlists)

        self.l_by_mixes = QLabel(self.gb_statistics)
        self.l_by_mixes.setObjectName("l_by_mixes")

        self.horizontalLayout_2.addWidget(self.l_by_mixes)

        self.l_by_manual = QLabel(self.gb_statistics)
        self.l_by_manual.setObjectName("l_by_manual")

        self.horizontalLayout_2.addWidget(self.l_by_manual)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.verticalLayout.addWidget(self.gb_statistics)

        self.tw_history = QTreeWidget(DialogHistory)
        self.tw_history.setObjectName("tw_history")
        self.tw_history.setAlternatingRowColors(True)
        self.tw_history.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tw_history.setSortingEnabled(True)

        self.verticalLayout.addWidget(self.tw_history)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.pb_export = QPushButton(DialogHistory)
        self.pb_export.setObjectName("pb_export")

        self.horizontalLayout_3.addWidget(self.pb_export)

        self.pb_import = QPushButton(DialogHistory)
        self.pb_import.setObjectName("pb_import")

        self.horizontalLayout_3.addWidget(self.pb_import)

        self.pb_clear_history = QPushButton(DialogHistory)
        self.pb_clear_history.setObjectName("pb_clear_history")
        self.pb_clear_history.setStyleSheet("background-color: #dc3545; color: white;")

        self.horizontalLayout_3.addWidget(self.pb_clear_history)

        self.pb_remove_selected = QPushButton(DialogHistory)
        self.pb_remove_selected.setObjectName("pb_remove_selected")

        self.horizontalLayout_3.addWidget(self.pb_remove_selected)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_2)

        self.pb_refresh = QPushButton(DialogHistory)
        self.pb_refresh.setObjectName("pb_refresh")

        self.horizontalLayout_3.addWidget(self.pb_refresh)

        self.pb_close = QPushButton(DialogHistory)
        self.pb_close.setObjectName("pb_close")

        self.horizontalLayout_3.addWidget(self.pb_close)

        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.retranslateUi(DialogHistory)

        QMetaObject.connectSlotsByName(DialogHistory)

    # setupUi

    def retranslateUi(self, DialogHistory):
        DialogHistory.setWindowTitle(QCoreApplication.translate("DialogHistory", "Download History", None))
        self.l_info.setText(
            QCoreApplication.translate(
                "DialogHistory",
                "View and manage your download history. Tracks are grouped by source (album, playlist, mix).",
                None,
            )
        )
        self.gb_file_info.setTitle(QCoreApplication.translate("DialogHistory", "History File Location", None))
        self.pb_open_folder.setText(QCoreApplication.translate("DialogHistory", "Open Folder", None))
        self.gb_statistics.setTitle(QCoreApplication.translate("DialogHistory", "Statistics", None))
        self.l_total_tracks.setText(QCoreApplication.translate("DialogHistory", "Total Tracks: 0", None))
        self.l_by_albums.setText(QCoreApplication.translate("DialogHistory", "Albums: 0", None))
        self.l_by_playlists.setText(QCoreApplication.translate("DialogHistory", "Playlists: 0", None))
        self.l_by_mixes.setText(QCoreApplication.translate("DialogHistory", "Mixes: 0", None))
        self.l_by_manual.setText(QCoreApplication.translate("DialogHistory", "Manual: 0", None))
        ___qtreewidgetitem = self.tw_history.headerItem()
        ___qtreewidgetitem.setText(3, QCoreApplication.translate("DialogHistory", "Track ID", None))
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("DialogHistory", "Download Date", None))
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("DialogHistory", "Type", None))
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("DialogHistory", "Source / Track", None))
        self.pb_export.setText(QCoreApplication.translate("DialogHistory", "Export...", None))
        self.pb_import.setText(QCoreApplication.translate("DialogHistory", "Import...", None))
        self.pb_clear_history.setText(QCoreApplication.translate("DialogHistory", "Clear History", None))
        self.pb_remove_selected.setText(QCoreApplication.translate("DialogHistory", "Remove Selected", None))
        self.pb_refresh.setText(QCoreApplication.translate("DialogHistory", "Refresh", None))
        self.pb_close.setText(QCoreApplication.translate("DialogHistory", "Close", None))

    # retranslateUi
