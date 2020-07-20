# -*- coding: utf-8 -*-
import logging

from box import Box

from fastflix.shared import QtWidgets, QtCore

logger = logging.getLogger("fastflix")

recommended_bitrates = [
    "150000   (320x240p @ 24,25,30)",
    "276000   (640x360p @ 24,25,30)",
    "512000   (640x480p @ 24,25,30)",
    "1024000  (1280x720p @ 24,25,30)",
    "1800000 (1280x720p @ 50,60)",
    "1800000 (1920x1080p @ 24,25,30)",
    "3000000 (1920x1080p @ 50,60)",
    "6000000 (2560x1440p @ 24,25,30)",
    "9000000 (2560x1440p @ 50,60)",
    "12000000 (3840x2160p @ 24,25,30)",
    "18000000 (3840x2160p @ 50,60)",
    "Custom",
]

recommended_qp = ["24 - recommended", "30 - standard", '50 - "I\'m just testing to see if this works"', "Custom"]


class AV1(QtWidgets.QWidget):
    def __init__(self, parent, main):
        super(AV1, self).__init__(parent)
        self.main = main
        grid = QtWidgets.QGridLayout()

        self.widgets = Box(fps=None, remove_hdr=None, mode=None, segment_size=None)

        self.mode = "QP"

        grid.addLayout(self.init_remove_hdr(), 1, 0, 1, 2)
        grid.addLayout(self.init_speed(), 0, 0, 1, 2)

        grid.addLayout(self.init_modes(), 0, 2, 4, 4)
        grid.addLayout(self.init_segment_size(), 3, 0, 1, 2)

        grid.addWidget(QtWidgets.QWidget(), 5, 0)
        grid.setRowStretch(5, 1)
        guide_label = QtWidgets.QLabel(f"<a href='https://github.com/OpenVisualCloud/SVT-AV1'>SVT-AV1 Github</a>")
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

    def init_remove_hdr(self):
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel("Remove HDR"))
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

    def init_segment_size(self):
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel("Segment Size (seconds)"))
        self.widgets.segment_size = QtWidgets.QComboBox()
        self.widgets.segment_size.addItems(["10", "30", "60", "90", "120", "240"])
        self.widgets.segment_size.setCurrentIndex(2)
        self.widgets.segment_size.currentIndexChanged.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.segment_size)
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
            segment_size=int(self.widgets.segment_size.currentText()),
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
        if self.main.streams["video"][self.main.video_track].get("color_space", "").startswith("bt2020"):
            self.widgets.remove_hdr.setDisabled(False)
        else:
            self.widgets.remove_hdr.setDisabled(True)

    def set_mode(self, x):
        self.mode = x.text()
