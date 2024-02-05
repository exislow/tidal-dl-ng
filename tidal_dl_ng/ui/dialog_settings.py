################################################################################
## Form generated from reading UI file 'dialog_settings.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)


class Ui_DialogSettings:
    def setupUi(self, DialogSettings):
        if not DialogSettings.objectName():
            DialogSettings.setObjectName("DialogSettings")
        DialogSettings.resize(640, 682)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(100)
        sizePolicy.setVerticalStretch(100)
        sizePolicy.setHeightForWidth(DialogSettings.sizePolicy().hasHeightForWidth())
        DialogSettings.setSizePolicy(sizePolicy)
        DialogSettings.setSizeGripEnabled(True)
        self.lv_dialog_settings = QVBoxLayout(DialogSettings)
        self.lv_dialog_settings.setObjectName("lv_dialog_settings")
        self.lv_dialog_settings.setContentsMargins(0, 0, 0, 0)
        self.lv_main = QVBoxLayout()
        self.lv_main.setObjectName("lv_main")
        self.lv_main.setContentsMargins(12, 12, 12, 12)
        self.gb_flags = QGroupBox(DialogSettings)
        self.gb_flags.setObjectName("gb_flags")
        sizePolicy1 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy1.setHorizontalStretch(100)
        sizePolicy1.setVerticalStretch(100)
        sizePolicy1.setHeightForWidth(self.gb_flags.sizePolicy().hasHeightForWidth())
        self.gb_flags.setSizePolicy(sizePolicy1)
        self.gb_flags.setFlat(False)
        self.gb_flags.setCheckable(False)
        self.lv_flags = QVBoxLayout(self.gb_flags)
        self.lv_flags.setObjectName("lv_flags")
        self.lh_flags_1 = QHBoxLayout()
        self.lh_flags_1.setObjectName("lh_flags_1")
        self.lv_flags_video_download = QVBoxLayout()
        self.lv_flags_video_download.setObjectName("lv_flags_video_download")
        self.cb_video_download = QCheckBox(self.gb_flags)
        self.cb_video_download.setObjectName("cb_video_download")
        sizePolicy1.setHeightForWidth(self.cb_video_download.sizePolicy().hasHeightForWidth())
        self.cb_video_download.setSizePolicy(sizePolicy1)

        self.lv_flags_video_download.addWidget(self.cb_video_download)

        self.lh_flags_1.addLayout(self.lv_flags_video_download)

        self.lv_flags_video_convert = QVBoxLayout()
        self.lv_flags_video_convert.setObjectName("lv_flags_video_convert")
        self.cb_video_convert_mp4 = QCheckBox(self.gb_flags)
        self.cb_video_convert_mp4.setObjectName("cb_video_convert_mp4")
        sizePolicy1.setHeightForWidth(self.cb_video_convert_mp4.sizePolicy().hasHeightForWidth())
        self.cb_video_convert_mp4.setSizePolicy(sizePolicy1)

        self.lv_flags_video_convert.addWidget(self.cb_video_convert_mp4)

        self.lh_flags_1.addLayout(self.lv_flags_video_convert)

        self.lv_flags.addLayout(self.lh_flags_1)

        self.lh_flags_2 = QHBoxLayout()
        self.lh_flags_2.setObjectName("lh_flags_2")
        self.lh_flags_lyrics_embed = QHBoxLayout()
        self.lh_flags_lyrics_embed.setObjectName("lh_flags_lyrics_embed")
        self.cb_lyrics_embed = QCheckBox(self.gb_flags)
        self.cb_lyrics_embed.setObjectName("cb_lyrics_embed")
        sizePolicy2 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.cb_lyrics_embed.sizePolicy().hasHeightForWidth())
        self.cb_lyrics_embed.setSizePolicy(sizePolicy2)

        self.lh_flags_lyrics_embed.addWidget(self.cb_lyrics_embed)

        self.lh_flags_2.addLayout(self.lh_flags_lyrics_embed)

        self.lh_flags_lyrics_file = QHBoxLayout()
        self.lh_flags_lyrics_file.setObjectName("lh_flags_lyrics_file")
        self.cb_lyrics_file = QCheckBox(self.gb_flags)
        self.cb_lyrics_file.setObjectName("cb_lyrics_file")
        sizePolicy1.setHeightForWidth(self.cb_lyrics_file.sizePolicy().hasHeightForWidth())
        self.cb_lyrics_file.setSizePolicy(sizePolicy1)

        self.lh_flags_lyrics_file.addWidget(self.cb_lyrics_file)

        self.lh_flags_2.addLayout(self.lh_flags_lyrics_file)

        self.lv_flags.addLayout(self.lh_flags_2)

        self.lh_flag_3 = QHBoxLayout()
        self.lh_flag_3.setObjectName("lh_flag_3")
        self.lv_flag_download_delay = QVBoxLayout()
        self.lv_flag_download_delay.setObjectName("lv_flag_download_delay")
        self.cb_download_delay = QCheckBox(self.gb_flags)
        self.cb_download_delay.setObjectName("cb_download_delay")
        sizePolicy1.setHeightForWidth(self.cb_download_delay.sizePolicy().hasHeightForWidth())
        self.cb_download_delay.setSizePolicy(sizePolicy1)

        self.lv_flag_download_delay.addWidget(self.cb_download_delay)

        self.lh_flag_3.addLayout(self.lv_flag_download_delay)

        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName("verticalLayout_4")

        self.lh_flag_3.addLayout(self.verticalLayout_4)

        self.lv_flags.addLayout(self.lh_flag_3)

        self.lv_main.addWidget(self.gb_flags)

        self.gb_choices = QGroupBox(DialogSettings)
        self.gb_choices.setObjectName("gb_choices")
        sizePolicy3 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.gb_choices.sizePolicy().hasHeightForWidth())
        self.gb_choices.setSizePolicy(sizePolicy3)
        self.lv_choices = QVBoxLayout(self.gb_choices)
        self.lv_choices.setObjectName("lv_choices")
        self.lh_choices_skip_existing = QHBoxLayout()
        self.lh_choices_skip_existing.setObjectName("lh_choices_skip_existing")
        self.l_icon_skip_existing = QLabel(self.gb_choices)
        self.l_icon_skip_existing.setObjectName("l_icon_skip_existing")
        sizePolicy4 = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.l_icon_skip_existing.sizePolicy().hasHeightForWidth())
        self.l_icon_skip_existing.setSizePolicy(sizePolicy4)

        self.lh_choices_skip_existing.addWidget(self.l_icon_skip_existing)

        self.l_skip_existing = QLabel(self.gb_choices)
        self.l_skip_existing.setObjectName("l_skip_existing")
        sizePolicy4.setHeightForWidth(self.l_skip_existing.sizePolicy().hasHeightForWidth())
        self.l_skip_existing.setSizePolicy(sizePolicy4)

        self.lh_choices_skip_existing.addWidget(self.l_skip_existing)

        self.c_skip_existing = QComboBox(self.gb_choices)
        self.c_skip_existing.setObjectName("c_skip_existing")

        self.lh_choices_skip_existing.addWidget(self.c_skip_existing)

        self.lh_choices_skip_existing.setStretch(2, 50)

        self.lv_choices.addLayout(self.lh_choices_skip_existing)

        self.lh_choices_quality_audio = QHBoxLayout()
        self.lh_choices_quality_audio.setObjectName("lh_choices_quality_audio")
        self.l_icon_quality_audio = QLabel(self.gb_choices)
        self.l_icon_quality_audio.setObjectName("l_icon_quality_audio")
        sizePolicy4.setHeightForWidth(self.l_icon_quality_audio.sizePolicy().hasHeightForWidth())
        self.l_icon_quality_audio.setSizePolicy(sizePolicy4)

        self.lh_choices_quality_audio.addWidget(self.l_icon_quality_audio)

        self.l_quality_audio = QLabel(self.gb_choices)
        self.l_quality_audio.setObjectName("l_quality_audio")
        sizePolicy4.setHeightForWidth(self.l_quality_audio.sizePolicy().hasHeightForWidth())
        self.l_quality_audio.setSizePolicy(sizePolicy4)

        self.lh_choices_quality_audio.addWidget(self.l_quality_audio)

        self.c_quality_audio = QComboBox(self.gb_choices)
        self.c_quality_audio.setObjectName("c_quality_audio")

        self.lh_choices_quality_audio.addWidget(self.c_quality_audio)

        self.lh_choices_quality_audio.setStretch(2, 50)

        self.lv_choices.addLayout(self.lh_choices_quality_audio)

        self.lh_choices_quality_video = QHBoxLayout()
        self.lh_choices_quality_video.setObjectName("lh_choices_quality_video")
        self.l_icon_quality_video = QLabel(self.gb_choices)
        self.l_icon_quality_video.setObjectName("l_icon_quality_video")
        sizePolicy4.setHeightForWidth(self.l_icon_quality_video.sizePolicy().hasHeightForWidth())
        self.l_icon_quality_video.setSizePolicy(sizePolicy4)

        self.lh_choices_quality_video.addWidget(self.l_icon_quality_video)

        self.l_quality_video = QLabel(self.gb_choices)
        self.l_quality_video.setObjectName("l_quality_video")
        sizePolicy4.setHeightForWidth(self.l_quality_video.sizePolicy().hasHeightForWidth())
        self.l_quality_video.setSizePolicy(sizePolicy4)

        self.lh_choices_quality_video.addWidget(self.l_quality_video)

        self.c_quality_video = QComboBox(self.gb_choices)
        self.c_quality_video.setObjectName("c_quality_video")

        self.lh_choices_quality_video.addWidget(self.c_quality_video)

        self.lh_choices_quality_video.setStretch(2, 50)

        self.lv_choices.addLayout(self.lh_choices_quality_video)

        self.lh_choices_cover_dimension = QHBoxLayout()
        self.lh_choices_cover_dimension.setObjectName("lh_choices_cover_dimension")
        self.lh_choices_cover_dimension.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.l_icon_metadata_cover_dimension = QLabel(self.gb_choices)
        self.l_icon_metadata_cover_dimension.setObjectName("l_icon_metadata_cover_dimension")
        sizePolicy4.setHeightForWidth(self.l_icon_metadata_cover_dimension.sizePolicy().hasHeightForWidth())
        self.l_icon_metadata_cover_dimension.setSizePolicy(sizePolicy4)

        self.lh_choices_cover_dimension.addWidget(self.l_icon_metadata_cover_dimension)

        self.l_metadata_cover_dimension = QLabel(self.gb_choices)
        self.l_metadata_cover_dimension.setObjectName("l_metadata_cover_dimension")
        sizePolicy4.setHeightForWidth(self.l_metadata_cover_dimension.sizePolicy().hasHeightForWidth())
        self.l_metadata_cover_dimension.setSizePolicy(sizePolicy4)

        self.lh_choices_cover_dimension.addWidget(self.l_metadata_cover_dimension)

        self.c_metadata_cover_dimension = QComboBox(self.gb_choices)
        self.c_metadata_cover_dimension.setObjectName("c_metadata_cover_dimension")
        sizePolicy5 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        sizePolicy5.setHorizontalStretch(10)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.c_metadata_cover_dimension.sizePolicy().hasHeightForWidth())
        self.c_metadata_cover_dimension.setSizePolicy(sizePolicy5)

        self.lh_choices_cover_dimension.addWidget(self.c_metadata_cover_dimension)

        self.lh_choices_cover_dimension.setStretch(2, 50)

        self.lv_choices.addLayout(self.lh_choices_cover_dimension)

        self.lv_main.addWidget(self.gb_choices)

        self.gb_path = QGroupBox(DialogSettings)
        self.gb_path.setObjectName("gb_path")
        self.horizontalLayout_2 = QHBoxLayout(self.gb_path)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.lh_path_base = QHBoxLayout()
        self.lh_path_base.setObjectName("lh_path_base")
        self.l_icon_download_base_path = QLabel(self.gb_path)
        self.l_icon_download_base_path.setObjectName("l_icon_download_base_path")
        sizePolicy4.setHeightForWidth(self.l_icon_download_base_path.sizePolicy().hasHeightForWidth())
        self.l_icon_download_base_path.setSizePolicy(sizePolicy4)

        self.lh_path_base.addWidget(self.l_icon_download_base_path)

        self.l_download_base_path = QLabel(self.gb_path)
        self.l_download_base_path.setObjectName("l_download_base_path")
        sizePolicy3.setHeightForWidth(self.l_download_base_path.sizePolicy().hasHeightForWidth())
        self.l_download_base_path.setSizePolicy(sizePolicy3)

        self.lh_path_base.addWidget(self.l_download_base_path)

        self.verticalLayout_2.addLayout(self.lh_path_base)

        self.lh_path_fmt_track = QHBoxLayout()
        self.lh_path_fmt_track.setObjectName("lh_path_fmt_track")
        self.l_icon_format_track = QLabel(self.gb_path)
        self.l_icon_format_track.setObjectName("l_icon_format_track")
        sizePolicy4.setHeightForWidth(self.l_icon_format_track.sizePolicy().hasHeightForWidth())
        self.l_icon_format_track.setSizePolicy(sizePolicy4)

        self.lh_path_fmt_track.addWidget(self.l_icon_format_track)

        self.l_format_track = QLabel(self.gb_path)
        self.l_format_track.setObjectName("l_format_track")
        sizePolicy3.setHeightForWidth(self.l_format_track.sizePolicy().hasHeightForWidth())
        self.l_format_track.setSizePolicy(sizePolicy3)

        self.lh_path_fmt_track.addWidget(self.l_format_track)

        self.verticalLayout_2.addLayout(self.lh_path_fmt_track)

        self.lh_path_fmt_video = QHBoxLayout()
        self.lh_path_fmt_video.setObjectName("lh_path_fmt_video")
        self.l_icon_format_video = QLabel(self.gb_path)
        self.l_icon_format_video.setObjectName("l_icon_format_video")
        sizePolicy4.setHeightForWidth(self.l_icon_format_video.sizePolicy().hasHeightForWidth())
        self.l_icon_format_video.setSizePolicy(sizePolicy4)

        self.lh_path_fmt_video.addWidget(self.l_icon_format_video)

        self.l_format_video = QLabel(self.gb_path)
        self.l_format_video.setObjectName("l_format_video")
        sizePolicy3.setHeightForWidth(self.l_format_video.sizePolicy().hasHeightForWidth())
        self.l_format_video.setSizePolicy(sizePolicy3)

        self.lh_path_fmt_video.addWidget(self.l_format_video)

        self.verticalLayout_2.addLayout(self.lh_path_fmt_video)

        self.lh_path_fmt_album = QHBoxLayout()
        self.lh_path_fmt_album.setObjectName("lh_path_fmt_album")
        self.l_icon_format_album = QLabel(self.gb_path)
        self.l_icon_format_album.setObjectName("l_icon_format_album")
        sizePolicy6 = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        sizePolicy6.setHorizontalStretch(0)
        sizePolicy6.setVerticalStretch(0)
        sizePolicy6.setHeightForWidth(self.l_icon_format_album.sizePolicy().hasHeightForWidth())
        self.l_icon_format_album.setSizePolicy(sizePolicy6)

        self.lh_path_fmt_album.addWidget(self.l_icon_format_album)

        self.l_format_album = QLabel(self.gb_path)
        self.l_format_album.setObjectName("l_format_album")
        sizePolicy3.setHeightForWidth(self.l_format_album.sizePolicy().hasHeightForWidth())
        self.l_format_album.setSizePolicy(sizePolicy3)

        self.lh_path_fmt_album.addWidget(self.l_format_album)

        self.verticalLayout_2.addLayout(self.lh_path_fmt_album)

        self.lh_fpath_mt_playlist = QHBoxLayout()
        self.lh_fpath_mt_playlist.setObjectName("lh_fpath_mt_playlist")
        self.l_icon_format_playlist = QLabel(self.gb_path)
        self.l_icon_format_playlist.setObjectName("l_icon_format_playlist")
        sizePolicy4.setHeightForWidth(self.l_icon_format_playlist.sizePolicy().hasHeightForWidth())
        self.l_icon_format_playlist.setSizePolicy(sizePolicy4)

        self.lh_fpath_mt_playlist.addWidget(self.l_icon_format_playlist)

        self.l_format_playlist = QLabel(self.gb_path)
        self.l_format_playlist.setObjectName("l_format_playlist")
        sizePolicy3.setHeightForWidth(self.l_format_playlist.sizePolicy().hasHeightForWidth())
        self.l_format_playlist.setSizePolicy(sizePolicy3)

        self.lh_fpath_mt_playlist.addWidget(self.l_format_playlist)

        self.verticalLayout_2.addLayout(self.lh_fpath_mt_playlist)

        self.lh_path_fmt_mix = QHBoxLayout()
        self.lh_path_fmt_mix.setObjectName("lh_path_fmt_mix")
        self.l_icon_format_mix = QLabel(self.gb_path)
        self.l_icon_format_mix.setObjectName("l_icon_format_mix")
        sizePolicy6.setHeightForWidth(self.l_icon_format_mix.sizePolicy().hasHeightForWidth())
        self.l_icon_format_mix.setSizePolicy(sizePolicy6)

        self.lh_path_fmt_mix.addWidget(self.l_icon_format_mix)

        self.l_format_mix = QLabel(self.gb_path)
        self.l_format_mix.setObjectName("l_format_mix")
        sizePolicy3.setHeightForWidth(self.l_format_mix.sizePolicy().hasHeightForWidth())
        self.l_format_mix.setSizePolicy(sizePolicy3)

        self.lh_path_fmt_mix.addWidget(self.l_format_mix)

        self.verticalLayout_2.addLayout(self.lh_path_fmt_mix)

        self.horizontalLayout_2.addLayout(self.verticalLayout_2)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.le_download_base_path = QLineEdit(self.gb_path)
        self.le_download_base_path.setObjectName("le_download_base_path")
        sizePolicy2.setHeightForWidth(self.le_download_base_path.sizePolicy().hasHeightForWidth())
        self.le_download_base_path.setSizePolicy(sizePolicy2)
        self.le_download_base_path.setDragEnabled(True)

        self.horizontalLayout_3.addWidget(self.le_download_base_path)

        self.pb_download_base_path = QPushButton(self.gb_path)
        self.pb_download_base_path.setObjectName("pb_download_base_path")

        self.horizontalLayout_3.addWidget(self.pb_download_base_path)

        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.le_format_track = QLineEdit(self.gb_path)
        self.le_format_track.setObjectName("le_format_track")

        self.horizontalLayout_7.addWidget(self.le_format_track)

        self.verticalLayout.addLayout(self.horizontalLayout_7)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.le_format_video = QLineEdit(self.gb_path)
        self.le_format_video.setObjectName("le_format_video")

        self.horizontalLayout_5.addWidget(self.le_format_video)

        self.verticalLayout.addLayout(self.horizontalLayout_5)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.le_format_album = QLineEdit(self.gb_path)
        self.le_format_album.setObjectName("le_format_album")

        self.horizontalLayout_6.addWidget(self.le_format_album)

        self.verticalLayout.addLayout(self.horizontalLayout_6)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.le_format_playlist = QLineEdit(self.gb_path)
        self.le_format_playlist.setObjectName("le_format_playlist")
        sizePolicy2.setHeightForWidth(self.le_format_playlist.sizePolicy().hasHeightForWidth())
        self.le_format_playlist.setSizePolicy(sizePolicy2)

        self.horizontalLayout_4.addWidget(self.le_format_playlist)

        self.verticalLayout.addLayout(self.horizontalLayout_4)

        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        self.le_format_mix = QLineEdit(self.gb_path)
        self.le_format_mix.setObjectName("le_format_mix")

        self.horizontalLayout_8.addWidget(self.le_format_mix)

        self.verticalLayout.addLayout(self.horizontalLayout_8)

        self.horizontalLayout_2.addLayout(self.verticalLayout)

        self.horizontalLayout_2.setStretch(1, 50)

        self.lv_main.addWidget(self.gb_path)

        self.bb_dialog = QDialogButtonBox(DialogSettings)
        self.bb_dialog.setObjectName("bb_dialog")
        self.bb_dialog.setOrientation(Qt.Horizontal)
        self.bb_dialog.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)

        self.lv_main.addWidget(self.bb_dialog)

        self.lv_dialog_settings.addLayout(self.lv_main)

        self.retranslateUi(DialogSettings)
        self.bb_dialog.accepted.connect(DialogSettings.accept)
        self.bb_dialog.rejected.connect(DialogSettings.reject)

        QMetaObject.connectSlotsByName(DialogSettings)

    # setupUi

    def retranslateUi(self, DialogSettings):
        DialogSettings.setWindowTitle(QCoreApplication.translate("DialogSettings", "Preferences", None))
        self.gb_flags.setTitle(QCoreApplication.translate("DialogSettings", "Flags", None))
        self.cb_video_download.setText(QCoreApplication.translate("DialogSettings", "CheckBox", None))
        self.cb_video_convert_mp4.setText(QCoreApplication.translate("DialogSettings", "CheckBox", None))
        # if QT_CONFIG(whatsthis)
        self.cb_lyrics_embed.setWhatsThis("")
        # endif // QT_CONFIG(whatsthis)
        self.cb_lyrics_embed.setText(QCoreApplication.translate("DialogSettings", "CheckBox", None))
        self.cb_lyrics_file.setText(QCoreApplication.translate("DialogSettings", "CheckBox", None))
        self.cb_download_delay.setText(QCoreApplication.translate("DialogSettings", "CheckBox", None))
        self.gb_choices.setTitle(QCoreApplication.translate("DialogSettings", "Choices", None))
        self.l_icon_skip_existing.setText(QCoreApplication.translate("DialogSettings", "TextLabel", None))
        self.l_skip_existing.setText(QCoreApplication.translate("DialogSettings", "TextLabel", None))
        self.l_icon_quality_audio.setText(QCoreApplication.translate("DialogSettings", "TextLabel", None))
        self.l_quality_audio.setText(QCoreApplication.translate("DialogSettings", "TextLabel", None))
        self.l_icon_quality_video.setText(QCoreApplication.translate("DialogSettings", "TextLabel", None))
        self.l_quality_video.setText(QCoreApplication.translate("DialogSettings", "TextLabel", None))
        self.l_icon_metadata_cover_dimension.setText(QCoreApplication.translate("DialogSettings", "TextLabel", None))
        self.l_metadata_cover_dimension.setText(QCoreApplication.translate("DialogSettings", "TextLabel", None))
        self.gb_path.setTitle(QCoreApplication.translate("DialogSettings", "Path", None))
        self.l_icon_download_base_path.setText(QCoreApplication.translate("DialogSettings", "TextLabel", None))
        self.l_download_base_path.setText(QCoreApplication.translate("DialogSettings", "TextLabel", None))
        self.l_icon_format_track.setText(QCoreApplication.translate("DialogSettings", "TextLabel", None))
        self.l_format_track.setText(QCoreApplication.translate("DialogSettings", "TextLabel", None))
        self.l_icon_format_video.setText(QCoreApplication.translate("DialogSettings", "TextLabel", None))
        self.l_format_video.setText(QCoreApplication.translate("DialogSettings", "TextLabel", None))
        self.l_icon_format_album.setText(QCoreApplication.translate("DialogSettings", "TextLabel", None))
        self.l_format_album.setText(QCoreApplication.translate("DialogSettings", "TextLabel", None))
        self.l_icon_format_playlist.setText(QCoreApplication.translate("DialogSettings", "TextLabel", None))
        self.l_format_playlist.setText(QCoreApplication.translate("DialogSettings", "TextLabel", None))
        self.l_icon_format_mix.setText(QCoreApplication.translate("DialogSettings", "TextLabel", None))
        self.l_format_mix.setText(QCoreApplication.translate("DialogSettings", "TextLabel", None))
        self.pb_download_base_path.setText(QCoreApplication.translate("DialogSettings", "...", None))

    # retranslateUi
