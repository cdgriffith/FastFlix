# -*- coding: utf-8 -*-

import logging
import shutil
from pathlib import Path

from iso639 import Lang
from iso639.exceptions import InvalidLanguageValue
from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.exceptions import FastFlixInternalException
from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.shared import error_message, link

logger = logging.getLogger("fastflix")
language_list = sorted((k for k, v in Lang._data["name"].items() if v["pt2B"] and v["pt1"]), key=lambda x: x.lower())

known_language_list = [
    "English",
    "Chinese (Simplified)",
    "Italian",
    "French",
    "Spanish",
    "German",
    "Japanese",
    "Russian",
    "Portuguese",
    "Swedish",
    "Polish",
    "Romanian",
    "Ukrainian",
    "Korean",
    # "Chinese (Traditional)"    #reserved for future use
]
possible_detect_points = ["1", "2", "4", "6", "8", "10", "15", "20", "25", "50", "100"]

scale_digits = ["0", "1", "1.25", "1.5", "1.75", "2", "2.5", "3"]
scale_percents = ["Disable Scaling", "100%", "125%", "150%", "175%", "200%", "250%", "300%"]


class Settings(QtWidgets.QWidget):
    def __init__(self, app: FastFlixApp, main, *args, **kwargs):
        super().__init__(None, *args, **kwargs)
        self.app = app
        self.main = main
        self.config_file = self.app.fastflix.config.config_path
        self.setWindowTitle(t("Settings"))
        self.setMinimumSize(600, 200)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        layout = QtWidgets.QGridLayout()

        ffmpeg_label = QtWidgets.QLabel("FFmpeg")
        self.ffmpeg_path = QtWidgets.QLineEdit()
        self.ffmpeg_path.setText(str(self.app.fastflix.config.ffmpeg))
        ffmpeg_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        ffmpeg_path_button.clicked.connect(lambda: self.select_ffmpeg())
        layout.addWidget(ffmpeg_label, 0, 0)
        layout.addWidget(self.ffmpeg_path, 0, 1)
        layout.addWidget(ffmpeg_path_button, 0, 2)

        ffprobe_label = QtWidgets.QLabel("FFprobe")
        self.ffprobe_path = QtWidgets.QLineEdit()
        self.ffprobe_path.setText(str(self.app.fastflix.config.ffprobe))
        ffprobe_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        ffprobe_path_button.clicked.connect(lambda: self.select_ffprobe())
        layout.addWidget(ffprobe_label, 1, 0)
        layout.addWidget(self.ffprobe_path, 1, 1)
        layout.addWidget(ffprobe_path_button, 1, 2)

        work_dir_label = QtWidgets.QLabel(t("Work Directory"))
        self.work_dir = QtWidgets.QLineEdit()
        self.work_dir.setText(str(self.app.fastflix.config.work_path))
        work_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        work_path_button.clicked.connect(lambda: self.select_work_path())
        layout.addWidget(work_dir_label, 2, 0)
        layout.addWidget(self.work_dir, 2, 1)
        layout.addWidget(work_path_button, 2, 2)

        layout.addWidget(QtWidgets.QLabel(t("Config File")), 4, 0)
        layout.addWidget(QtWidgets.QLabel(str(self.config_file)), 4, 1)

        self.language_combo = QtWidgets.QComboBox(self)
        self.language_combo.addItems(known_language_list)
        try:
            if self.app.fastflix.config.language in ("chs", "zho"):
                index = known_language_list.index("Chinese (Simplified)")

            # reserved for future use
            # elif self.app.fastflix.config.language == "cht":
            # index = known_language_list.index("Chinese (Traditional)")

            else:
                index = known_language_list.index(Lang(self.app.fastflix.config.language).name)
        except (IndexError, InvalidLanguageValue):
            logger.exception(f"{t('Could not find language for')} {self.app.fastflix.config.language}")
            index = known_language_list.index("English")
        self.language_combo.setCurrentIndex(index)

        layout.addWidget(QtWidgets.QLabel(t("Language")), 5, 0)
        layout.addWidget(self.language_combo, 5, 1)

        config_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon))
        config_button.clicked.connect(
            lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(self.config_file)))
        )
        layout.addWidget(config_button, 4, 2)

        save = QtWidgets.QPushButton(
            icon=self.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton), text=t("Save")
        )
        save.clicked.connect(lambda: self.save())

        cancel = QtWidgets.QPushButton(
            icon=self.style().standardIcon(QtWidgets.QStyle.SP_DialogCancelButton), text=t("Cancel")
        )
        cancel.clicked.connect(lambda: self.close())

        self.use_sane_audio = QtWidgets.QCheckBox(t("Use Sane Audio Selection (updatable in config file)"))
        if self.app.fastflix.config.use_sane_audio:
            self.use_sane_audio.setChecked(True)
        self.disable_version_check = QtWidgets.QCheckBox(t("Disable update check on startup"))
        if not self.app.fastflix.config.disable_version_check:
            self.disable_version_check.setChecked(False)
        elif self.app.fastflix.config.disable_version_check:
            self.disable_version_check.setChecked(True)

        self.disable_end_message = QtWidgets.QCheckBox(t("Disable completion and error messages"))
        if self.app.fastflix.config.disable_complete_message:
            self.disable_end_message.setChecked(True)

        self.logger_level_widget = QtWidgets.QComboBox()
        self.logger_level_widget.addItems(["Debug", "Info", "Warning", "Error"])
        self.logger_level_widget.setCurrentIndex(int(self.app.fastflix.config.logging_level // 10) - 1)

        self.theme = QtWidgets.QComboBox()
        self.theme.addItems(["onyx", "light", "dark", "system"])
        self.theme.setCurrentText(self.app.fastflix.config.theme)

        self.crop_detect_points_widget = QtWidgets.QComboBox()
        self.crop_detect_points_widget.addItems(possible_detect_points)

        try:
            self.crop_detect_points_widget.setCurrentIndex(
                possible_detect_points.index(str(self.app.fastflix.config.crop_detect_points))
            )
        except ValueError:
            self.crop_detect_points_widget.setCurrentIndex(5)

        self.ui_scale_widget = QtWidgets.QComboBox()
        self.ui_scale_widget.addItems(scale_percents)
        self.ui_scale_widget.setCurrentText(scale_percents[scale_digits.index(self.app.fastflix.config.ui_scale)])

        nvencc_label = QtWidgets.QLabel(
            link("https://github.com/rigaya/NVEnc/releases", "NVEncC", app.fastflix.config.theme)
        )
        nvencc_label.setOpenExternalLinks(True)
        self.nvencc_path = QtWidgets.QLineEdit()
        if self.app.fastflix.config.nvencc:
            self.nvencc_path.setText(str(self.app.fastflix.config.nvencc))
        nvenc_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        nvenc_path_button.clicked.connect(lambda: self.select_nvencc())
        layout.addWidget(nvencc_label, 12, 0)
        layout.addWidget(self.nvencc_path, 12, 1)
        layout.addWidget(nvenc_path_button, 12, 2)

        vceenc_label = QtWidgets.QLabel(
            link("https://github.com/rigaya/VCEEnc/releases", "VCEEncC", app.fastflix.config.theme)
        )
        vceenc_label.setOpenExternalLinks(True)
        self.vceenc_path = QtWidgets.QLineEdit()
        if self.app.fastflix.config.vceencc:
            self.vceenc_path.setText(str(self.app.fastflix.config.vceencc))
        vceenc_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        vceenc_path_button.clicked.connect(lambda: self.select_vceenc())
        layout.addWidget(vceenc_label, 13, 0)
        layout.addWidget(self.vceenc_path, 13, 1)
        layout.addWidget(vceenc_path_button, 13, 2)

        qsvencc_label = QtWidgets.QLabel(
            link("https://github.com/rigaya/QSVEnc/releases", "QSVEncC", app.fastflix.config.theme)
        )
        qsvencc_label.setOpenExternalLinks(True)
        self.qsvenc_path = QtWidgets.QLineEdit()
        if self.app.fastflix.config.qsvencc:
            self.qsvenc_path.setText(str(self.app.fastflix.config.qsvencc))
        qsvencc_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        qsvencc_path_button.clicked.connect(lambda: self.select_qsvencc())
        layout.addWidget(qsvencc_label, 14, 0)
        layout.addWidget(self.qsvenc_path, 14, 1)
        layout.addWidget(qsvencc_path_button, 14, 2)

        hdr10_parser_label = QtWidgets.QLabel(
            link("https://github.com/quietvoid/hdr10plus_tool", "HDR10+ Parser Tool", app.fastflix.config.theme)
        )
        hdr10_parser_label.setOpenExternalLinks(True)
        self.hdr10_parser_path = QtWidgets.QLineEdit()
        if self.app.fastflix.config.hdr10plus_parser:
            self.hdr10_parser_path.setText(str(self.app.fastflix.config.hdr10plus_parser))
        hdr10_parser_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        hdr10_parser_path_button.clicked.connect(lambda: self.select_hdr10_parser())
        layout.addWidget(hdr10_parser_label, 15, 0)
        layout.addWidget(self.hdr10_parser_path, 15, 1)
        layout.addWidget(hdr10_parser_path_button, 15, 2)

        # OUTPUT DIR
        output_label = QtWidgets.QLabel(t("Default Output Folder"))
        self.output_path_line_edit = QtWidgets.QLineEdit()
        if self.app.fastflix.config.output_directory:
            self.output_path_line_edit.setText(str(self.app.fastflix.config.output_directory))
        output_label_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        output_label_path_button.clicked.connect(lambda: self.select_output_directory())
        layout.addWidget(output_label, 17, 0)
        layout.addWidget(self.output_path_line_edit, 17, 1)
        layout.addWidget(output_label_path_button, 17, 2)

        self.default_output_dir = QtWidgets.QCheckBox(t("Use same output directory as source file"))
        if not self.app.fastflix.config.output_directory:
            self.default_output_dir.setChecked(True)
            self.output_path_line_edit.setDisabled(True)
        self.default_output_dir.clicked.connect(
            lambda: self.output_path_line_edit.setDisabled(self.output_path_line_edit.isEnabled())
        )
        layout.addWidget(self.default_output_dir, 16, 0, 1, 2)

        # SOURCE DIR

        source_label = QtWidgets.QLabel(t("Default Source Folder"))
        self.source_path_line_edit = QtWidgets.QLineEdit()
        if self.app.fastflix.config.source_directory:
            self.source_path_line_edit.setText(str(self.app.fastflix.config.source_directory))
        source_label_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        source_label_path_button.clicked.connect(lambda: self.select_source_directory())
        layout.addWidget(source_label, 19, 0)
        layout.addWidget(self.source_path_line_edit, 19, 1)
        layout.addWidget(source_label_path_button, 19, 2)

        self.default_source_dir = QtWidgets.QCheckBox(t("No Default Source Folder"))
        if not self.app.fastflix.config.source_directory:
            self.default_source_dir.setChecked(True)
            self.source_path_line_edit.setDisabled(True)
        self.default_source_dir.clicked.connect(
            lambda: self.source_path_line_edit.setDisabled(self.source_path_line_edit.isEnabled())
        )

        self.sticky_tabs = QtWidgets.QCheckBox(t("Disable Automatic Tab Switching"))
        self.sticky_tabs.setChecked(self.app.fastflix.config.sticky_tabs)

        mm = QtWidgets.QHBoxLayout()
        mm.addWidget(self.default_source_dir)
        mm.addWidget(self.sticky_tabs)

        layout.addLayout(mm, 18, 0, 1, 2)

        self.clean_old_logs_button = QtWidgets.QCheckBox(
            t("Remove GUI logs and compress conversion logs older than 30 days at exit")
        )
        self.clean_old_logs_button.setChecked(self.app.fastflix.config.clean_old_logs)

        # Layouts

        layout.addWidget(self.use_sane_audio, 7, 0, 1, 2)
        layout.addWidget(self.disable_version_check, 8, 0, 1, 2)
        layout.addWidget(QtWidgets.QLabel(t("GUI Logging Level")), 9, 0)
        layout.addWidget(self.logger_level_widget, 9, 1)
        layout.addWidget(QtWidgets.QLabel(t("Theme")), 10, 0)
        layout.addWidget(self.theme, 10, 1)
        layout.addWidget(QtWidgets.QLabel(t("Crop Detect Points")), 11, 0, 1, 1)
        layout.addWidget(self.crop_detect_points_widget, 11, 1, 1, 1)

        layout.addWidget(QtWidgets.QLabel(t("UI Scale")), 20, 0, 1, 1)
        layout.addWidget(self.ui_scale_widget, 20, 1, 1, 1)

        layout.addWidget(self.clean_old_logs_button, 21, 0, 1, 3)
        layout.addWidget(self.disable_end_message, 22, 0, 1, 3)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(cancel)
        button_layout.addWidget(save)

        layout.addLayout(button_layout, 24, 0, 1, 3)

        self.setLayout(layout)

    def save(self):
        new_ffmpeg = Path(self.ffmpeg_path.text())
        new_ffprobe = Path(self.ffprobe_path.text())
        new_work_dir = Path(self.work_dir.text())
        restart_needed = False
        try:
            updated_ffmpeg = self.update_ffmpeg(new_ffmpeg)
            self.update_ffprobe(new_ffprobe)
        except FastFlixInternalException:
            return

        try:
            new_work_dir.mkdir(exist_ok=True, parents=True)
        except OSError:
            error_message(f'{t("Could not create / access work directory")} "{new_work_dir}"')
        else:
            self.app.fastflix.config.work_path = new_work_dir
        self.app.fastflix.config.use_sane_audio = self.use_sane_audio.isChecked()
        if self.theme.currentText() != self.app.fastflix.config.theme:
            restart_needed = True
        self.app.fastflix.config.theme = self.theme.currentText()

        old_lang = self.app.fastflix.config.language
        current_text = self.language_combo.currentText()
        try:
            if current_text == "Chinese (Simplified)":
                self.app.fastflix.config.language = "chs"

            # reserved for future use
            # elif current_text != "Chinese (Traditional)":
            # self.app.fastflix.config.language = "cht"

            else:
                self.app.fastflix.config.language = Lang(self.language_combo.currentText()).pt3
        except InvalidLanguageValue:
            error_message(
                f"{t('Could not set language to')} {self.language_combo.currentText()}\n {t('Please report this issue')}"
            )
        self.app.fastflix.config.disable_version_check = self.disable_version_check.isChecked()
        log_level = (self.logger_level_widget.currentIndex() + 1) * 10
        self.app.fastflix.config.logging_level = log_level
        logger.setLevel(log_level)
        self.app.fastflix.config.crop_detect_points = int(self.crop_detect_points_widget.currentText())

        new_nvencc = Path(self.nvencc_path.text()) if self.nvencc_path.text().strip() else None
        if str(self.app.fastflix.config.nvencc) != str(new_nvencc):
            restart_needed = True
        self.app.fastflix.config.nvencc = new_nvencc

        new_qsvencc = Path(self.qsvenc_path.text()) if self.qsvenc_path.text().strip() else None
        if str(self.app.fastflix.config.qsvencc) != str(new_qsvencc):
            restart_needed = True
        self.app.fastflix.config.qsvencc = new_qsvencc

        new_vce = Path(self.vceenc_path.text()) if self.vceenc_path.text().strip() else None
        if str(self.app.fastflix.config.vceencc) != str(new_vce):
            restart_needed = True
        self.app.fastflix.config.vceencc = new_vce

        new_hdr10_parser = Path(self.hdr10_parser_path.text()) if self.hdr10_parser_path.text().strip() else None
        if str(self.app.fastflix.config.hdr10plus_parser) != str(new_hdr10_parser):
            restart_needed = True
        self.app.fastflix.config.hdr10plus_parser = new_hdr10_parser

        new_output_path = False
        if self.output_path_line_edit.text().strip() and not self.default_output_dir.isChecked():
            new_output_path = Path(self.output_path_line_edit.text())
        self.app.fastflix.config.output_directory = new_output_path

        new_source_path = False
        if self.source_path_line_edit.text().strip() and not self.default_source_dir.isChecked():
            new_source_path = Path(self.source_path_line_edit.text())
        self.app.fastflix.config.source_directory = new_source_path

        old_scale = self.app.fastflix.config.ui_scale
        self.app.fastflix.config.ui_scale = scale_digits[scale_percents.index(self.ui_scale_widget.currentText())]
        if self.app.fastflix.config.ui_scale != old_scale:
            restart_needed = True

        self.app.fastflix.config.clean_old_logs = self.clean_old_logs_button.isChecked()
        self.app.fastflix.config.sticky_tabs = self.sticky_tabs.isChecked()
        self.app.fastflix.config.disable_complete_message = self.disable_end_message.isChecked()

        self.main.config_update()
        self.app.fastflix.config.save()
        if updated_ffmpeg or old_lang != self.app.fastflix.config.language or restart_needed:
            error_message(t("Please restart FastFlix to apply settings"))
        self.close()

    def select_ffmpeg(self):
        dirname = Path(self.ffmpeg_path.text()).parent
        if not dirname.exists():
            dirname = Path()
        filename = QtWidgets.QFileDialog.getOpenFileName(self, caption="FFmepg location", dir=str(dirname))
        if not filename or not filename[0]:
            return
        self.ffmpeg_path.setText(str(Path(filename[0]).absolute()))

    def select_nvencc(self):
        dirname = Path(self.nvencc_path.text()).parent
        if not dirname.exists():
            dirname = Path()
        filename = QtWidgets.QFileDialog.getOpenFileName(self, caption="NVEncC location", dir=str(dirname))
        if not filename or not filename[0]:
            return
        self.nvencc_path.setText(str(Path(filename[0]).absolute()))

    def select_qsvencc(self):
        dirname = Path(self.qsvenc_path.text()).parent
        if not dirname.exists():
            dirname = Path()
        filename = QtWidgets.QFileDialog.getOpenFileName(self, caption="QSVEncC location", dir=str(dirname))
        if not filename or not filename[0]:
            return
        self.qsvenc_path.setText(str(Path(filename[0]).absolute()))

    def select_vceenc(self):
        dirname = Path(self.vceenc_path.text()).parent
        if not dirname.exists():
            dirname = Path()
        filename = QtWidgets.QFileDialog.getOpenFileName(self, caption="VCEEncC location", dir=str(dirname))
        if not filename or not filename[0]:
            return
        self.vceenc_path.setText(str(Path(filename[0]).absolute()))

    def select_hdr10_parser(self):
        dirname = Path(self.hdr10_parser_path.text()).parent
        if not dirname.exists():
            dirname = Path()
        filename = QtWidgets.QFileDialog.getOpenFileName(self, caption="hdr10+ parser", dir=str(dirname))
        if not filename or not filename[0]:
            return
        self.hdr10_parser_path.setText(str(Path(filename[0]).absolute()))

    def select_output_directory(self):
        dirname = Path(self.output_path_line_edit.text()).parent
        if not dirname.exists():
            dirname = Path()
        filename = QtWidgets.QFileDialog.getExistingDirectory(self, caption="Output Directory", dir=str(dirname))
        if not filename:
            return
        self.output_path_line_edit.setText(filename)

    def select_source_directory(self):
        dirname = Path(self.source_path_line_edit.text()).parent
        if not dirname.exists():
            dirname = Path()
        filename = QtWidgets.QFileDialog.getExistingDirectory(self, caption="Source Directory", dir=str(dirname))
        if not filename:
            return
        self.source_path_line_edit.setText(filename)

    @staticmethod
    def path_check(name, new_path):
        if not new_path.exists():
            which = shutil.which(str(new_path))
            if not which:
                error_message(f"No {name} instance found at {new_path}, not updated")
                raise FastFlixInternalException(f"No {name} instance found at {new_path}, not updated")
            return Path(which)
        if not new_path.is_file():
            error_message(f"{new_path} is not a file")
            raise FastFlixInternalException(f"No {name} instance found at {new_path}, not updated")
        return new_path

    def update_ffmpeg(self, new_path):
        if self.app.fastflix.config.ffmpeg == new_path:
            return False
        new_path = self.path_check("FFmpeg", new_path)
        self.app.fastflix.config.ffmpeg = new_path
        self.update_setting("ffmpeg", str(new_path))
        return True

    def select_ffprobe(self):
        dirname = Path(self.ffprobe_path.text()).parent
        if not dirname.exists():
            dirname = Path()
        filename = QtWidgets.QFileDialog.getOpenFileName(self, caption="FFprobe location", dir=str(dirname))
        if not filename or not filename[0]:
            return
        self.ffprobe_path.setText(filename[0])

    def update_ffprobe(self, new_path):
        if self.app.fastflix.config.ffprobe == new_path:
            return False
        new_path = self.path_check("FFprobe", new_path)
        self.app.fastflix.config.ffprobe = new_path
        self.update_setting("ffprobe", str(new_path))
        return True

    def select_work_path(self):
        dirname = Path(self.work_dir.text())
        if not dirname.exists():
            dirname = Path()
        dialog = QtWidgets.QFileDialog()
        dialog.setFileMode(QtWidgets.QFileDialog.Directory)
        dialog.setOption(QtWidgets.QFileDialog.ShowDirsOnly)
        work_path = dialog.getExistingDirectory(dir=str(dirname), caption="Work directory")
        if not work_path:
            return
        self.work_dir.setText(work_path)

    def update_setting(self, name, value):
        setattr(self.app.fastflix.config, name, value)
