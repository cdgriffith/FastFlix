# -*- coding: utf-8 -*-
import logging
from typing import List

from box import Box
from qtpy import QtGui, QtWidgets

from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp

logger = logging.getLogger("fastflix")

ffmpeg_extra_command = ""


class SettingPanel(QtWidgets.QWidget):
    def __init__(self, parent, main, app: FastFlixApp, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.main = main
        self.app = app
        self.widgets = Box()
        self.labels = Box()
        self.opts = Box()
        self.only_int = QtGui.QIntValidator()

    @staticmethod
    def translate_tip(tooltip):
        return "\n".join([t(x) for x in tooltip.split("\n") if x.strip()])

    def determine_default(self, widget_name, opt, items: List):
        if widget_name == "pix_fmt":
            items = [x.split(":")[1].strip() for x in items]
        elif widget_name in ("crf", "qp"):
            if not opt:
                return 6
            items = [x.split("(")[0].strip() for x in items]
            opt = str(opt)
        elif widget_name == "bitrate":
            if not opt:
                return 5
            items = [x.split("(")[0].strip() for x in items]
        if isinstance(opt, str):
            try:
                return items.index(opt)
            except Exception:
                logger.error(f"Could not set default for {widget_name} to {opt} as it's not in the list")
                return 0
        if isinstance(opt, bool):
            return int(opt)
        return opt

    def _add_combo_box(
        self, label, options, widget_name, opt=None, connect="default", enabled=True, default=0, tooltip=""
    ):
        layout = QtWidgets.QHBoxLayout()
        self.labels[widget_name] = QtWidgets.QLabel(t(label))
        if tooltip:
            self.labels[widget_name].setToolTip(self.translate_tip(tooltip))

        self.widgets[widget_name] = QtWidgets.QComboBox()
        self.widgets[widget_name].addItems(options)

        if opt:
            default = self.determine_default(
                widget_name, self.app.fastflix.config.encoder_opt(self.profile_name, opt), options
            )
            self.opts[widget_name] = opt
        self.widgets[widget_name].setCurrentIndex(default or 0)
        self.widgets[widget_name].setDisabled(not enabled)
        if tooltip:
            self.widgets[widget_name].setToolTip(self.translate_tip(tooltip))
        if connect:
            if connect == "default":
                self.widgets[widget_name].currentIndexChanged.connect(lambda: self.main.page_update())
            elif connect == "self":
                self.widgets[widget_name].currentIndexChanged.connect(lambda: self.page_update())
            else:
                self.widgets[widget_name].currentIndexChanged.connect(connect)

        layout.addWidget(self.labels[widget_name])
        layout.addWidget(self.widgets[widget_name])

        return layout

    def _add_check_box(self, label, widget_name, opt, connect="default", enabled=True, checked=True, tooltip=""):
        layout = QtWidgets.QHBoxLayout()
        # self.labels[widget_name] = QtWidgets.QLabel()
        # self.labels[widget_name].setToolTip()

        self.widgets[widget_name] = QtWidgets.QCheckBox(t(label))
        self.opts[widget_name] = opt
        self.widgets[widget_name].setChecked(self.app.fastflix.config.encoder_opt(self.profile_name, opt))
        self.widgets[widget_name].setDisabled(not enabled)
        if tooltip:
            self.widgets[widget_name].setToolTip(self.translate_tip(tooltip))
        if connect:
            if connect == "default":
                self.widgets[widget_name].toggled.connect(lambda: self.main.page_update())
            elif connect == "self":
                self.widgets[widget_name].toggled.connect(lambda: self.page_update())
            else:
                self.widgets[widget_name].toggled.connect(connect)

        # layout.addWidget(self.labels[widget_name])
        layout.addWidget(self.widgets[widget_name])

        return layout

    def _add_custom(self, connect="default"):
        layout = QtWidgets.QHBoxLayout()
        self.labels.ffmpeg_options = QtWidgets.QLabel(t("Custom ffmpeg options"))
        self.labels.ffmpeg_options.setToolTip(t("Extra flags or options, cannot modify existing settings"))
        layout.addWidget(self.labels.ffmpeg_options)
        self.ffmpeg_extras_widget = QtWidgets.QLineEdit()
        self.ffmpeg_extras_widget.setText(ffmpeg_extra_command)
        if connect and connect != "default":
            self.ffmpeg_extras_widget.disconnect()
            if connect == "self":
                connect = lambda: self.page_update()
            self.ffmpeg_extras_widget.textChanged.connect(connect)
        else:
            self.ffmpeg_extras_widget.textChanged.connect(lambda: self.ffmpeg_extra_update())
        layout.addWidget(self.ffmpeg_extras_widget)
        return layout

    def _add_file_select(self, label, widget_name, button_action, connect="default", enabled=True, tooltip=""):
        layout = QtWidgets.QHBoxLayout()
        self.labels[widget_name] = QtWidgets.QLabel(t(label))
        self.labels[widget_name].setToolTip(tooltip)

        self.widgets[widget_name] = QtWidgets.QLineEdit()
        self.widgets[widget_name].setDisabled(not enabled)
        self.widgets[widget_name].setToolTip(tooltip)

        if connect:
            if connect == "default":
                self.widgets[widget_name].textChanged.connect(lambda: self.main.page_update())
            elif connect == "self":
                self.widgets[widget_name].textChanged.connect(lambda: self.page_update())
            else:
                self.widgets[widget_name].textChanged.connect(connect)

        button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogContentsView))
        button.clicked.connect(button_action)

        layout.addWidget(self.labels[widget_name])
        layout.addWidget(self.widgets[widget_name])
        layout.addWidget(button)
        return layout

    def _add_modes(
        self,
        recommended_bitrates,
        recommended_qps,
        qp_name="crf",
    ):
        layout = QtWidgets.QGridLayout()
        qp_group_box = QtWidgets.QGroupBox()
        qp_group_box.setStyleSheet("QGroupBox{padding-top:5px; margin-top:-18px}")
        qp_box_layout = QtWidgets.QHBoxLayout()
        bitrate_group_box = QtWidgets.QGroupBox()
        bitrate_group_box.setStyleSheet("QGroupBox{padding-top:5px; margin-top:-18px}")
        bitrate_box_layout = QtWidgets.QHBoxLayout()
        self.widgets.mode = QtWidgets.QButtonGroup()
        self.widgets.mode.buttonClicked.connect(self.set_mode)

        bitrate_radio = QtWidgets.QRadioButton("Bitrate")
        bitrate_radio.setFixedWidth(80)
        self.widgets.mode.addButton(bitrate_radio)
        self.widgets.bitrate = QtWidgets.QComboBox()
        self.widgets.bitrate.setFixedWidth(250)
        self.widgets.bitrate.addItems(recommended_bitrates)
        config_opt = self.app.fastflix.config.encoder_opt(self.profile_name, "bitrate")
        if config_opt:
            self.mode = "Bitrate"
        self.widgets.bitrate.setCurrentIndex(self.determine_default("bitrate", config_opt, recommended_bitrates))
        self.widgets.bitrate.currentIndexChanged.connect(lambda: self.mode_update())
        self.widgets.custom_bitrate = QtWidgets.QLineEdit("3000")
        self.widgets.custom_bitrate.setFixedWidth(100)
        self.widgets.custom_bitrate.setDisabled(True)
        self.widgets.custom_bitrate.textChanged.connect(lambda: self.main.build_commands())
        bitrate_box_layout.addWidget(bitrate_radio)
        bitrate_box_layout.addWidget(self.widgets.bitrate)
        bitrate_box_layout.addStretch()
        bitrate_box_layout.addWidget(QtWidgets.QLabel("Custom:"))
        bitrate_box_layout.addWidget(self.widgets.custom_bitrate)

        qp_help = (
            f"{qp_name.upper()} {t('is extremely source dependant')},\n"
            f"{t('the resolution-to-')}{qp_name.upper()}{t('are mere suggestions!')}"
        )
        qp_radio = QtWidgets.QRadioButton(qp_name.upper())
        qp_radio.setChecked(True)
        qp_radio.setFixedWidth(80)
        qp_radio.setToolTip(qp_help)
        self.widgets.mode.addButton(qp_radio)

        self.widgets[qp_name] = QtWidgets.QComboBox()
        self.widgets[qp_name].setToolTip(qp_help)
        self.widgets[qp_name].setFixedWidth(250)
        self.widgets[qp_name].addItems(recommended_qps)
        self.widgets[qp_name].setCurrentIndex(
            self.determine_default(
                qp_name, self.app.fastflix.config.encoder_opt(self.profile_name, qp_name), recommended_qps
            )
        )
        self.widgets[qp_name].currentIndexChanged.connect(lambda: self.mode_update())
        self.widgets[f"custom_{qp_name}"] = QtWidgets.QLineEdit("30")
        self.widgets[f"custom_{qp_name}"].setFixedWidth(100)
        self.widgets[f"custom_{qp_name}"].setDisabled(True)
        self.widgets[f"custom_{qp_name}"].setValidator(self.only_int)
        self.widgets[f"custom_{qp_name}"].textChanged.connect(lambda: self.main.build_commands())
        qp_box_layout.addWidget(qp_radio)
        qp_box_layout.addWidget(self.widgets[qp_name])
        qp_box_layout.addStretch()
        qp_box_layout.addWidget(QtWidgets.QLabel("Custom:"))
        qp_box_layout.addWidget(self.widgets[f"custom_{qp_name}"])

        bitrate_group_box.setLayout(bitrate_box_layout)
        qp_group_box.setLayout(qp_box_layout)

        layout.addWidget(qp_group_box, 0, 0)
        layout.addWidget(bitrate_group_box, 1, 0)

        return layout

    @property
    def ffmpeg_extras(self):
        return ffmpeg_extra_command

    def ffmpeg_extra_update(self):
        global ffmpeg_extra_command
        ffmpeg_extra_command = self.ffmpeg_extras_widget.text().strip()
        self.main.page_update()

    def new_source(self):
        if not self.app.fastflix.current_video or not self.app.fastflix.current_video.streams:
            return
        # elif (
        #     self.app.fastflix.current_video.streams["video"][self.main.video_track]
        #     .get("color_space", "")
        #     .startswith("bt2020")
        # ):
        #     self.widgets.remove_hdr.setDisabled(False)
        #     self.labels.remove_hdr.setStyleSheet("QLabel{color:#000}")
        # else:
        #     self.widgets.remove_hdr.setDisabled(True)
        #     self.labels.remove_hdr.setStyleSheet("QLabel{color:#000}")

    def update_profile(self):
        for widget_name, opt in self.opts.items():
            if isinstance(self.widgets[widget_name], QtWidgets.QComboBox):
                default = self.determine_default(
                    widget_name,
                    self.app.fastflix.config.encoder_opt(self.profile_name, opt),
                    [self.widgets[widget_name].itemText(i) for i in range(self.widgets[widget_name].count())],
                )
                if default is not None:
                    self.widgets[widget_name].setCurrentIndex(default)
            elif isinstance(self.widgets[widget_name], QtWidgets.QCheckBox):
                checked = self.app.fastflix.config.encoder_opt(self.profile_name, opt)
                if checked is not None:
                    self.widgets[widget_name].setChecked(checked)
            elif isinstance(self.widgets[widget_name], QtWidgets.QLineEdit):
                data = self.app.fastflix.config.encoder_opt(self.profile_name, opt)
                if widget_name == "x265_params":
                    data = ":".join(data)
                self.widgets[widget_name].setText(data or "")

    def init_max_mux(self):
        return self._add_combo_box(
            label=t("Max Muxing Queue Size"),
            tooltip=t('Useful when you have the "Too many packets buffered for output stream" error'),
            widget_name="max_mux",
            options=["default", "1024", "2048", "4096", "8192"],
            opt="max_muxing_queue_size",
        )

    def reload(self):
        for widget_name, opt in self.opts.items():
            data = getattr(self.app.fastflix.current_video.video_settings.video_encoder_settings, opt)
            if isinstance(self.widgets[widget_name], QtWidgets.QComboBox):
                if isinstance(data, int):
                    self.widgets[widget_name].setCurrentIndex(data)
                else:
                    self.widgets[widget_name].setCurrentText(data)
            elif isinstance(self.widgets[widget_name], QtWidgets.QCheckBox):
                self.widgets[widget_name].setChecked(data)
            elif isinstance(self.widgets[widget_name], QtWidgets.QLineEdit):
                if widget_name == "x265_params":
                    data = ":".join(data)
                self.widgets[widget_name].setText(data or "")
