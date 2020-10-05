# -*- coding: utf-8 -*-
import logging

from box import Box
from qtpy import QtGui, QtWidgets

logger = logging.getLogger("fastflix")

ffmpeg_extra_command = ""


class SettingPanel(QtWidgets.QWidget):
    def __init__(self, parent, main, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.main = main
        self.widgets = Box()
        self.labels = Box()
        self.only_int = QtGui.QIntValidator()

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

    def _add_custom(self, connect="default"):
        layout = QtWidgets.QHBoxLayout()
        self.labels.ffmpeg_options = QtWidgets.QLabel("Custom ffmpeg options")
        self.labels.ffmpeg_options.setToolTip("Extra flags or options, cannot modify existing settings")
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

    def _add_remove_hdr(self, connect="default"):
        return self._add_combo_box(
            label="Remove HDR",
            widget_name="remove_hdr",
            options=["No", "Yes"],
            tooltip=(
                "Convert BT2020 colorspace into bt709\n "
                "WARNING: This will take much longer and result in a larger file"
            ),
            enabled=False,
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
        if not self.main.streams:
            return
        elif self.main.streams["video"][self.main.video_track].get("color_space", "").startswith("bt2020"):
            self.widgets.remove_hdr.setDisabled(False)
            self.labels.remove_hdr.setStyleSheet("QLabel{color:#000}")
        else:
            self.widgets.remove_hdr.setDisabled(True)
            self.labels.remove_hdr.setStyleSheet("QLabel{color:#000}")
