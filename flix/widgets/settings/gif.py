from box import Box

from flix.shared import QtGui, QtCore, QtWidgets, error_message, main_width


class GIF(QtWidgets.QWidget):

    def __init__(self, parent):
        super(GIF, self).__init__(parent)

        grid = QtWidgets.QGridLayout()

        grid.addWidget(QtWidgets.QLabel("GIF"), 0, 0)

        self.widgets = Box(
            fps=None,
            remove_hdr=None,
        dither=None)

        grid.addLayout(self.init_fps(), 1, 0)
        grid.addLayout(self.init_remove_hdr(), 2, 0)
        grid.addLayout(self.init_dither(), 3, 0)

        grid.addWidget(QtWidgets.QWidget(), 5, 0, 5, 2)
        self.setLayout(grid)

    def init_fps(self):
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel("FPS"))
        self.widgets.fps = QtWidgets.QComboBox()
        self.widgets.fps.addItems([str(x) for x in range(1, 31)])
        self.widgets.fps.setCurrentIndex(14)
        layout.addWidget(self.widgets.fps)
        return layout

    def init_remove_hdr(self):
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel('Remove HDR'))
        self.widgets.remove_hdr = QtWidgets.QComboBox()
        self.widgets.remove_hdr.addItems(['Auto Remove', 'Yes', 'No'])
        self.widgets.remove_hdr.setCurrentIndex(0)
        layout.addWidget(self.widgets.remove_hdr)
        return layout

    def init_dither(self):
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel('Dither'))
        self.widgets.dither = QtWidgets.QComboBox()
        self.widgets.dither.addItems(['dither'])
        self.widgets.dither.setCurrentIndex(0)
        layout.addWidget(self.widgets.remove_hdr)
        return layout

    def get_settings(self):
        return Box(
            fps=int(self.widgets.fps.currentText()),
            remove_hdr=self.widgets.remove_hdr.currentText(),
            dither=self.widgets.dither.currentText()
        )
