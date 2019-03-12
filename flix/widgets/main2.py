#!/usr/bin/env python
import os
from pathlib import Path
import time
from datetime import timedelta
import logging
import tempfile

import reusables
from box import Box

from flix.flix import Flix
from flix.shared import QtGui, QtCore, Qt, QtWidgets, error_message, main_width
from flix.widgets.video_options import VideoOptions

logger = logging.getLogger('flix')


class Main(QtWidgets.QWidget):

    def __init__(self, parent, source=""):
        super().__init__(parent)
        self.container = parent

        self.input_video = None

        self.widgets = Box(
            input_file=None,
            preview=None,
            start_time=None,
            duration=None,
            crop=Box(top=None, bottom=None, left=None, right=None),
            scale=Box(width=None, height=None, keep_aspect_ratio=None)
        )

        self.options = Box()

        self.grid = QtWidgets.QGridLayout()

        self.init_input_file()
        self.init_video_track_select()
        self.init_output_file()
        self.init_output_type()

        self.init_start_time()
        self.init_preview_image()
        self.init_scale()
        self.init_crop()

        options = VideoOptions(self)
        self.grid.addWidget(options, 5, 0, 10, 14)

        self.setLayout(self.grid)
        self.show()

    def init_input_file(self):
        input_file_layout = QtWidgets.QHBoxLayout()
        self.widgets.input_file = QtWidgets.QLineEdit("")
        self.widgets.input_file.setReadOnly(True)
        self.widgets.input_file.setFixedWidth(400)
        open_input_file = QtWidgets.QPushButton("...")
        open_input_file.setFixedWidth(50)
        open_input_file.setDefault(True)
        input_file_layout.addWidget(QtWidgets.QLabel("Source File:"))
        input_file_layout.addWidget(self.widgets.input_file)
        input_file_layout.addWidget(open_input_file)
        input_file_layout.setSpacing(20)
        open_input_file.clicked.connect(lambda: self.open_file(self.widgets.input_file))
        self.grid.addLayout(input_file_layout, 0, 0)

    def init_video_track_select(self):
        video_box_layout = QtWidgets.QHBoxLayout()
        self.video_box = QtWidgets.QComboBox()
        self.video_box.addItems([])
        video_box_layout.addWidget(QtWidgets.QLabel("Video: "), stretch=0)
        video_box_layout.addWidget(self.video_box, stretch=1)
        video_box_layout.setSpacing(20)
        # self.video_box.currentIndexChanged.connect(self.video_track_change)
        self.grid.addLayout(video_box_layout, 1, 0)

    def init_output_file(self):
        output_file_layout = QtWidgets.QHBoxLayout()
        self.widgets.output_file = QtWidgets.QLineEdit("")
        self.widgets.output_file.setReadOnly(True)
        self.widgets.output_file.setFixedWidth(400)
        open_input_file = QtWidgets.QPushButton("...")
        open_input_file.setFixedWidth(50)
        open_input_file.setDefault(True)
        output_file_layout.addWidget(QtWidgets.QLabel("Save As:"))
        output_file_layout.addWidget(self.widgets.output_file)
        output_file_layout.addWidget(open_input_file)
        output_file_layout.setSpacing(20)
        # open_input_file.clicked.connect(lambda: self.open_file(self.widgets.output_file))
        self.grid.addLayout(output_file_layout, 2, 0)

    def init_output_type(self):
        video_box_layout = QtWidgets.QHBoxLayout()
        video_box = QtWidgets.QComboBox()
        video_box.addItems(['GIF', 'AV1 (Experimental)'])
        video_box_layout.addWidget(QtWidgets.QLabel("Output: "), stretch=0)
        video_box_layout.addWidget(video_box, stretch=1)
        video_box_layout.setSpacing(20)
        # self.video_box.currentIndexChanged.connect(self.video_track_change)
        self.grid.addLayout(video_box_layout, 3, 0)

    def init_preview_image(self):
        self.widgets.preview = QtWidgets.QLabel()
        self.widgets.preview.setBackgroundRole(QtGui.QPalette.Base)
        self.widgets.preview.setFixedSize(400, 200)
        self.widgets.preview.setStyleSheet('border: 2px solid #dddddd;')  # background-color:#f0f0f0
        self.grid.addWidget(self.widgets.preview, 0, 10, 5, 4, (Qt.AlignTop | Qt.AlignRight))

    def init_start_time(self):
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel("Start: "))
        self.widgets.start_time = QtWidgets.QLineEdit("00:00:00")
        layout.addWidget(self.widgets.start_time)

        layout.addWidget(QtWidgets.QLabel("End: "))
        self.widgets.duration = QtWidgets.QLineEdit("00:00:00")
        layout.addWidget(self.widgets.duration)

        self.grid.addLayout(layout, 4, 0)

    def init_scale(self):
        self.source_label_duration = QtWidgets.QLabel("")
        self.source_label_colorspace = QtWidgets.QLabel("")
        self.scale_area = QtWidgets.QGroupBox()
        scale_layout = QtWidgets.QVBoxLayout()

        dimensions_layout = QtWidgets.QHBoxLayout()
        dimensions_layout.addWidget(QtWidgets.QLabel("Dimensions:"))
        self.source_label_width = QtWidgets.QLabel("0")
        dimensions_layout.addWidget(self.source_label_width)
        dimensions_layout.addWidget(QtWidgets.QLabel("x"))
        self.source_label_height = QtWidgets.QLabel("0")
        dimensions_layout.addWidget(self.source_label_height)
        dimensions_layout.addStretch()


        new_scale_layout = QtWidgets.QHBoxLayout()
        new_scale_layout.addWidget(QtWidgets.QLabel("Scale:"))
        self.scale_width = QtWidgets.QLineEdit("0")
        # self.scale_width.editingFinished.connect(self.scale_update)
        new_scale_layout.addWidget(self.scale_width)
        new_scale_layout.addWidget(QtWidgets.QLabel("x"))
        self.scale_height = QtWidgets.QLineEdit("0")
        # self.scale_height.editingFinished.connect(self.scale_update)
        self.scale_height.setDisabled(True)
        new_scale_layout.addWidget(self.scale_height)

        self.keep_aspect_button = QtWidgets.QCheckBox("Keep aspect ratio")
        self.keep_aspect_button.setChecked(True)
        # self.keep_aspect_button.toggled.connect(self.scale_update)

        self.scale_warning_message = QtWidgets.QLabel("")

        # scale_layout.addLayout(dimensions_layout)
        scale_layout.addLayout(new_scale_layout)
        scale_layout.addWidget(self.keep_aspect_button)
        # scale_layout.addWidget(self.scale_warning_message)
        self.scale_area.setLayout(scale_layout)

        self.grid.addWidget(self.scale_area, 0, 5, 2, 2)

    def init_crop(self):
        # Cropping
        self.crop = QtWidgets.QGroupBox()
        # self.crop.setFixedHeight(180)
        crop_layout = QtWidgets.QVBoxLayout()

        crop_top_layout = QtWidgets.QHBoxLayout()
        crop_top_layout.addStretch()
        crop_top_layout.addWidget(QtWidgets.QLabel("Top"))
        self.crop_top = QtWidgets.QLineEdit("0")
        self.crop_top.setFixedWidth(60)
        crop_top_layout.addWidget(self.crop_top)
        crop_top_layout.addStretch()

        crop_hz_layout = QtWidgets.QHBoxLayout()
        crop_hz_layout.addStretch()
        crop_hz_layout.addWidget(QtWidgets.QLabel("Left"))
        self.crop_left = QtWidgets.QLineEdit("0")
        self.crop_left.setFixedWidth(60)
        crop_hz_layout.addWidget(self.crop_left, stretch=0)
        crop_hz_layout.addWidget(QtWidgets.QLabel("Right"))
        self.crop_right = QtWidgets.QLineEdit("0")
        self.crop_right.setFixedWidth(60)
        crop_hz_layout.addWidget(self.crop_right, stretch=0)
        crop_hz_layout.addStretch()

        crop_bottom_layout = QtWidgets.QHBoxLayout()
        crop_bottom_layout.addStretch()
        crop_bottom_layout.addWidget(QtWidgets.QLabel("Bottom"))
        self.crop_bottom = QtWidgets.QLineEdit("0")
        self.crop_bottom.setFixedWidth(60)
        crop_bottom_layout.addWidget(self.crop_bottom, stretch=0)
        crop_bottom_layout.addStretch()

        crop_layout.addLayout(crop_top_layout)
        crop_layout.addLayout(crop_hz_layout)
        crop_layout.addLayout(crop_bottom_layout)

        self.crop.setLayout(crop_layout)
        self.crop_top.editingFinished.connect(lambda: self.generate_thumbnail())
        self.crop_left.editingFinished.connect(lambda: self.generate_thumbnail())
        self.crop_right.editingFinished.connect(lambda: self.generate_thumbnail())
        self.crop_bottom.editingFinished.connect(lambda: self.generate_thumbnail())
        self.crop.toggled.connect(lambda x: self.generate_thumbnail())

        self.grid.addWidget(self.crop, 2, 5, 3, 2)


    @reusables.log_exception('flix', show_traceback=False)
    def open_file(self, update_text):
        filename = QtWidgets.QFileDialog.getOpenFileName(self, caption="Open Video",
                                                         filter="Video Files (*.mkv *.mp4 *.m4v *.mov *.avi *.divx)")
        if not filename or not filename[0]:
            return
        update_text.setText(filename[0])
        self.update_video_info()
        self.open_input_file.setDefault(False)
        self.create_button.setDefault(True)

    @reusables.log_exception('flix', show_traceback=False)
    def save_file(self):
        f = Path(self.input_file_path.text())
        save_file = os.path.join(f.parent, f"{f.stem}-flix-{int(time.time())}.mkv")
        filename = QtWidgets.QFileDialog.getSaveFileName(self, caption="Save Video As", dir=str(save_file),
                                                         filter="Video File (*.mkv)")
        return filename[0] if filename else False


    @reusables.log_exception('flix', show_traceback=False)
    def update_video_info(self):
        self.streams, self.format_info = self.flix.parse(self.input_file_path.text())
        text_audio_tracks = []
        for i, x in enumerate(self.streams['audio']):
            track_info = f"{i}: "
            tags = x.get("tags")
            if tags:
                track_info += tags.get('title')
                if 'language' in tags:
                    track_info += f' {tags.language}'
            track_info += f' - {x.codec_name}'
            if 'profile' in x:
                track_info += f' ({x.profile})'
            track_info += f' - {x.channels} channels'

            text_audio_tracks.append(track_info)
        text_audio_tracks.append("Disabled")
        text_video_tracks = [f'{i}: codec {x.codec_name}' for i, x in enumerate(self.streams['video'])]

        for i in range(self.audio_box.count()):
            self.audio_box.removeItem(0)

        for i in range(self.video_box.count()):
            self.video_box.removeItem(0)

        self.audio_box.addItems(text_audio_tracks)
        self.video_box.addItems(text_video_tracks)
        self.video_duration = float(self.format_info.get('duration', 0))

        logger.debug(f"{len(self.streams['video'])} video tracks found")
        logger.debug(f"{len(self.streams['audio'])} audio tracks found")
        if self.streams['subtitle']:
            logger.debug(f"{len(self.streams['subtitle'])} subtitle tracks found")
        if self.streams['attachment']:
            logger.debug(f"{len(self.streams['attachment'])} attachment tracks found")
        if self.streams['data']:
            logger.debug(f"{len(self.streams['data'])} data tracks found")

        if self.streams['subtitle'] and self.streams['subtitle'][0].codec_name in ('ass', 'ssa', 'mov_text'):
            logger.debug("Supported subtitles detected")
            # self.keep_subtitles.show()
            # self.keep_subtitles.setChecked(True)
        else:
            if self.streams['subtitle']:
                # hdmv_pgs_subtitle, dvd_subtitle
                logger.warning(f"Cannot keep subtitles of type: {self.streams['subtitle'][0].codec_name}")
            # self.keep_subtitles.setChecked(False)
            # self.keep_subtitles.hide()
        if self.streams['video']:
            self.update_source_labels(**self.streams['video'][0])
        self.generate_thumbnail()


