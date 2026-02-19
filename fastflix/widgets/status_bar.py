# -*- coding: utf-8 -*-
import logging
from dataclasses import dataclass, field
from typing import Callable

from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.resources import main_icon
from fastflix.ui_scale import scaler

logger = logging.getLogger("fastflix")


@dataclass
class Task:
    name: str
    command: Callable
    kwargs: dict = field(default_factory=dict)


# State constants
STATE_IDLE = "idle"
STATE_ENCODING = "encoding"
STATE_PROCESSING = "processing"
STATE_ERROR = "error"
STATE_COMPLETE = "complete"

STATE_COLORS = {
    STATE_IDLE: QtGui.QColor("#888888"),
    STATE_ENCODING: QtGui.QColor("#3daee9"),
    STATE_PROCESSING: QtGui.QColor("#f0a030"),
    STATE_ERROR: QtGui.QColor("#da4453"),
    STATE_COMPLETE: QtGui.QColor("#27ae60"),
}


class StatusBarWidget(QtWidgets.QFrame):
    progress_signal = QtCore.Signal(int)
    stop_signal = QtCore.Signal()

    def __init__(self, app: FastFlixApp, parent=None):
        super().__init__(parent)
        self.app = app
        self.cancelled = False
        self._state = STATE_IDLE
        self._pulse_bright = True

        self.setObjectName("StatusBarWidget")
        self.setFixedHeight(scaler.scale(28))

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(8)

        # Icon label
        self.icon_label = QtWidgets.QLabel()
        self.icon_label.setFixedSize(scaler.scale(20), scaler.scale(20))
        self.icon_label.setStyleSheet("background: transparent;")
        self._base_icon = self._load_base_icon()
        self._update_icon(STATE_COLORS[STATE_IDLE])
        layout.addWidget(self.icon_label)

        # Status message
        self.status_label = QtWidgets.QLabel(t("Ready"))
        self.status_label.setMinimumWidth(100)
        layout.addWidget(self.status_label, stretch=1)

        # Progress bar — hidden by default, shown only when actively used
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(scaler.scale(16))
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar, stretch=1)

        self.setLayout(layout)

        # Pulse animation timer
        self._pulse_timer = QtCore.QTimer(self)
        self._pulse_timer.setInterval(500)
        self._pulse_timer.timeout.connect(self._pulse_tick)

        self._apply_theme_style()

    def _load_base_icon(self) -> QtGui.QPixmap:
        pixmap = QtGui.QPixmap(main_icon)
        if pixmap.isNull():
            pixmap = QtGui.QPixmap(20, 20)
            pixmap.fill(QtCore.Qt.transparent)
        return pixmap.scaled(
            scaler.scale(20),
            scaler.scale(20),
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )

    def _create_tinted_icon(self, color: QtGui.QColor) -> QtGui.QPixmap:
        tinted = QtGui.QPixmap(self._base_icon.size())
        tinted.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(tinted)
        painter.drawPixmap(0, 0, self._base_icon)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), color)
        painter.end()
        return tinted

    def _update_icon(self, color: QtGui.QColor, opacity: float = 1.0):
        tinted = self._create_tinted_icon(color)
        if opacity < 1.0:
            faded = QtGui.QPixmap(tinted.size())
            faded.fill(QtCore.Qt.transparent)
            painter = QtGui.QPainter(faded)
            painter.setOpacity(opacity)
            painter.drawPixmap(0, 0, tinted)
            painter.end()
            tinted = faded
        self.icon_label.setPixmap(tinted)

    def _pulse_tick(self):
        self._pulse_bright = not self._pulse_bright
        opacity = 1.0 if self._pulse_bright else 0.4
        color = STATE_COLORS.get(self._state, STATE_COLORS[STATE_IDLE])
        self._update_icon(color, opacity)

    def _show_progress(self):
        if not self.progress_bar.isVisible():
            self.progress_bar.show()

    def _hide_progress(self):
        if self.progress_bar.isVisible():
            self.progress_bar.setValue(0)
            self.progress_bar.hide()

    def set_state(self, state: str, message: str = ""):
        self._state = state
        color = STATE_COLORS.get(state, STATE_COLORS[STATE_IDLE])

        if message:
            self.status_label.setText(message)
        elif state == STATE_IDLE:
            self.status_label.setText(t("Ready"))

        if state == STATE_IDLE:
            self._hide_progress()

        # Start/stop pulsing based on state
        if state in (STATE_ENCODING, STATE_PROCESSING):
            self._pulse_bright = True
            self._update_icon(color, 1.0)
            if not self._pulse_timer.isActive():
                self._pulse_timer.start()
        else:
            self._pulse_timer.stop()
            self._pulse_bright = True
            self._update_icon(color, 1.0)

    def set_progress(self, percent: int):
        percent = max(0, min(100, percent))
        if percent > 0:
            self._show_progress()
            self.progress_bar.setValue(percent)
        else:
            self._hide_progress()

    def run_tasks(
        self, tasks: list, signal_task: bool = False, can_cancel: bool = False, persist_complete: bool = False
    ):
        """Blocking task runner that replaces ProgressBar popup for post-startup tasks.

        Runs tasks synchronously while updating the status bar, calling processEvents()
        to keep the UI responsive.

        If persist_complete is True and tasks succeed without error or cancellation,
        the status bar stays green with a completion message instead of restoring
        the previous state.
        """
        if not tasks:
            logger.error("Status bar run_tasks called without any tasks")
            return

        self.cancelled = False
        errored = False
        previous_state = self._state
        previous_message = self.status_label.text()
        previous_progress = self.progress_bar.value()
        previous_visible = self.progress_bar.isVisible()

        self.set_state(STATE_PROCESSING, tasks[0].name)
        self.progress_bar.setValue(0)
        self._show_progress()
        self.app.processEvents()

        try:
            if signal_task:
                self.progress_signal.connect(self._update_task_progress)
                tasks[0].kwargs["signal"] = self.progress_signal
                tasks[0].kwargs["stop_signal"] = self.stop_signal
                try:
                    tasks[0].command(config=self.app.fastflix.config, app=self.app, **tasks[0].kwargs)
                finally:
                    try:
                        self.progress_signal.disconnect(self._update_task_progress)
                    except RuntimeError:
                        pass
            else:
                ratio = 100 / len(tasks)
                for i, task in enumerate(tasks, start=1):
                    logger.info(f"Running task {task.name}")
                    self.set_state(STATE_PROCESSING, task.name)
                    self.app.processEvents()
                    if self.app.fastflix.shutting_down or self.cancelled:
                        break
                    try:
                        task.command(config=self.app.fastflix.config, app=self.app, **task.kwargs)
                    except Exception:
                        logger.exception(f"Could not run task {task.name}")
                        raise
                    self.set_progress(int(i * ratio))
                    self.app.processEvents()
        except Exception:
            errored = True
            raise
        finally:
            if persist_complete and not self.cancelled and not errored:
                self.set_state(STATE_COMPLETE, f"{tasks[-1].name} - {t('Complete')}")
                self._hide_progress()
            else:
                self.set_state(previous_state, previous_message)
                if previous_visible and previous_progress > 0:
                    self.set_progress(previous_progress)
                else:
                    self._hide_progress()

    def _update_task_progress(self, value: int):
        self.set_progress(value)
        self.app.processEvents()
        if self.app.fastflix.shutting_down:
            self.stop_signal.emit()

    def cancel(self):
        self.stop_signal.emit()
        self.cancelled = True

    def _apply_theme_style(self):
        theme = self.app.fastflix.config.theme
        if theme == "onyx":
            self.setStyleSheet("#StatusBarWidget {  background-color: #3a4149;  border-top: 1px solid #567781;}")
            self.status_label.setStyleSheet("color: #b5b5b5; background: transparent;")
            self.progress_bar.setStyleSheet(
                "QProgressBar {"
                "  background-color: #4a555e;"
                "  border: 1px solid #567781;"
                "  border-radius: 3px;"
                "  color: white;"
                "  text-align: center;"
                "}"
                "QProgressBar::chunk {"
                "  background-color: #3daee9;"
                "  border-radius: 2px;"
                "}"
            )
        elif theme == "dark":
            self.setStyleSheet("#StatusBarWidget {  background-color: #2d2d2d;  border-top: 1px solid #555555;}")
            self.status_label.setStyleSheet("color: #cccccc; background: transparent;")
            self.progress_bar.setStyleSheet(
                "QProgressBar {"
                "  background-color: #3d3d3d;"
                "  border: 1px solid #555555;"
                "  border-radius: 3px;"
                "  color: white;"
                "  text-align: center;"
                "}"
                "QProgressBar::chunk {"
                "  background-color: #3daee9;"
                "  border-radius: 2px;"
                "}"
            )
        else:
            self.setStyleSheet("#StatusBarWidget {  background-color: #f0f0f0;  border-top: 1px solid #cccccc;}")
            self.status_label.setStyleSheet("color: #333333; background: transparent;")

    def update_theme(self):
        self._apply_theme_style()

    def cleanup(self):
        self._pulse_timer.stop()
