# -*- coding: utf-8 -*-
"""A modern sliding toggle switch widget, drop-in replacement for QCheckBox."""

from PySide6 import QtCore, QtGui, QtWidgets


class ToggleSwitch(QtWidgets.QCheckBox):
    """A sliding toggle switch that subclasses QCheckBox.

    Drop-in replacement — emits the same stateChanged/toggled signals,
    works with isChecked()/setChecked(), and supports a text label.
    """

    def __init__(self, text="", parent=None, track_color="#444444", active_color="#4a9eed", knob_color="#ffffff"):
        super().__init__(text, parent)
        self.track_color = QtGui.QColor(track_color)
        self.active_color = QtGui.QColor(active_color)
        self.knob_color = QtGui.QColor(knob_color)

        self._track_width = 24
        self._track_height = 12
        self._knob_diameter = 8
        self._knob_margin = 2
        self._label_spacing = 8

        self._knob_position = 0.0
        self._animation = QtCore.QPropertyAnimation(self, b"knob_position", self)
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QtCore.QEasingCurve.InOutCubic)

        self.stateChanged.connect(self._animate)

    def _get_knob_position(self):
        return self._knob_position

    def _set_knob_position(self, value):
        self._knob_position = value
        self.update()

    knob_position = QtCore.Property(float, _get_knob_position, _set_knob_position)

    def _animate(self):
        self._animation.stop()
        self._animation.setStartValue(self._knob_position)
        self._animation.setEndValue(1.0 if self.isChecked() else 0.0)
        self._animation.start()

    def sizeHint(self):
        text_width = 0
        if self.text():
            fm = QtGui.QFontMetrics(self.font())
            text_width = fm.horizontalAdvance(self.text()) + self._label_spacing
        return QtCore.QSize(
            self._track_width + text_width + 4,
            max(self._track_height + 4, fm.height() if self.text() else self._track_height + 4),
        )

    def minimumSizeHint(self):
        return self.sizeHint()

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Calculate track position (vertically centered)
        track_y = (self.height() - self._track_height) // 2
        track_rect = QtCore.QRectF(0, track_y, self._track_width, self._track_height)
        track_radius = self._track_height / 2

        # Interpolate track color
        ratio = self._knob_position
        r = self.track_color.red() + (self.active_color.red() - self.track_color.red()) * ratio
        g = self.track_color.green() + (self.active_color.green() - self.track_color.green()) * ratio
        b = self.track_color.blue() + (self.active_color.blue() - self.track_color.blue()) * ratio
        current_color = QtGui.QColor(int(r), int(g), int(b))

        # Draw track
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(current_color)
        painter.drawRoundedRect(track_rect, track_radius, track_radius)

        # Draw knob
        knob_travel = self._track_width - self._knob_diameter - 2 * self._knob_margin
        knob_x = self._knob_margin + self._knob_position * knob_travel
        knob_y = track_y + (self._track_height - self._knob_diameter) / 2
        painter.setBrush(self.knob_color)
        painter.drawEllipse(QtCore.QRectF(knob_x, knob_y, self._knob_diameter, self._knob_diameter))

        # Draw label text
        if self.text():
            painter.setPen(self.palette().color(QtGui.QPalette.WindowText))
            text_x = self._track_width + self._label_spacing
            text_rect = QtCore.QRectF(text_x, 0, self.width() - text_x, self.height())
            painter.drawText(text_rect, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, self.text())

        painter.end()
