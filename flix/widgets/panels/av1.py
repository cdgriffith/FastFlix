import logging

from box import Box

from flix.shared import QtGui, QtCore, QtWidgets, error_message, main_width

logger = logging.getLogger('flix')


class AV1(QtWidgets.QWidget):

    def __init__(self, parent, main):
        super(AV1, self).__init__(parent)
        self.main = main

        grid = QtWidgets.QGridLayout()

        grid.addWidget(QtWidgets.QLabel("AV1"), 0, 0)

        self.widgets = Box(
            fps=None,
            remove_hdr=None,
            mode=None)

        self.mode = 'QP'

        grid.addLayout(self.init_remove_hdr(), 1, 0, 1, 2)
        grid.addLayout(self.init_modes(), 0, 2, 4, 4)

        grid.addWidget(QtWidgets.QWidget(), 5, 0, 5, 2)
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
        layout.addWidget(QtWidgets.QLabel('Remove HDR'))
        self.widgets.remove_hdr = QtWidgets.QComboBox()
        self.widgets.remove_hdr.addItems(['No', 'Yes'])
        self.widgets.remove_hdr.setCurrentIndex(0)
        self.widgets.remove_hdr.setDisabled(True)
        self.widgets.remove_hdr.currentIndexChanged.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.remove_hdr)
        return layout

    def init_modes(self):
        layout = QtWidgets.QGridLayout()
        qp_group_box = QtWidgets.QGroupBox()
        qp_group_box.setStyleSheet("QGroupBox{padding-top:5px; margin-top:-18px}")
        qp_box_layout = QtWidgets.QHBoxLayout()
        bitrate_group_box = QtWidgets.QGroupBox()
        bitrate_group_box.setStyleSheet("QGroupBox{padding-top:5px; margin-top:-18px}")
        bitrate_box_layout = QtWidgets.QHBoxLayout()
        # rotation_dir = Path(base_path, 'data', 'rotations')
        # group_box.setStyleSheet("QGroupBox{padding-top:15px; margin-top:-15px; padding-bottom:-5px}")
        self.widgets.mode = QtWidgets.QButtonGroup()
        self.widgets.mode.buttonClicked.connect(self.set_mode)

        bitrate_radio = QtWidgets.QRadioButton("Bitrate")
        self.widgets.mode.addButton(bitrate_radio)
        self.widgets.bitrate = QtWidgets.QComboBox()
        self.widgets.bitrate.addItems(['30'])
        self.widgets.bitrate.currentIndexChanged.connect(lambda: self.main.build_commands())
        # self.widgets.bitrate.setCurrentIndex(6)
        bitrate_box_layout.addWidget(bitrate_radio)
        bitrate_box_layout.addWidget(self.widgets.bitrate)

        qp_radio = QtWidgets.QRadioButton("QP")
        qp_radio.setChecked(True)
        self.widgets.mode.addButton(qp_radio)

        self.widgets.qp = QtWidgets.QComboBox()
        self.widgets.qp.addItems(['30'])
        self.widgets.qp.setCurrentIndex(0)
        self.widgets.qp.currentIndexChanged.connect(lambda: self.main.build_commands())

        qp_box_layout.addWidget(qp_radio)
        qp_box_layout.addWidget(self.widgets.qp)

        bitrate_group_box.setLayout(bitrate_box_layout)
        qp_group_box.setLayout(qp_box_layout)

        layout.addWidget(qp_group_box, 0, 0)
        layout.addWidget(bitrate_group_box, 1, 0)
        return layout

    def get_settings(self):
        settings = Box(
            disable_hdr=bool(self.widgets.remove_hdr.currentIndex()),
        )
        if self.mode == "CRF":
            settings.qp = int(self.widgets.qp.currentText().split(" ", 1)[0])
        else:
            settings.bitrate = self.widgets.bitrate.currentText().split(" ", 1)[0]
        logger.info(settings)
        return settings

    def new_source(self):
        if not self.main.streams:
            return
        if self.main.streams['video'][self.main.video_track].get('color_space', '').startswith('bt2020'):
            self.widgets.remove_hdr.setDisabled(False)
        else:
            self.widgets.remove_hdr.setDisabled(True)

    def set_mode(self, x):
        self.mode = x.text()
