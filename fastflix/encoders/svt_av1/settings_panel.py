# -*- coding: utf-8 -*-
import logging

from box import Box

from qtpy import QtWidgets, QtCore, QtGui

logger = logging.getLogger("fastflix")

recommended_bitrates = [
    "150k   (320x240p @ 30fps)",
    "276k   (640x360p @ 30fps)",
    "512k   (640x480p @ 30fps)",
    "1024k  (1280x720p @ 30fps)",
    "1800k (1280x720p @ 60fps)",
    "1800k (1920x1080p @ 30fps)",
    "3000k (1920x1080p @ 60fps)",
    "6000k (2560x1440p @ 30fps)",
    "9000k (2560x1440p @ 60fps)",
    "12000k (3840x2160p @ 30fps)",
    "18000k (3840x2160p @ 60fps)",
    "Custom",
]

recommended_qp = ["24 - recommended", "30 - standard", '50 - "I\'m just testing to see if this works"', "Custom"]
pix_fmts = ["8-bit: yuv420p", "10-bit: yuv420p10le"]


class SVT_AV1(QtWidgets.QWidget):
    def __init__(self, parent, main):
        super(SVT_AV1, self).__init__(parent)
        self.main = main
        grid = QtWidgets.QGridLayout()

        self.widgets = Box(fps=None, remove_hdr=None, mode=None, segment_size=None)

        self.mode = "QP"

        grid.addLayout(self.init_speed(), 0, 0, 1, 2)
        grid.addLayout(self.init_remove_hdr(), 1, 0, 1, 2)
        grid.addLayout(self.init_pix_fmts(), 2, 0, 1, 2)
        grid.addLayout(self.init_tile_rows(), 3, 0, 1, 2)
        grid.addLayout(self.init_tile_columns(), 4, 0, 1, 2)
        grid.addLayout(self.init_tier(), 5, 0, 1, 2)
        grid.addLayout(self.init_sc_detection(), 6, 0, 1, 2)

        grid.addLayout(self.init_modes(), 0, 2, 4, 4)
        grid.addLayout(self.init_single_pass(), 4, 2, 1, 1)
        grid.addWidget(QtWidgets.QWidget(), 5, 0)
        grid.setRowStretch(5, 1)
        guide_label = QtWidgets.QLabel(
            f"<a href='https://github.com/AOMediaCodec/SVT-AV1/blob/master/Docs/svt-av1_encoder_user_guide.md'>SVT-AV1 Encoding Guide</a>"
        )
        guide_label.setAlignment(QtCore.Qt.AlignBottom)
        guide_label.setOpenExternalLinks(True)
        grid.addWidget(guide_label, 9, 0, -1, 1)
        self.setLayout(grid)
        self.hide()

    # def init_fps(self):
    #     layout = QtWidgets.QHBoxLayout()
    #     layout.addWidget(QtWidgets.QLabel("FPS"))
    #     self.widgets.fps = QtWidgets.QComboBox()
    #     self.widgets.fps.addItems([str(x) for x in range(1, 31)])
    #     self.widgets.fps.setCurrentIndex(14)
    #     self.widgets.fps.currentIndexChanged.connect(lambda: self.main.build_commands())
    #     layout.addWidget(self.widgets.fps)
    #     return layout

    def _add_combo_box(self, label, options, widget_name, connect="default", enabled=True, default=0, tooltip=""):
        layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel(label)
        label.setToolTip(tooltip)
        layout.addWidget(label)
        self.widgets[widget_name] = QtWidgets.QComboBox()
        self.widgets[widget_name].addItems(options)
        self.widgets[widget_name].setCurrentIndex(default)
        self.widgets[widget_name].setDisabled(not enabled)
        if connect:
            if connect == "default":
                self.widgets[widget_name].currentIndexChanged.connect(lambda: self.main.page_update())
            else:
                self.widgets[widget_name].currentIndexChanged.connect(connect)
        layout.addWidget(self.widgets[widget_name])

        return layout, self.widgets[widget_name], label

    def init_tile_rows(self):
        layout, combo_box, label = self._add_combo_box("Tile Rows", [str(x) for x in range(0, 7)], "tile_rows")
        return layout

    def init_tile_columns(self):
        layout, combo_box, label = self._add_combo_box("Tile Columns", [str(x) for x in range(0, 5)], "tile_columns")
        return layout

    def init_pix_fmts(self):
        layout, combo_box, label = self._add_combo_box("Bit Depth", pix_fmts, "pix_fmt")
        return layout

    def init_tier(self):
        layout, combo_box, label = self._add_combo_box("Tier", ["main", "high"], "tier")
        return layout

    def init_sc_detection(self):
        layout, combo_box, label = self._add_combo_box("Scene Detection", ["false", "true"], "sc_detection")
        return layout

    def init_single_pass(self):
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel("Single Pass"))
        self.widgets.single_pass = QtWidgets.QCheckBox()
        self.widgets.single_pass.setChecked(False)
        self.widgets.single_pass.toggled.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.single_pass)
        return layout

    def init_remove_hdr(self):
        layout = QtWidgets.QHBoxLayout()
        self.remove_hdr_label = QtWidgets.QLabel("Remove HDR")
        self.remove_hdr_label.setToolTip(
            "Convert BT2020 colorspace into bt709\n " "WARNING: This will take much longer and result in a larger file"
        )
        layout.addWidget(self.remove_hdr_label)
        self.widgets.remove_hdr = QtWidgets.QComboBox()
        self.widgets.remove_hdr.addItems(["No", "Yes"])
        self.widgets.remove_hdr.setCurrentIndex(0)
        self.widgets.remove_hdr.setDisabled(True)
        self.widgets.remove_hdr.currentIndexChanged.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.remove_hdr)
        return layout

    def init_speed(self):
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel("Speed"))
        self.widgets.speed = QtWidgets.QComboBox()
        self.widgets.speed.addItems([str(x) for x in range(9)])
        self.widgets.speed.setCurrentIndex(7)
        self.widgets.speed.currentIndexChanged.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.speed)
        return layout

    def init_modes(self):
        layout = QtWidgets.QGridLayout()
        qp_group_box = QtWidgets.QGroupBox()
        qp_group_box.setStyleSheet("QGroupBox{padding-top:5px; margin-top:-18px}")
        qp_box_layout = QtWidgets.QHBoxLayout()

        # rotation_dir = Path(base_path, 'data', 'rotations')
        # group_box.setStyleSheet("QGroupBox{padding-top:15px; margin-top:-15px; padding-bottom:-5px}")
        self.widgets.mode = QtWidgets.QButtonGroup()
        self.widgets.mode.buttonClicked.connect(self.set_mode)

        bitrate_group_box = QtWidgets.QGroupBox()
        bitrate_group_box.setStyleSheet("QGroupBox{padding-top:5px; margin-top:-18px}")
        bitrate_box_layout = QtWidgets.QHBoxLayout()
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

        qp_radio = QtWidgets.QRadioButton("QP")
        qp_radio.setChecked(True)
        qp_radio.setFixedWidth(80)
        self.widgets.mode.addButton(qp_radio)

        self.widgets.qp = QtWidgets.QComboBox()
        self.widgets.qp.setFixedWidth(250)
        self.widgets.qp.addItems(recommended_qp)
        self.widgets.qp.setCurrentIndex(0)
        self.widgets.qp.currentIndexChanged.connect(lambda: self.mode_update())
        self.widgets.custom_qp = QtWidgets.QLineEdit("30")
        self.widgets.custom_qp.setFixedWidth(100)
        self.widgets.custom_qp.setDisabled(True)
        self.widgets.custom_qp.textChanged.connect(lambda: self.main.build_commands())
        qp_box_layout.addWidget(qp_radio)
        qp_box_layout.addWidget(self.widgets.qp)
        qp_box_layout.addStretch()
        qp_box_layout.addWidget(QtWidgets.QLabel("Custom:"))
        qp_box_layout.addWidget(self.widgets.custom_qp)

        bitrate_group_box.setLayout(bitrate_box_layout)
        qp_group_box.setLayout(qp_box_layout)

        bitrate_group_box.setLayout(bitrate_box_layout)
        qp_group_box.setLayout(qp_box_layout)

        layout.addWidget(qp_group_box, 0, 0)
        layout.addWidget(bitrate_group_box, 1, 0)
        return layout

    def mode_update(self):
        self.widgets.custom_qp.setDisabled(self.widgets.qp.currentText() != "Custom")
        self.widgets.custom_bitrate.setDisabled(self.widgets.bitrate.currentText() != "Custom")
        self.main.build_commands()

    def get_settings(self):
        settings = Box(
            disable_hdr=bool(self.widgets.remove_hdr.currentIndex()),
            speed=self.widgets.speed.currentText(),
            tile_columns=int(self.widgets.tile_columns.currentText()),
            tile_rows=int(self.widgets.tile_rows.currentText()),
            single_pass=self.widgets.single_pass.isChecked(),
            tier=int(self.widgets.tier.currentIndex()),
            sc_detection=int(self.widgets.sc_detection.currentIndex()),
            pix_fmt=self.widgets.pix_fmt.currentText().split(":")[1].strip(),
        )
        if self.mode == "QP":
            qp = self.widgets.qp.currentText()
            settings.qp = int(qp.split(" ", 1)[0]) if qp.lower() != "custom" else self.widgets.custom_qp.text()
        else:
            bitrate = self.widgets.bitrate.currentText()
            settings.bitrate = bitrate.split(" ", 1)[0] if bitrate.lower() != "custom" else self.widgets.bitrate.text()
        return settings

    def new_source(self):
        if not self.main.streams:
            return
        if "zcale" not in self.main.flix.filters:
            self.widgets.remove_hdr.setDisabled(True)
            self.remove_hdr_label.setStyleSheet("QLabel{color:#777}")
            self.remove_hdr_label.setToolTip("cannot remove HDR, zcale filter not in current version of FFmpeg")
            logger.warning("zcale filter not detected in current version of FFmpeg, cannot remove HDR")
        elif self.main.streams["video"][self.main.video_track].get("color_space", "").startswith("bt2020"):
            self.widgets.remove_hdr.setDisabled(False)
            self.remove_hdr_label.setStyleSheet("QLabel{color:#000}")
        else:
            self.widgets.remove_hdr.setDisabled(True)
            self.remove_hdr_label.setStyleSheet("QLabel{color:#000}")

    def set_mode(self, x):
        self.mode = x.text()
        self.main.build_commands()
