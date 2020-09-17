# -*- coding: utf-8 -*-

from box import Box
from qtpy import QtWidgets


class SettingPanel(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widgets = Box()
        self.labels = Box()

    def _add_combo_box(self, label, options, widget_name, connect="default", enabled=True, default=0, tooltip=""):
        layout = QtWidgets.QHBoxLayout()
        self.labels[widget_name] = QtWidgets.QLabel(label)
        self.labels[widget_name].setToolTip(tooltip)

        self.widgets[widget_name] = QtWidgets.QComboBox()
        self.widgets[widget_name].addItems(options)
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

    def _add_check_box(self, label, widget_name, connect="default", enabled=True, checked=True, tooltip=""):
        layout = QtWidgets.QHBoxLayout()
        self.labels[widget_name] = QtWidgets.QLabel(label)
        self.labels[widget_name].setToolTip(tooltip)

        self.widgets[widget_name] = QtWidgets.QCheckBox()
        self.widgets[widget_name].setChecked(checked)
        self.widgets[widget_name].setDisabled(not enabled)
        if connect:
            if connect == "default":
                self.widgets[widget_name].toggled.connect(lambda: self.main.page_update())
            elif connect == "self":
                self.widgets[widget_name].toggled.connect(lambda: self.page_update())
            else:
                self.widgets[widget_name].toggled.connect(connect)

        layout.addWidget(self.labels[widget_name])
        layout.addWidget(self.widgets[widget_name])

        return layout

    def _add_custom(self, widget_name="extra", connect="default"):
        layout = QtWidgets.QHBoxLayout()
        self.labels.ffmpeg_options = QtWidgets.QLabel("Custom ffmpeg options")
        self.labels.ffmpeg_options.setToolTip("Extra flags or options, cannot modify existing settings")
        layout.addWidget(self.labels.ffmpeg_options)
        self.widgets[widget_name] = QtWidgets.QLineEdit()
        if connect:
            if connect == "default":
                self.widgets[widget_name].textChanged.connect(lambda: self.main.page_update())
            elif connect == "self":
                self.widgets[widget_name].textChanged.connect(lambda: self.page_update())
            else:
                self.widgets[widget_name].textChanged.connect(connect)
        layout.addWidget(self.widgets[widget_name])
        return layout
