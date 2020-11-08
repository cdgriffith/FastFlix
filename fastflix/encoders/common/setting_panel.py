# -*- coding: utf-8 -*-
import logging
from typing import List

from box import Box
from qtpy import QtGui, QtWidgets

from fastflix.models.fastflix_app import FastFlixApp
from fastflix.language import t

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

    def determine_default(self, widget_name, opt, items: List):
        if widget_name == "pix_fmt":
            items = [x.split(":")[1].strip() for x in items]
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
        self.labels[widget_name].setToolTip(tooltip)

        self.widgets[widget_name] = QtWidgets.QComboBox()
        self.widgets[widget_name].addItems(options)

        if opt:
            default = self.determine_default(
                widget_name, self.app.fastflix.config.encoder_opt(self.profile_name, opt), options
            )
            self.opts[widget_name] = opt
        self.widgets[widget_name].setCurrentIndex(default)
        self.widgets[widget_name].setDisabled(not enabled)
        self.widgets[widget_name].setToolTip(tooltip)
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
        self.widgets[widget_name].setToolTip(tooltip)
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
        self.widgets.bitrate.setCurrentIndex(6)
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
            f"{qp_name.upper()} is extremely source dependant,<br>"
            f"the resolution-to-{qp_name.upper()} are mere suggestions!<br>"
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
        self.widgets[qp_name].setCurrentIndex(5)
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

    def _add_remove_hdr(self, connect="default"):
        return self._add_combo_box(
            label="Remove HDR",
            widget_name="remove_hdr",
            options=["No", "Yes"],
            tooltip=(
                "Convert BT2020 colorspace into bt709\n "
                "WARNING: This will take much longer and result in a larger file"
            ),
            opt="remove_hdr",
            connect=connect,
        )

    @property
    def ffmpeg_extras(self):
        return ffmpeg_extra_command

    def ffmpeg_extra_update(self):
        global ffmpeg_extra_command
        ffmpeg_extra_command = self.ffmpeg_extras_widget.text().strip()
        self.main.page_update()

    def new_source(self):
        if not self.app.fastflix.current_video.streams:
            return
        elif (
            self.app.fastflix.current_video.streams["video"][self.main.video_track]
            .get("color_space", "")
            .startswith("bt2020")
        ):
            self.widgets.remove_hdr.setDisabled(False)
            self.labels.remove_hdr.setStyleSheet("QLabel{color:#000}")
        else:
            self.widgets.remove_hdr.setDisabled(True)
            self.labels.remove_hdr.setStyleSheet("QLabel{color:#000}")

    def update_profile(self):
        for widget_name, opt in self.opts.items():
            if isinstance(self.widgets[widget_name], QtWidgets.QComboBox):
                default = self.determine_default(
                    widget_name,
                    self.app.fastflix.config.encoder_opt(self.profile_name, opt),
                    [self.widgets[widget_name].itemText(i) for i in range(self.widgets[widget_name].count())],
                )
                self.widgets[widget_name].setCurrentIndex(default)
            elif isinstance(self.widgets[widget_name], QtWidgets.QCheckBox):
                self.widgets[widget_name].setChecked(self.app.fastflix.config.encoder_opt(self.profile_name, opt))

    def init_max_mux(self):
        return self._add_combo_box(
            label="Max Muxing Queue Size",
            tooltip='Useful when you have the "Too many packets buffered for output stream" error',
            widget_name="max_mux",
            options=["default", "1024", "2048", "4096", "8192"],
            opt="max_muxing_queue_size",
        )
