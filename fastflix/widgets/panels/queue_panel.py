#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy
from dataclasses import asdict

from box import Box
from iso639 import Lang
from qtpy import QtCore, QtGui, QtWidgets

from fastflix.language import t
from fastflix.shared import link
from fastflix.models.encode import SubtitleTrack
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.models.video import Video
from fastflix.resources import black_x_icon, down_arrow_icon, up_arrow_icon, play_icon, folder_icon, edit_box_icon
from fastflix.shared import FastFlixInternalException, error_message, main_width, open_folder
from fastflix.widgets.panels.abstract_list import FlixList


class EncodeItem(QtWidgets.QTabWidget):
    def __init__(self, parent, video: Video, index, first=False, currently_encoding=False):
        self.loading = True
        super().__init__(parent)
        self.parent = parent
        self.index = index
        self.first = first
        self.last = False
        self.video = video
        self.currently_encoding = currently_encoding

        self.widgets = Box(
            up_button=QtWidgets.QPushButton(QtGui.QIcon(up_arrow_icon), ""),
            down_button=QtWidgets.QPushButton(QtGui.QIcon(down_arrow_icon), ""),
            cancel_button=QtWidgets.QPushButton(QtGui.QIcon(black_x_icon), ""),
            reload_buttom=QtWidgets.QPushButton(QtGui.QIcon(edit_box_icon), ""),
        )

        for widget in self.widgets.values():
            widget.setStyleSheet("""QPushButton, QPushButton:hover{border-width: 0;}""")
            if self.currently_encoding:
                widget.setDisabled(True)

        self.setFixedHeight(50)

        title = QtWidgets.QLabel(f"{video.source.name} -> {video.video_settings.output_path.name}")

        settings = Box(copy.deepcopy(asdict(video.video_settings)))
        settings.output_path = str(settings.output_path)
        del settings.conversion_commands

        title.setToolTip(settings.to_yaml())

        open_button = QtWidgets.QPushButton(QtGui.QIcon(folder_icon), t("Open Directory"))
        open_button.setLayoutDirection(QtCore.Qt.RightToLeft)
        open_button.setIconSize(QtCore.QSize(14, 14))
        open_button.clicked.connect(lambda: open_folder(video.video_settings.output_path.parent))

        view_button = QtWidgets.QPushButton(QtGui.QIcon(play_icon), t("Watch"))
        view_button.setLayoutDirection(QtCore.Qt.RightToLeft)
        view_button.setIconSize(QtCore.QSize(14, 14))
        view_button.clicked.connect(
            lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(video.video_settings.output_path)))
        )

        open_button.setStyleSheet(
            """
        QPushButton { border: 0; }
        QPushButton:hover { border: 0; text-decoration: underline; }
        """
        )
        view_button.setStyleSheet(
            """
        QPushButton { border: 0; }
        QPushButton:hover { border: 0; text-decoration: underline; }
        """
        )

        status = t("Ready to encode")
        if video.status.error:
            status = t("Encoding errored")
        elif video.status.complete:
            status = f"{t('Encoding complete')}"
        elif video.status.running:
            status = (
                f"{t('Encoding command')} {video.status.current_command} {t('of')} "
                f"{len(video.video_settings.conversion_commands)}"
            )
        elif video.status.cancelled:
            status = t("Cancelled - Ready to try again")

        if not self.currently_encoding:
            self.widgets.cancel_button.clicked.connect(lambda: self.parent.remove_item(self.video))
            self.widgets.reload_buttom.clicked.connect(lambda: self.parent.reload_from_queue(self.video))
        self.widgets.cancel_button.setFixedWidth(25)
        self.widgets.reload_buttom.setFixedWidth(25)

        grid = QtWidgets.QGridLayout()
        grid.addLayout(self.init_move_buttons(), 0, 0)
        # grid.addWidget(self.widgets.track_number, 0, 1)
        grid.addWidget(title, 0, 1, 1, 3)
        grid.addWidget(QtWidgets.QLabel(f"{video.video_settings.video_encoder_settings.name}"), 0, 4)
        grid.addWidget(QtWidgets.QLabel(f"{t('Audio Tracks')}: {len(video.video_settings.audio_tracks)}"), 0, 5)
        grid.addWidget(QtWidgets.QLabel(f"{t('Subtitles')}: {len(video.video_settings.subtitle_tracks)}"), 0, 6)
        grid.addWidget(QtWidgets.QLabel(status), 0, 7)
        if video.status.complete:
            grid.addWidget(view_button, 0, 8)
            grid.addWidget(open_button, 0, 9)

        right_buttons = QtWidgets.QHBoxLayout()
        right_buttons.addWidget(self.widgets.reload_buttom)
        right_buttons.addWidget(self.widgets.cancel_button)

        grid.addLayout(right_buttons, 0, 10, alignment=QtCore.Qt.AlignRight)
        # grid.addLayout(disposition_layout, 0, 4)
        # grid.addWidget(self.widgets.burn_in, 0, 5)
        # grid.addLayout(self.init_language(), 0, 6)
        # # grid.addWidget(self.init_extract_button(), 0, 6)
        # grid.addWidget(self.widgets.enable_check, 0, 8)

        self.setLayout(grid)
        self.loading = False
        self.updating_burn = False

    def init_move_buttons(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(0)
        self.widgets.up_button.setDisabled(self.first)
        self.widgets.up_button.setFixedWidth(20)
        self.widgets.up_button.clicked.connect(lambda: self.parent.move_up(self))
        self.widgets.down_button.setDisabled(self.last)
        self.widgets.down_button.setFixedWidth(20)
        self.widgets.down_button.clicked.connect(lambda: self.parent.move_down(self))
        layout.addWidget(self.widgets.up_button)
        layout.addWidget(self.widgets.down_button)
        return layout

    def set_first(self, first=True):
        self.first = first
        self.widgets.up_button.setDisabled(self.first)

    def set_last(self, last=True):
        self.last = last
        self.widgets.down_button.setDisabled(self.last)

    def set_outdex(self, outdex):
        pass

    @property
    def enabled(self):
        return True

    def update_enable(self):
        pass

    def page_update(self):
        if not self.loading:
            return self.parent.main.page_update(build_thumbnail=False)


class EncodingQueue(FlixList):
    def __init__(self, parent, app: FastFlixApp):
        self.main = parent.main
        self.app = app

        top_layout = QtWidgets.QHBoxLayout()

        top_layout.addWidget(QtWidgets.QLabel(t("Queue")))
        top_layout.addStretch(1)

        pause_queue = QtWidgets.QPushButton(
            self.app.style().standardIcon(QtWidgets.QStyle.SP_MediaPause), "Pause Queue"
        )
        # pause_queue.setFixedHeight(40)
        pause_queue.setFixedWidth(120)
        top_layout.addWidget(pause_queue, QtCore.Qt.AlignRight)

        pause_encode = QtWidgets.QPushButton(
            self.app.style().standardIcon(QtWidgets.QStyle.SP_MediaPause), "Pause Encode"
        )
        # pause_encode.setFixedHeight(40)
        pause_encode.setFixedWidth(120)
        top_layout.addWidget(pause_encode, QtCore.Qt.AlignRight)

        super().__init__(app, parent, t("Queue"), "queue", top_row_layout=top_layout)

    def reorder(self, update=True):
        super().reorder(update=update)
        self.app.fastflix.queue = [track.video for track in self.tracks]

    def new_source(self, currently_encoding=False):
        self.tracks = []
        for i, video in enumerate(self.app.fastflix.queue, start=1):
            self.tracks.append(EncodeItem(self, video, i, currently_encoding=currently_encoding))
        super()._new_source(self.tracks)
        self.app.processEvents()

    def remove_item(self, video):
        self.app.fastflix.queue.remove(video)
        self.new_source()

    def reload_from_queue(self, video):
        self.main.reload_video_from_queue(video)
        self.app.fastflix.queue.remove(video)
        self.new_source()
