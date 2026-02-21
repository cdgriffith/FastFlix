# -*- coding: utf-8 -*-

import logging
import shutil
from pathlib import Path

from iso639 import iter_langs
from iso639.exceptions import InvalidLanguageValue
from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.exceptions import FastFlixInternalException
from fastflix.language import t, Language
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.naming import (
    PRE_ENCODE_VARIABLES,
    POST_ENCODE_VARIABLES,
    ALL_VARIABLES,
    generate_preview,
    validate_template,
)
from fastflix.shared import error_message, link
from fastflix.widgets.flow_layout import FlowLayout

logger = logging.getLogger("fastflix")
language_list = [v.name for v in iter_langs() if v.pt2b and v.pt1]

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
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Window)

        main_layout = QtWidgets.QVBoxLayout()

        tab_widget = QtWidgets.QTabWidget()
        tab_widget.addTab(self._build_settings_tab(), t("Settings"))
        tab_widget.addTab(self._build_output_naming_tab(), t("Output Naming"))
        tab_widget.addTab(self._build_locations_tab(), t("Application Locations"))
        main_layout.addWidget(tab_widget)

        # Save/Cancel buttons at the bottom (outside tabs)
        save = QtWidgets.QPushButton(
            icon=self.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton), text=t("Save")
        )
        save.clicked.connect(lambda: self.save())

        cancel = QtWidgets.QPushButton(
            icon=self.style().standardIcon(QtWidgets.QStyle.SP_DialogCancelButton), text=t("Cancel")
        )
        cancel.clicked.connect(lambda: self.close())

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(cancel)
        button_layout.addWidget(save)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def _build_settings_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout()
        layout.setColumnStretch(1, 1)
        row = 0

        # Config File
        layout.addWidget(QtWidgets.QLabel(t("Config File")), row, 0)
        layout.addWidget(QtWidgets.QLabel(str(self.config_file)), row, 1)
        config_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon))
        config_button.setFixedWidth(30)
        config_button.clicked.connect(
            lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(self.config_file)))
        )
        layout.addWidget(config_button, row, 2)
        row += 1

        # Work Directory
        work_dir_label = QtWidgets.QLabel(t("Work Directory"))
        self.work_dir = QtWidgets.QLineEdit()
        self.work_dir.setText(str(self.app.fastflix.config.work_path))
        work_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        work_path_button.setFixedWidth(30)
        work_path_button.clicked.connect(lambda: self.select_work_path())
        layout.addWidget(work_dir_label, row, 0)
        layout.addWidget(self.work_dir, row, 1)
        layout.addWidget(work_path_button, row, 2)
        row += 1

        # Language
        self.language_combo = QtWidgets.QComboBox(self)
        self.language_combo.addItems(known_language_list)
        try:
            if self.app.fastflix.config.language in ("chs", "zho"):
                index = known_language_list.index("Chinese (Simplified)")
            else:
                index = known_language_list.index(Language(self.app.fastflix.config.language).name)
        except (IndexError, InvalidLanguageValue):
            logger.exception(f"{t('Could not find language for')} {self.app.fastflix.config.language}")
            index = known_language_list.index("English")
        self.language_combo.setCurrentIndex(index)
        layout.addWidget(QtWidgets.QLabel(t("Language")), row, 0)
        layout.addWidget(self.language_combo, row, 1)
        row += 1

        # Theme
        self.theme = QtWidgets.QComboBox()
        self.theme.addItems(["onyx", "light", "dark", "system"])
        self.theme.setCurrentText(self.app.fastflix.config.theme)
        layout.addWidget(QtWidgets.QLabel(t("Theme")), row, 0)
        layout.addWidget(self.theme, row, 1)
        row += 1

        # GUI Logging Level
        self.logger_level_widget = QtWidgets.QComboBox()
        self.logger_level_widget.addItems(["Debug", "Info", "Warning", "Error"])
        self.logger_level_widget.setCurrentIndex(int(self.app.fastflix.config.logging_level // 10) - 1)
        layout.addWidget(QtWidgets.QLabel(t("GUI Logging Level")), row, 0)
        layout.addWidget(self.logger_level_widget, row, 1)
        row += 1

        # Crop Detect Points
        self.crop_detect_points_widget = QtWidgets.QComboBox()
        self.crop_detect_points_widget.addItems(possible_detect_points)
        try:
            self.crop_detect_points_widget.setCurrentIndex(
                possible_detect_points.index(str(self.app.fastflix.config.crop_detect_points))
            )
        except ValueError:
            self.crop_detect_points_widget.setCurrentIndex(5)
        layout.addWidget(QtWidgets.QLabel(t("Crop Detect Points")), row, 0)
        layout.addWidget(self.crop_detect_points_widget, row, 1)
        row += 1

        # UI Scale
        self.ui_scale_widget = QtWidgets.QComboBox()
        self.ui_scale_widget.addItems(scale_percents)
        self.ui_scale_widget.setCurrentText(scale_percents[scale_digits.index(self.app.fastflix.config.ui_scale)])
        layout.addWidget(QtWidgets.QLabel(t("UI Scale")), row, 0)
        layout.addWidget(self.ui_scale_widget, row, 1)
        row += 1

        # Checkboxes
        self.use_sane_audio = QtWidgets.QCheckBox(t("Use Sane Audio Selection (updatable in config file)"))
        if self.app.fastflix.config.use_sane_audio:
            self.use_sane_audio.setChecked(True)
        layout.addWidget(self.use_sane_audio, row, 0, 1, 2)
        row += 1

        self.disable_version_check = QtWidgets.QCheckBox(t("Disable update check on startup"))
        if self.app.fastflix.config.disable_version_check:
            self.disable_version_check.setChecked(True)
        layout.addWidget(self.disable_version_check, row, 0, 1, 2)
        row += 1

        self.show_complete_message = QtWidgets.QCheckBox(t("Show completion popup message"))
        self.show_complete_message.setChecked(self.app.fastflix.config.show_complete_message)
        layout.addWidget(self.show_complete_message, row, 0, 1, 2)
        row += 1

        self.show_error_message = QtWidgets.QCheckBox(t("Show error popup message"))
        self.show_error_message.setChecked(self.app.fastflix.config.show_error_message)
        layout.addWidget(self.show_error_message, row, 0, 1, 2)
        row += 1

        self.clean_old_logs_button = QtWidgets.QCheckBox(
            t("Remove GUI logs and compress conversion logs older than 30 days at exit")
        )
        self.clean_old_logs_button.setChecked(self.app.fastflix.config.clean_old_logs)
        layout.addWidget(self.clean_old_logs_button, row, 0, 1, 3)
        row += 1

        self.disable_deinterlace_button = QtWidgets.QCheckBox(t("Disable interlace check"))
        self.disable_deinterlace_button.setChecked(self.app.fastflix.config.disable_deinterlace_check)
        layout.addWidget(self.disable_deinterlace_button, row, 0, 1, 3)
        row += 1

        self.use_keyframes_for_preview = QtWidgets.QCheckBox(t("Use keyframes for preview images"))
        self.use_keyframes_for_preview.setChecked(self.app.fastflix.config.use_keyframes_for_preview)
        layout.addWidget(self.use_keyframes_for_preview, row, 0, 1, 3)
        row += 1

        self.sticky_tabs = QtWidgets.QCheckBox(t("Disable Automatic Tab Switching"))
        self.sticky_tabs.setChecked(self.app.fastflix.config.sticky_tabs)
        layout.addWidget(self.sticky_tabs, row, 0, 1, 2)
        row += 1

        self.auto_detect_subtitles = QtWidgets.QCheckBox(t("Auto-detect external subtitle files"))
        self.auto_detect_subtitles.setChecked(self.app.fastflix.config.auto_detect_subtitles)
        layout.addWidget(self.auto_detect_subtitles, row, 0, 1, 3)
        row += 1

        # Default Output Directory
        self.default_output_dir = QtWidgets.QCheckBox(t("Use same output directory as source file"))
        layout.addWidget(self.default_output_dir, row, 0, 1, 2)
        row += 1

        output_label = QtWidgets.QLabel(t("Default Output Folder"))
        self.output_path_line_edit = QtWidgets.QLineEdit()
        if self.app.fastflix.config.output_directory:
            self.output_path_line_edit.setText(str(self.app.fastflix.config.output_directory))
        self.output_label_path_button = QtWidgets.QPushButton(
            icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon)
        )
        self.output_label_path_button.setFixedWidth(30)
        self.output_label_path_button.clicked.connect(lambda: self.select_output_directory())
        layout.addWidget(output_label, row, 0)
        layout.addWidget(self.output_path_line_edit, row, 1)
        layout.addWidget(self.output_label_path_button, row, 2)
        row += 1

        if not self.app.fastflix.config.output_directory:
            self.default_output_dir.setChecked(True)
            self.output_path_line_edit.setDisabled(True)
            self.output_label_path_button.setDisabled(True)

        def out_click():
            self.output_path_line_edit.setDisabled(self.output_path_line_edit.isEnabled())
            self.output_label_path_button.setEnabled(self.output_path_line_edit.isEnabled())

        self.default_output_dir.clicked.connect(out_click)

        # Default Source Directory
        self.default_source_dir = QtWidgets.QCheckBox(t("No Default Source Folder"))
        layout.addWidget(self.default_source_dir, row, 0, 1, 2)
        row += 1

        source_label = QtWidgets.QLabel(t("Default Source Folder"))
        self.source_path_line_edit = QtWidgets.QLineEdit()
        if self.app.fastflix.config.source_directory:
            self.source_path_line_edit.setText(str(self.app.fastflix.config.source_directory))
        self.source_label_path_button = QtWidgets.QPushButton(
            icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon)
        )
        self.source_label_path_button.setFixedWidth(30)
        self.source_label_path_button.clicked.connect(lambda: self.select_source_directory())
        layout.addWidget(source_label, row, 0)
        layout.addWidget(self.source_path_line_edit, row, 1)
        layout.addWidget(self.source_label_path_button, row, 2)
        row += 1

        if not self.app.fastflix.config.source_directory:
            self.default_source_dir.setChecked(True)
            self.source_path_line_edit.setDisabled(True)
            self.source_label_path_button.setDisabled(True)

        def in_dir():
            self.source_path_line_edit.setDisabled(self.source_path_line_edit.isEnabled())
            self.source_label_path_button.setEnabled(self.source_path_line_edit.isEnabled())

        self.default_source_dir.clicked.connect(in_dir)

        # Spacer
        layout.setRowStretch(row, 1)

        tab.setLayout(layout)
        return tab

    def _build_output_naming_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()

        # Template editor
        template_label = QtWidgets.QLabel(t("Output Filename Template"))
        template_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(template_label)

        template_row = QtWidgets.QHBoxLayout()
        self.template_edit = QtWidgets.QLineEdit()
        self.template_edit.setText(self.app.fastflix.config.output_name_format)
        self.template_edit.setPlaceholderText("{source}-fastflix-{rand_4}")
        self.template_edit.textChanged.connect(self._update_template_preview)
        template_row.addWidget(self.template_edit)

        reset_button = QtWidgets.QPushButton(t("Reset"))
        reset_button.setFixedWidth(60)
        reset_button.setToolTip(t("Reset to default template"))
        reset_button.clicked.connect(lambda: self.template_edit.setText("{source}-fastflix-{rand_4}"))
        template_row.addWidget(reset_button)

        layout.addLayout(template_row)

        # Live preview
        preview_header = QtWidgets.QLabel(t("Preview:"))
        preview_header.setStyleSheet("font-weight: bold; margin-top: 6px;")
        layout.addWidget(preview_header)

        self.template_preview = QtWidgets.QLabel()
        self.template_preview.setWordWrap(True)
        self.template_preview.setStyleSheet("color: #888; padding: 4px;")
        layout.addWidget(self.template_preview)

        # Validation status
        self.template_status = QtWidgets.QLabel()
        layout.addWidget(self.template_status)

        # Pre-encode variable chips
        pre_header = QtWidgets.QLabel(t("Pre-Encode Variables"))
        pre_header.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(pre_header)

        self._variable_chips = {}
        pre_flow = FlowLayout(h_spacing=6, v_spacing=6)
        pre_container = QtWidgets.QWidget()
        for var in PRE_ENCODE_VARIABLES:
            chip = self._make_chip(f"{{{var.name}}}", var.description, var.example, is_post=False)
            self._variable_chips[var.name] = chip
            pre_flow.addWidget(chip)
        pre_container.setLayout(pre_flow)
        layout.addWidget(pre_container)

        # Post-encode variable chips
        post_header = QtWidgets.QLabel(t("Post-Encode Variables"))
        post_header.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(post_header)
        post_subtitle = QtWidgets.QLabel(t("Resolved after encoding completes; file will be renamed automatically"))
        post_subtitle.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(post_subtitle)

        post_flow = FlowLayout(h_spacing=6, v_spacing=6)
        post_container = QtWidgets.QWidget()
        for var in POST_ENCODE_VARIABLES:
            chip = self._make_chip(f"{{{var.name}}}", var.description, var.example, is_post=True)
            self._variable_chips[var.name] = chip
            post_flow.addWidget(chip)
        post_container.setLayout(post_flow)
        layout.addWidget(post_container)

        # Variable reference table (always visible)
        self.ref_table = QtWidgets.QTableWidget()
        self.ref_table.setColumnCount(4)
        self.ref_table.setHorizontalHeaderLabels([t("Variable"), t("Description"), t("Phase"), t("Example")])
        self.ref_table.setRowCount(len(ALL_VARIABLES))
        self.ref_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.ref_table.horizontalHeader().setStretchLastSection(True)
        self.ref_table.verticalHeader().setVisible(False)
        for row, var in enumerate(ALL_VARIABLES):
            self.ref_table.setItem(row, 0, QtWidgets.QTableWidgetItem(f"{{{var.name}}}"))
            self.ref_table.setItem(row, 1, QtWidgets.QTableWidgetItem(var.description))
            phase_text = t("Pre-Encode") if var.phase.value == "pre_encode" else t("Post-Encode")
            self.ref_table.setItem(row, 2, QtWidgets.QTableWidgetItem(phase_text))
            self.ref_table.setItem(row, 3, QtWidgets.QTableWidgetItem(var.example))
        self.ref_table.resizeColumnsToContents()
        layout.addWidget(self.ref_table)

        # Initialize preview
        self._update_template_preview()

        tab.setLayout(layout)
        return tab

    _CHIP_STYLE_PRE = (
        "QPushButton { background-color: #2a6e9e; color: white; border-radius: 10px; "
        "padding: 4px 10px; font-size: 12px; border: 1px solid #3a8ebe; }"
        "QPushButton:hover { background-color: #3a7eae; }"
    )
    _CHIP_STYLE_POST = (
        "QPushButton { background-color: #5b4a8a; color: white; border-radius: 10px; "
        "padding: 4px 10px; font-size: 12px; border: 1px solid #7a6aaa; }"
        "QPushButton:hover { background-color: #6b5a9a; }"
    )
    _CHIP_STYLE_DISABLED = (
        "QPushButton { background-color: #555; color: #888; border-radius: 10px; "
        "padding: 4px 10px; font-size: 12px; border: 1px solid #666; }"
    )

    def _make_chip(self, text, description, example, is_post=False):
        """Create a clickable variable chip button."""
        chip = QtWidgets.QPushButton(text)
        chip.setToolTip(f"{description}\n{t('Example')}: {example}")
        chip.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        chip.setProperty("is_post", is_post)
        chip.setStyleSheet(self._CHIP_STYLE_POST if is_post else self._CHIP_STYLE_PRE)
        chip.clicked.connect(lambda: self._insert_variable(text))
        return chip

    def _insert_variable(self, text):
        """Insert variable text at cursor position in template editor."""
        cursor_pos = self.template_edit.cursorPosition()
        current = self.template_edit.text()
        new_text = current[:cursor_pos] + text + current[cursor_pos:]
        self.template_edit.setText(new_text)
        self.template_edit.setCursorPosition(cursor_pos + len(text))
        self.template_edit.setFocus()

    def _update_template_preview(self):
        """Update the live preview, validation status, and chip enabled states."""
        template = self.template_edit.text()
        is_valid, message = validate_template(template)

        if is_valid:
            self.template_status.setText(f'<span style="color: green;">\u2714 {message}</span>')
        else:
            self.template_status.setText(f'<span style="color: red;">\u2718 {message}</span>')

        preview = generate_preview(template)
        self.template_preview.setText(preview)

        # Gray out chips for variables already present in the template
        for var_name, chip in self._variable_chips.items():
            already_used = f"{{{var_name}}}" in template
            chip.setEnabled(not already_used)
            if already_used:
                chip.setStyleSheet(self._CHIP_STYLE_DISABLED)
                chip.setCursor(QtGui.QCursor(QtCore.Qt.ForbiddenCursor))
            else:
                is_post = chip.property("is_post")
                chip.setStyleSheet(self._CHIP_STYLE_POST if is_post else self._CHIP_STYLE_PRE)
                chip.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

    def _build_locations_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout()
        layout.setColumnStretch(1, 1)
        row = 0

        # FFmpeg
        ffmpeg_label = QtWidgets.QLabel("FFmpeg")
        self.ffmpeg_path = QtWidgets.QLineEdit()
        self.ffmpeg_path.setText(str(self.app.fastflix.config.ffmpeg))
        ffmpeg_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        ffmpeg_path_button.setFixedWidth(30)
        ffmpeg_path_button.clicked.connect(lambda: self.select_ffmpeg())
        layout.addWidget(ffmpeg_label, row, 0)
        layout.addWidget(self.ffmpeg_path, row, 1)
        layout.addWidget(ffmpeg_path_button, row, 2)
        row += 1

        # FFprobe
        ffprobe_label = QtWidgets.QLabel("FFprobe")
        self.ffprobe_path = QtWidgets.QLineEdit()
        self.ffprobe_path.setText(str(self.app.fastflix.config.ffprobe))
        ffprobe_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        ffprobe_path_button.setFixedWidth(30)
        ffprobe_path_button.clicked.connect(lambda: self.select_ffprobe())
        layout.addWidget(ffprobe_label, row, 0)
        layout.addWidget(self.ffprobe_path, row, 1)
        layout.addWidget(ffprobe_path_button, row, 2)
        row += 1

        # NVEncC
        nvencc_label = QtWidgets.QLabel(
            link("https://github.com/rigaya/NVEnc/releases", "NVEncC", self.app.fastflix.config.theme)
        )
        nvencc_label.setOpenExternalLinks(True)
        self.nvencc_path = QtWidgets.QLineEdit()
        if self.app.fastflix.config.nvencc:
            self.nvencc_path.setText(str(self.app.fastflix.config.nvencc))
        nvenc_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        nvenc_path_button.setFixedWidth(30)
        nvenc_path_button.clicked.connect(lambda: self.select_nvencc())
        layout.addWidget(nvencc_label, row, 0)
        layout.addWidget(self.nvencc_path, row, 1)
        layout.addWidget(nvenc_path_button, row, 2)
        row += 1

        # VCEEncC
        vceenc_label = QtWidgets.QLabel(
            link("https://github.com/rigaya/VCEEnc/releases", "VCEEncC", self.app.fastflix.config.theme)
        )
        vceenc_label.setOpenExternalLinks(True)
        self.vceenc_path = QtWidgets.QLineEdit()
        if self.app.fastflix.config.vceencc:
            self.vceenc_path.setText(str(self.app.fastflix.config.vceencc))
        vceenc_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        vceenc_path_button.setFixedWidth(30)
        vceenc_path_button.clicked.connect(lambda: self.select_vceenc())
        layout.addWidget(vceenc_label, row, 0)
        layout.addWidget(self.vceenc_path, row, 1)
        layout.addWidget(vceenc_path_button, row, 2)
        row += 1

        # QSVEncC
        qsvencc_label = QtWidgets.QLabel(
            link("https://github.com/rigaya/QSVEnc/releases", "QSVEncC", self.app.fastflix.config.theme)
        )
        qsvencc_label.setOpenExternalLinks(True)
        self.qsvenc_path = QtWidgets.QLineEdit()
        if self.app.fastflix.config.qsvencc:
            self.qsvenc_path.setText(str(self.app.fastflix.config.qsvencc))
        qsvencc_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        qsvencc_path_button.setFixedWidth(30)
        qsvencc_path_button.clicked.connect(lambda: self.select_qsvencc())
        layout.addWidget(qsvencc_label, row, 0)
        layout.addWidget(self.qsvenc_path, row, 1)
        layout.addWidget(qsvencc_path_button, row, 2)
        row += 1

        # HDR10+ Parser
        hdr10_parser_label = QtWidgets.QLabel(
            link("https://github.com/quietvoid/hdr10plus_tool", "HDR10+ Parser Tool", self.app.fastflix.config.theme)
        )
        hdr10_parser_label.setOpenExternalLinks(True)
        self.hdr10_parser_path = QtWidgets.QLineEdit()
        if self.app.fastflix.config.hdr10plus_parser:
            self.hdr10_parser_path.setText(str(self.app.fastflix.config.hdr10plus_parser))
        hdr10_parser_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        hdr10_parser_path_button.setFixedWidth(30)
        hdr10_parser_path_button.clicked.connect(lambda: self.select_hdr10_parser())
        layout.addWidget(hdr10_parser_label, row, 0)
        layout.addWidget(self.hdr10_parser_path, row, 1)
        layout.addWidget(hdr10_parser_path_button, row, 2)
        row += 1

        # gifski
        gifski_label = QtWidgets.QLabel(link("https://gif.ski/", "gifski", self.app.fastflix.config.theme))
        gifski_label.setOpenExternalLinks(True)
        self.gifski_path = QtWidgets.QLineEdit()
        if self.app.fastflix.config.gifski:
            self.gifski_path.setText(str(self.app.fastflix.config.gifski))
        gifski_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        gifski_path_button.setFixedWidth(30)
        gifski_path_button.clicked.connect(lambda: self.select_gifski())
        layout.addWidget(gifski_label, row, 0)
        layout.addWidget(self.gifski_path, row, 1)
        layout.addWidget(gifski_path_button, row, 2)
        row += 1

        # Detected External Programs section
        detected_group = QtWidgets.QGroupBox(t("Detected External Programs"))
        detected_layout = QtWidgets.QGridLayout()
        detected_layout.setColumnStretch(1, 1)

        programs = [
            (self.app.fastflix.config.nvencc is not None, "NVEncC", t("NVIDIA hardware encoding")),
            (self.app.fastflix.config.qsvencc is not None, "QSVEncC", t("Intel hardware encoding")),
            (self.app.fastflix.config.vceencc is not None, "VCEEncC", t("AMD hardware encoding")),
            (self.app.fastflix.config.hdr10plus_parser is not None, "HDR10+ Parser", t("HDR10+ metadata extraction")),
            (self.app.fastflix.config.gifski is not None, "gifski", t("High quality GIF encoding")),
            (self.app.fastflix.config.pgs_ocr_available, "Tesseract + pgsrip", t("PGS subtitle OCR")),
        ]

        for det_row, (detected, name, description) in enumerate(programs):
            icon = "\u2714" if detected else "\u2718"
            color = "green" if detected else "red"
            status_label = QtWidgets.QLabel(f'<span style="color: {color};">{icon}</span>')
            detected_layout.addWidget(status_label, det_row, 0)
            detected_layout.addWidget(QtWidgets.QLabel(f"<b>{name}</b>"), det_row, 1)
            detected_layout.addWidget(QtWidgets.QLabel(description), det_row, 2)

        if not self.app.fastflix.config.pgs_ocr_available:
            ocr_link = QtWidgets.QLabel(
                link(
                    "https://github.com/cdgriffith/FastFlix/wiki/PGS-OCR-Setup",
                    t("PGS OCR setup instructions"),
                    self.app.fastflix.config.theme,
                )
            )
            ocr_link.setOpenExternalLinks(True)
            detected_layout.addWidget(ocr_link, len(programs), 0, 1, 3)

        detected_group.setLayout(detected_layout)
        layout.addWidget(detected_group, row, 0, 1, 3)
        row += 1

        # Spacer
        layout.setRowStretch(row, 1)

        tab.setLayout(layout)
        return tab

    def save(self):
        new_ffmpeg = Path(self.ffmpeg_path.text())
        new_ffprobe = Path(self.ffprobe_path.text())
        new_work_dir = Path(self.work_dir.text())
        restart_needed = False
        encoder_reload_needed = False
        try:
            updated_ffmpeg = self.update_ffmpeg(new_ffmpeg)
            if updated_ffmpeg:
                encoder_reload_needed = True
            self.update_ffprobe(new_ffprobe)
        except FastFlixInternalException:
            return

        try:
            new_work_dir.mkdir(exist_ok=True, parents=True)
        except OSError:
            error_message(f'{t("Could not create / access work directory")} "{new_work_dir}"', parent=self)
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
                self.app.fastflix.config.language = Language(self.language_combo.currentText()).pt3
        except InvalidLanguageValue:
            error_message(
                f"{t('Could not set language to')} {self.language_combo.currentText()}\n {t('Please report this issue')}",
                parent=self,
            )
        self.app.fastflix.config.disable_version_check = self.disable_version_check.isChecked()
        log_level = (self.logger_level_widget.currentIndex() + 1) * 10
        self.app.fastflix.config.logging_level = log_level
        logger.setLevel(log_level)
        self.app.fastflix.config.crop_detect_points = int(self.crop_detect_points_widget.currentText())

        new_nvencc = Path(self.nvencc_path.text()) if self.nvencc_path.text().strip() else None
        if str(self.app.fastflix.config.nvencc) != str(new_nvencc):
            encoder_reload_needed = True
        self.app.fastflix.config.nvencc = new_nvencc

        new_qsvencc = Path(self.qsvenc_path.text()) if self.qsvenc_path.text().strip() else None
        if str(self.app.fastflix.config.qsvencc) != str(new_qsvencc):
            encoder_reload_needed = True
        self.app.fastflix.config.qsvencc = new_qsvencc

        new_vce = Path(self.vceenc_path.text()) if self.vceenc_path.text().strip() else None
        if str(self.app.fastflix.config.vceencc) != str(new_vce):
            encoder_reload_needed = True
        self.app.fastflix.config.vceencc = new_vce

        new_hdr10_parser = Path(self.hdr10_parser_path.text()) if self.hdr10_parser_path.text().strip() else None
        if str(self.app.fastflix.config.hdr10plus_parser) != str(new_hdr10_parser):
            encoder_reload_needed = True
        self.app.fastflix.config.hdr10plus_parser = new_hdr10_parser

        new_gifski = Path(self.gifski_path.text()) if self.gifski_path.text().strip() else None
        if str(self.app.fastflix.config.gifski) != str(new_gifski):
            encoder_reload_needed = True
        self.app.fastflix.config.gifski = new_gifski

        new_output_path = None
        if self.output_path_line_edit.text().strip() and not self.default_output_dir.isChecked():
            new_output_path = Path(self.output_path_line_edit.text())
        self.app.fastflix.config.output_directory = new_output_path

        new_source_path = None
        if self.source_path_line_edit.text().strip() and not self.default_source_dir.isChecked():
            new_source_path = Path(self.source_path_line_edit.text())
        self.app.fastflix.config.source_directory = new_source_path

        old_scale = self.app.fastflix.config.ui_scale
        self.app.fastflix.config.ui_scale = scale_digits[scale_percents.index(self.ui_scale_widget.currentText())]
        if self.app.fastflix.config.ui_scale != old_scale:
            restart_needed = True

        # Output naming template
        new_template = self.template_edit.text().strip()
        if new_template:
            is_valid, msg = validate_template(new_template)
            if not is_valid:
                error_message(f"{t('Invalid output naming template')}: {msg}", parent=self)
                return
            self.app.fastflix.config.output_name_format = new_template
        else:
            self.app.fastflix.config.output_name_format = "{source}-fastflix-{rand_4}"

        self.app.fastflix.config.clean_old_logs = self.clean_old_logs_button.isChecked()
        self.app.fastflix.config.sticky_tabs = self.sticky_tabs.isChecked()
        self.app.fastflix.config.show_complete_message = self.show_complete_message.isChecked()
        self.app.fastflix.config.show_error_message = self.show_error_message.isChecked()
        self.app.fastflix.config.disable_deinterlace_check = self.disable_deinterlace_button.isChecked()
        self.app.fastflix.config.use_keyframes_for_preview = self.use_keyframes_for_preview.isChecked()
        self.app.fastflix.config.auto_detect_subtitles = self.auto_detect_subtitles.isChecked()

        self.main.config_update(encoder_reload_needed=encoder_reload_needed)
        self.app.fastflix.config.save()
        if old_lang != self.app.fastflix.config.language or restart_needed:
            error_message(t("Please restart FastFlix to apply settings"), parent=self)
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

    def select_gifski(self):
        dirname = Path(self.gifski_path.text()).parent
        if not dirname.exists():
            dirname = Path()
        filename = QtWidgets.QFileDialog.getOpenFileName(self, caption="gifski location", dir=str(dirname))
        if not filename or not filename[0]:
            return
        self.gifski_path.setText(str(Path(filename[0]).absolute()))

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
