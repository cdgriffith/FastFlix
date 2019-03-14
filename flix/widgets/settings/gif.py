from flix.shared import QtGui, QtCore, QtWidgets, error_message, main_width


class GIF(QtWidgets.QWidget):

    def __init__(self, parent):
        super(GIF, self).__init__(parent)

        grid = QtWidgets.QGridLayout()

        grid.addWidget(QtWidgets.QLabel("GIF"))

        self.setLayout(grid)
