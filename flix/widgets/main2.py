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
from flix.widgets.worker import Worker

logger = logging.getLogger('flix')


class Main(QtWidgets.QWidget):
    completed = QtCore.Signal(int)
    thumbnail_complete = QtCore.Signal()
    cancelled = QtCore.Signal()

    def __init__(self, parent, source=""):
        super().__init__(parent)
        self.container = parent

        self.input_video = None
        self.streams, self.format_info = None, None

        self.widgets = Box(
            input_file=None,
            preview=None,
            start_time=None,
            duration=None,
            video_track=None,
            crop=Box(top=None, bottom=None, left=None, right=None),
            scale=Box(width=None, height=None, keep_aspect_ratio=None)
        )

        self.ffmpeg = 'ffmpeg'
        self.ffprobe = 'ffprobe'
        self.svt_av1 = 'C:\\Users\\teckc\\Downloads\\svt-av1-1.0.239\\SvtAv1EncApp.exe'
        self.thumb_file = 'test.png'

        #self.completed.connect(self.conversion_complete)
        #self.cancelled.connect(self.conversion_cancelled)
        self.thumbnail_complete.connect(self.thumbnail_generated)

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
        #self.widgets.input_file.setFixedWidth(400)
        open_input_file = QtWidgets.QPushButton("...")
        open_input_file.setFixedWidth(50)
        open_input_file.setDefault(True)
        input_file_layout.addWidget(QtWidgets.QLabel("Source File:"))
        input_file_layout.addWidget(self.widgets.input_file)
        input_file_layout.addWidget(open_input_file)
        input_file_layout.setSpacing(20)
        open_input_file.clicked.connect(lambda: self.open_file())
        self.grid.addLayout(input_file_layout, 0, 0)

    def init_video_track_select(self):
        video_box_layout = QtWidgets.QHBoxLayout()
        self.widgets.video_track = QtWidgets.QComboBox()
        self.widgets.video_track.addItems([])
        video_box_layout.addWidget(QtWidgets.QLabel("Video: "), stretch=0)
        video_box_layout.addWidget(self.widgets.video_track, stretch=1)
        video_box_layout.setSpacing(20)
        # self.video_box.currentIndexChanged.connect(self.video_track_change)
        self.grid.addLayout(video_box_layout, 1, 0)

    def init_output_file(self):
        output_file_layout = QtWidgets.QHBoxLayout()
        self.widgets.output_file = QtWidgets.QLineEdit("")
        self.widgets.output_file.setReadOnly(True)
        #self.widgets.output_file.setFixedWidth()
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
        self.widgets.preview.setFixedSize(320, 180)
        self.widgets.preview.setStyleSheet('border: 2px solid #dddddd;')  # background-color:#f0f0f0
        self.grid.addWidget(self.widgets.preview, 0, 10, 5, 4, (Qt.AlignTop | Qt.AlignRight))

    def init_start_time(self):
        self.widgets.start_time, layout = self.build_hoz_int_field("Start  ", right_stretch=False, time_field=True)
        self.widgets.duration, layout = self.build_hoz_int_field("  End  ", left_stretch=False, layout=layout, time_field=True)

        self.grid.addLayout(layout, 4, 0)

    def init_scale(self):
        scale_area = QtWidgets.QGroupBox()
        scale_layout = QtWidgets.QVBoxLayout()

        self.widgets.scale.width, new_scale_layout = self.build_hoz_int_field("Width  ", right_stretch=False)
        self.widgets.scale.height, new_scale_layout, lb, rb = self.build_hoz_int_field(
            "  Height  ", left_stretch=False, layout=new_scale_layout, return_buttons=True)
        self.widgets.scale.height.setDisabled(True)
        lb.setDisabled(True)
        rb.setDisabled(True)
        QtWidgets.QPushButton()

        self.widgets.scale.keep_aspect = QtWidgets.QCheckBox("Keep aspect ratio")
        self.widgets.scale.keep_aspect.setChecked(True)
        self.widgets.scale.keep_aspect.toggled.connect(lambda: self.toggle_disable((self.widgets.scale.height, lb, rb)))

        scale_layout.addLayout(new_scale_layout)
        scale_layout.addWidget(self.widgets.scale.keep_aspect)

        scale_area.setLayout(scale_layout)

        self.grid.addWidget(scale_area, 0, 5, 2, 2)

    @staticmethod
    def toggle_disable(widget_list):
        for widget in widget_list:
            widget.setDisabled(widget.isEnabled())

    def build_hoz_int_field(self, name, button_size=22, left_stretch=True, right_stretch=True,
                            layout=None, return_buttons=False, time_field=False):
        widget = QtWidgets.QLineEdit(self.number_to_time(0) if time_field else "0")
        widget.setFixedHeight(button_size)
        if not layout:
            layout = QtWidgets.QHBoxLayout()
            layout.setSpacing(0)
        if left_stretch:
            layout.addStretch()
        layout.addWidget(QtWidgets.QLabel(name))
        minus_button = QtWidgets.QPushButton("-")
        minus_button.setAutoRepeat(True)
        minus_button.setFixedSize(button_size, button_size)
        minus_button.clicked.connect(lambda: self.modify_int(widget, 'minus', time_field))
        plus_button = QtWidgets.QPushButton("+")
        plus_button.setAutoRepeat(True)
        plus_button.setFixedSize(button_size, button_size)
        plus_button.clicked.connect(lambda: self.modify_int(widget, 'add', time_field))
        if not time_field:
            widget.setFixedWidth(40)
        layout.addWidget(minus_button)
        layout.addWidget(widget)
        layout.addWidget(plus_button)
        if right_stretch:
            layout.addStretch()
        if return_buttons:
            return widget, layout, minus_button, plus_button
        return widget, layout

    def init_crop(self):
        crop_box = QtWidgets.QGroupBox()
        crop_layout = QtWidgets.QVBoxLayout()
        self.widgets.crop.top, crop_top_layout = self.build_hoz_int_field("Top  ")
        self.widgets.crop.left, crop_hz_layout = self.build_hoz_int_field("Left  ",
                                                                          right_stretch=False)
        self.widgets.crop.right, crop_hz_layout = self.build_hoz_int_field("    Right  ",
                                                                           left_stretch=False,
                                                                           layout=crop_hz_layout)
        self.widgets.crop.bottom, crop_bottom_layout = self.build_hoz_int_field("Bottom  ")

        crop_layout.addLayout(crop_top_layout)
        crop_layout.addLayout(crop_hz_layout)
        crop_layout.addLayout(crop_bottom_layout)

        crop_box.setLayout(crop_layout)
        # self.widgets.crop.top.editingFinished.connect(lambda: self.generate_thumbnail())
        # self.widgets.crop.left.editingFinished.connect(lambda: self.generate_thumbnail())
        # self.widgets.crop.right.editingFinished.connect(lambda: self.generate_thumbnail())
        # self.widgets.crop.bottom.editingFinished.connect(lambda: self.generate_thumbnail())
        # self.crop.toggled.connect(lambda x: self.generate_thumbnail())

        self.grid.addWidget(crop_box, 2, 5, 3, 2)

    def modify_int(self, widget, method="add", time_field=False):
        if time_field:
            value = self.time_to_number(widget.text())
            if value is None:
                return
        else:
            try:
                value = int(widget.text())
            except ValueError:
                logger.warning('...dummy')
                return
        modifier = (1 if method == 'add' else -1)
        new_value = value + modifier
        if time_field and new_value < 0:
            return
        widget.setText(str(new_value) if not time_field else self.number_to_time(new_value))

    @reusables.log_exception('flix', show_traceback=False)
    def open_file(self):
        filename = QtWidgets.QFileDialog.getOpenFileName(self, caption="Open Video",
                                                         filter="Video Files (*.mkv *.mp4 *.m4v *.mov *.avi *.divx)")
        if not filename or not filename[0]:
            return
        self.input_video = filename[0]
        self.widgets.input_file.setText(self.input_video)
        self.update_video_info()
        self.generate_thumbnail()

    @reusables.log_exception('flix', show_traceback=False)
    def save_file(self):
        f = Path(self.input_file_path.text())
        save_file = os.path.join(f.parent, f"{f.stem}-flix-{int(time.time())}.mkv")
        filename = QtWidgets.QFileDialog.getSaveFileName(self, caption="Save Video As", dir=str(save_file),
                                                         filter="Video File (*.mkv)")
        return filename[0] if filename else False

    @property
    def flix(self):
        return Flix(ffmpeg=self.ffmpeg, ffprobe=self.ffprobe, svt_av1=self.svt_av1)


    @reusables.log_exception('flix', show_traceback=False)
    def update_video_info(self):
        self.streams, self.format_info = self.flix.parse(self.input_video)
        logger.debug(self.streams)
        logger.debug(self.format_info)
        text_audio_tracks = []
        for i, x in enumerate(self.streams.audio):
            track_info = f"{i}: "
            tags = x.get("tags")
            if tags:
                track_info += tags.get('title', '')
                if 'language' in tags:
                    track_info += f' {tags.language}'
            track_info += f' - {x.codec_name}'
            if 'profile' in x:
                track_info += f' ({x.profile})'
            track_info += f' - {x.channels} channels'

            text_audio_tracks.append(track_info)
        text_video_tracks = [f'{i}: codec {x.codec_name}' for i, x in enumerate(self.streams.video)]

        for i in range(self.widgets.video_track.count()):
            self.widgets.video_track.removeItem(0)

        self.widgets.scale.width.setText(str(self.streams.video[0].width))
        self.widgets.scale.height.setText(str(self.streams.video[0].height))
        self.widgets.video_track.addItems(text_video_tracks)

        self.widgets.video_track.setDisabled(bool(len(self.streams.video) == 1))

        # self.video_duration = float(self.format_info.get('duration', 0))
        video_duration = float(self.format_info.get('duration', 0))

        logger.debug(f"{len(self.streams['video'])} video tracks found")
        logger.debug(f"{len(self.streams['audio'])} audio tracks found")
        if self.streams['subtitle']:
            logger.debug(f"{len(self.streams['subtitle'])} subtitle tracks found")
        if self.streams['attachment']:
            logger.debug(f"{len(self.streams['attachment'])} attachment tracks found")
        if self.streams['data']:
            logger.debug(f"{len(self.streams['data'])} data tracks found")

        self.widgets.duration.setText(self.number_to_time(video_duration))

        # if self.streams['subtitle'] and self.streams['subtitle'][0].codec_name in ('ass', 'ssa', 'mov_text'):
        #     logger.debug("Supported subtitles detected")
        #     # self.keep_subtitles.show()
        #     # self.keep_subtitles.setChecked(True)
        # else:
        #     if self.streams['subtitle']:
        #         # hdmv_pgs_subtitle, dvd_subtitle
        #         logger.warning(f"Cannot keep subtitles of type: {self.streams['subtitle'][0].codec_name}")
        #     # self.keep_subtitles.setChecked(False)
        #     # self.keep_subtitles.hide()
        # if self.streams['video']:
        #     self.update_source_labels(**self.streams['video'][0])
        # self.generate_thumbnail()

    @staticmethod
    def number_to_time(number):
        return str(timedelta(seconds=float(number)))[:10]

    @staticmethod
    def time_to_number(string_time):
        try:
            return float(string_time)
        except ValueError:
            pass
        base, *extra = string_time.split(".")
        micro = 0
        if extra and len(extra) == 1:
            try:
                micro = int(extra[0])
            except ValueError:
                logger.info('bad micro value')
                return
        total = float(f'.{micro}')
        for i, v in enumerate(reversed(base.split(":"))):
            try:
                v = int(v)
            except ValueError:
                logger.info(f'Not a valid int: {v}')
            total += v * (60 ** i)
        return total

    @reusables.log_exception('flix', show_traceback=False)
    def generate_thumbnail(self):
        if not self.input_video:
            return
        # try:
        #     crop = self.build_crop()
        # except (ValueError, AssertionError):
        #     logger.warning("Invalid crop, thumbnail will not reflect it")
        #     crop = None
        # if self.timing.isChecked():
        #     start_time = self._get_start_time()
        # elif self.video_duration > 5:

        start_time = 5
        thumb_command = self.flix.generate_thumbnail_command(
            source=self.input_video,
            output=self.thumb_file,
            video_track=self.streams['video'][self.widgets.video_track.currentIndex()]['index'],
            start_time=start_time,
            # disable_hdr=self.convert_hdr_check.isChecked(),
        )
        logger.info("Generating thumbnail")
        worker = Worker(self, thumb_command, cmd_type="thumb")
        worker.start()

    @reusables.log_exception('flix', show_traceback=False)
    def thumbnail_generated(self):
        print('called')
        pixmap = QtGui.QPixmap(str(self.thumb_file))
        pixmap = pixmap.scaled(320, 180, QtCore.Qt.KeepAspectRatio)
        self.widgets.preview.setPixmap(pixmap)
