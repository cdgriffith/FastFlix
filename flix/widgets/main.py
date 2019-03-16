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
from flix.widgets.command_runner import Worker as CW
from flix.widgets.av1 import AV1
from flix.widgets.x265 import X265
from flix.widgets.gif import GIF

from flix.builders import (gif as gif_builder)

logger = logging.getLogger('flix')


class Main(QtWidgets.QWidget):
    completed = QtCore.Signal(int)
    thumbnail_complete = QtCore.Signal()
    cancelled = QtCore.Signal()

    def __init__(self, parent, source=""):
        super().__init__(parent)
        self.container = parent

        self.command_runner = None

        self.input_video = None
        self.streams, self.format_info = None, None
        # self.x265 = X265(parent=self, source=source)
        # self.av1 = AV1(parent=self, source=source)
        # self.gif = GIF(parent=self, source=source)

        self.builders = Box(
            gif=gif_builder
        )

        self.widgets = Box(
            input_file=None,
            preview=None,
            start_time=None,
            duration=None,
            video_track=None,
            convert_to=None,
            crop=Box(top=None, bottom=None, left=None, right=None),
            scale=Box(width=None, height=None, keep_aspect_ratio=None)
        )

        self.ffmpeg = 'ffmpeg'
        self.ffprobe = 'ffprobe'
        self.svt_av1 = 'C:\\Users\\teckc\\Downloads\\svt-av1-1.0.239\\SvtAv1EncApp.exe'
        self.thumb_file = 'test.png'
        self.pallet_file = 'pallet.png'

        self.video_options = VideoOptions(self)

        #self.completed.connect(self.conversion_complete)
        #self.cancelled.connect(self.conversion_cancelled)
        self.thumbnail_complete.connect(self.thumbnail_generated)
        self.encoding_worker = None

        self.video_width = 0
        self.video_height = 0

        self.options = Box()

        self.grid = QtWidgets.QGridLayout()

        self.init_video_area()
        self.init_scale_and_crop()
        self.init_preview_image()

        self.grid.addWidget(self.video_options, 5, 0, 10, 15)
        self.grid.setSpacing(5)

        self.setLayout(self.grid)
        self.show()

    def init_video_area(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(self.init_button_menu())
        layout.addLayout(self.init_video_track_select())
        layout.addLayout(self.init_output_type())
        layout.addLayout(self.init_start_time())
        layout.addStretch()
        self.grid.addLayout(layout, 0, 0, 5, 6)

    def init_scale_and_crop(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.init_scale())
        layout.addWidget(self.init_crop())
        layout.addStretch()
        self.grid.addLayout(layout, 0, 6, 5, 4)

    def init_button_menu(self):
        layout = QtWidgets.QHBoxLayout()
        open_input_file = QtWidgets.QPushButton("Source")
        open_input_file.setFixedSize(100, 50)
        open_input_file.setDefault(True)
        open_input_file.clicked.connect(lambda: self.open_file())
        open_input_file.setStyleSheet('background: blue')
        convert = QtWidgets.QPushButton("Convert")
        convert.setFixedSize(100, 50)
        convert.setStyleSheet('background: green')
        convert.clicked.connect(lambda: self.create_video())
        layout.addWidget(open_input_file)
        layout.addWidget(convert)
        layout.addStretch()
        return layout

    def init_input_file(self):
        layout = QtWidgets.QHBoxLayout()
        self.widgets.input_file = QtWidgets.QLineEdit("")
        self.widgets.input_file.setReadOnly(True)
        open_input_file = QtWidgets.QPushButton("...")
        open_input_file.setFixedWidth(50)
        open_input_file.setMaximumHeight(22)
        open_input_file.setDefault(True)
        layout.addWidget(QtWidgets.QLabel("Source File:"))
        layout.addWidget(self.widgets.input_file)
        layout.addWidget(open_input_file)
        layout.setSpacing(10)
        open_input_file.clicked.connect(lambda: self.open_file())
        return layout

    def init_video_track_select(self):
        layout = QtWidgets.QHBoxLayout()
        self.widgets.video_track = QtWidgets.QComboBox()
        self.widgets.video_track.addItems([])
        layout.addWidget(QtWidgets.QLabel("Video: "), stretch=0)
        layout.addWidget(self.widgets.video_track, stretch=1)
        layout.setSpacing(10)
        return layout

    # def init_output_file(self):
    #     layout = QtWidgets.QHBoxLayout()
    #     self.widgets.output_file = QtWidgets.QLineEdit("")
    #     self.widgets.output_file.setReadOnly(True)
    #     open_file = QtWidgets.QPushButton("...")
    #     open_file.setFixedWidth(50)
    #     open_file.setDefault(False)
    #     layout.addWidget(QtWidgets.QLabel("Save As:"))
    #     layout.addWidget(self.widgets.output_file)
    #     layout.addWidget(open_file)
    #     layout.setSpacing(10)
    #     open_file.clicked.connect(lambda: self.save_file())
    #     return layout

    def init_output_type(self):
        layout = QtWidgets.QHBoxLayout()
        self.widgets.convert_to = QtWidgets.QComboBox()
        self.widgets.convert_to.addItems(['GIF', 'AV1 (Experimental)'])
        layout.addWidget(QtWidgets.QLabel("Output: "), stretch=0)
        layout.addWidget(self.widgets.convert_to, stretch=1)
        layout.setSpacing(10)
        self.widgets.convert_to.currentIndexChanged.connect(self.video_options.change_conversion)

        return layout

    def init_start_time(self):
        self.widgets.start_time, layout = self.build_hoz_int_field(
            "Start  ", right_stretch=False, time_field=True)
        self.widgets.duration, layout = self.build_hoz_int_field(
            "  End  ", left_stretch=False, layout=layout, time_field=True)
        return layout

    def init_scale(self):
        scale_area = QtWidgets.QGroupBox()
        scale_area.setStyleSheet("QGroupBox{padding-top:15px; margin-top:-18px}")
        scale_layout = QtWidgets.QVBoxLayout()

        self.widgets.scale.width, new_scale_layout = self.build_hoz_int_field("Width  ", right_stretch=False)
        self.widgets.scale.height, new_scale_layout, lb, rb = self.build_hoz_int_field(
            "  Height  ", left_stretch=False, layout=new_scale_layout, return_buttons=True)
        self.widgets.scale.height.setDisabled(True)
        lb.setDisabled(True)
        rb.setDisabled(True)
        QtWidgets.QPushButton()

        self.widgets.scale.width.textChanged.connect(self.scale_update)
        #self.widgets.scale.height.textChanged.connect(self.scale_update)

        bottom_row = QtWidgets.QHBoxLayout()
        self.widgets.scale.keep_aspect = QtWidgets.QCheckBox("Keep aspect ratio")
        self.widgets.scale.keep_aspect.setMaximumHeight(40)
        self.widgets.scale.keep_aspect.setChecked(True)
        self.widgets.scale.keep_aspect.toggled.connect(lambda: self.toggle_disable((self.widgets.scale.height, lb, rb)))

        label = QtWidgets.QLabel('Scale', alignment=(Qt.AlignBottom | Qt.AlignRight))
        label.setStyleSheet("QLabel{color:#777}")
        label.setMaximumHeight(40)
        bottom_row.addWidget(self.widgets.scale.keep_aspect, alignment=Qt.AlignCenter)

        scale_layout.addLayout(new_scale_layout)
        #scale_layout.addWidget(self.widgets.scale.keep_aspect)
        bottom_row.addWidget(label)
        scale_layout.addLayout(bottom_row)

        scale_area.setLayout(scale_layout)

        return scale_area

    def init_crop(self):
        crop_box = QtWidgets.QGroupBox()
        crop_box.setStyleSheet("QGroupBox{padding-top:15px; margin-top:-18px}")
        crop_layout = QtWidgets.QVBoxLayout()
        self.widgets.crop.top, crop_top_layout = self.build_hoz_int_field("Top  ")
        self.widgets.crop.left, crop_hz_layout = self.build_hoz_int_field("Left  ",
                                                                          right_stretch=False)
        self.widgets.crop.right, crop_hz_layout = self.build_hoz_int_field("    Right  ",
                                                                           left_stretch=False,
                                                                           layout=crop_hz_layout)
        self.widgets.crop.bottom, crop_bottom_layout = self.build_hoz_int_field("Bottom  ", right_stretch=True)

        label = QtWidgets.QLabel("Crop", alignment=(Qt.AlignBottom | Qt.AlignRight))
        label.setStyleSheet("QLabel{color:#777}")
        label.setMaximumHeight(40)
        crop_bottom_layout.addWidget(label)

        crop_layout.addLayout(crop_top_layout)
        crop_layout.addLayout(crop_hz_layout)
        crop_layout.addLayout(crop_bottom_layout)

        crop_box.setLayout(crop_layout)

        return crop_box

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

    def init_preview_image(self):
        self.widgets.preview = QtWidgets.QLabel()
        self.widgets.preview.setBackgroundRole(QtGui.QPalette.Base)
        self.widgets.preview.setFixedSize(320, 180)
        self.widgets.preview.setStyleSheet('border: 2px solid #dddddd;')  # background-color:#f0f0f0

        buttons = self.init_preview_buttons()

        self.grid.addWidget(self.widgets.preview, 0, 10, 5, 4, (Qt.AlignTop | Qt.AlignRight))
        self.grid.addLayout(buttons, 0, 14, 5, 1)

    def init_preview_buttons(self):
        layout = QtWidgets.QVBoxLayout()
        refresh = QtWidgets.QPushButton("R")
        refresh.setFixedWidth(20)
        preview = QtWidgets.QPushButton("P")
        preview.setFixedWidth(20)
        one = QtWidgets.QPushButton("1")
        one.setFixedWidth(20)
        two = QtWidgets.QPushButton("2")
        two.setFixedWidth(20)

        refresh.clicked.connect(lambda: self.generate_thumbnail())

        layout.addWidget(refresh)
        layout.addWidget(preview)
        layout.addWidget(one)
        layout.addWidget(two)
        layout.addStretch()
        return layout

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
        self.build_commands()

    @reusables.log_exception('flix', show_traceback=False)
    def open_file(self):
        filename = QtWidgets.QFileDialog.getOpenFileName(self, caption="Open Video",
                                                         filter="Video Files (*.mkv *.mp4 *.m4v *.mov *.avi *.divx)")
        if not filename or not filename[0]:
            return
        self.input_video = filename[0]
        self.update_video_info()
        self.generate_thumbnail()

    @reusables.log_exception('flix', show_traceback=False)
    def save_file(self, extension="mkv"):
        f = Path(self.input_video)
        save_file = os.path.join(f.parent, f"{f.stem}-flix-{int(time.time())}.{extension}")
        filename = QtWidgets.QFileDialog.getSaveFileName(self, caption="Save Video As", dir=str(save_file),
                                                         filter=f"Save File (*.{extension}")
        return filename[0] if filename else False

    @property
    def flix(self):
        return Flix(ffmpeg=self.ffmpeg, ffprobe=self.ffprobe, svt_av1=self.svt_av1)

    def build_crop(self):
        top = int(self.widgets.crop.top.text())
        left = int(self.widgets.crop.left.text())
        right = int(self.widgets.crop.right.text())
        bottom = int(self.widgets.crop.bottom.text())
        width = self.video_width - right - left
        height = self.video_height - bottom - top
        if (top+left+right+bottom) == 0:
            return None
        try:
            assert top >= 0, "Top must be positive number"
            assert left >= 0, "Left must be positive number"
            assert width > 0, "Total video width must be greater than 0"
            assert height > 0, "Total video height must be greater than 0"
            assert width <= self.video_width, "Width must be smaller than video width"
            assert height <= self.video_height, "Height must be smaller than video height"
        except AssertionError as err:
            error_message(f'Invalid Crop: {err}', parent=self)
            return
        return f"{width}:{height}:{left}:{top}"

    @reusables.log_exception('flix', show_traceback=False)
    def scale_update(self, *args):
        keep_aspect = self.widgets.scale.keep_aspect.isChecked()
        if not keep_aspect:
            return
        self.widgets.scale.height.setDisabled(keep_aspect)
        height = self.video_height
        width = self.video_width
        if self.build_crop():
            width, height, *_ = (int(x) for x in self.build_crop().split(":"))

        if keep_aspect and (not height or not width):
            return logger.info("Invalid source dimensions")

        try:
            scale_width = int(self.widgets.scale.width.text())
            assert scale_width > 0
        except (ValueError, AssertionError):
            logger.info("Invalid width")
            return
            #return self.scale_warning_message.setText("Invalid main_width")

        # if scale_width % 8:
        #     return self.scale_warning_message.setText("Width must be divisible by 8")

        if keep_aspect:
            ratio = scale_width / width
            scale_height = ratio * height
            self.widgets.scale.height.setText(str(int(scale_height)))
            return

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

        self.video_width = self.streams.video[0].width
        self.video_height = self.streams.video[0].height

        self.widgets.scale.width.setText(str(self.video_width))
        self.widgets.scale.height.setText(str(self.video_height))
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

    @property
    def start_time(self):
        return self.time_to_number(self.widgets.start_time.text())

    @property
    def duration(self):
        return self.time_to_number(self.widgets.duration.text())

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
        try:
            crop = self.build_crop()
        except (ValueError, AssertionError) as err:
            logger.warning(f"Invalid crop, thumbnail will not reflect it: {err}")
            crop = None
        start_time = 0
        if self.start_time:
            start_time = self.start_time
        elif self.duration > 5:
            start_time = 5
        thumb_command = self.flix.generate_thumbnail_command(
            source=self.input_video,
            output=self.thumb_file,
            video_track=self.streams['video'][self.widgets.video_track.currentIndex()]['index'],
            start_time=start_time,
            crop=crop
            # disable_hdr=self.convert_hdr_check.isChecked(),
        )
        logger.info("Generating thumbnail")
        worker = Worker(self, thumb_command, cmd_type="thumb")
        worker.start()

    @reusables.log_exception('flix', show_traceback=False)
    def thumbnail_generated(self):
        pixmap = QtGui.QPixmap(str(self.thumb_file))
        pixmap = pixmap.scaled(320, 180, QtCore.Qt.KeepAspectRatio)
        self.widgets.preview.setPixmap(pixmap)

    def build_scale(self):
        return None

    def get_all_settings(self):
        settings = Box(
            crop=self.build_crop(),
            scale=self.build_scale(),
            source=self.input_video,
            start_time=self.start_time,
            duration=self.duration,
            video_track=self.widgets.video_track.currentIndex()
        )
        settings.update(**self.video_options.get_settings())
        return settings

    def build_commands(self):
        settings = self.get_all_settings()
        convert = self.widgets.convert_to.currentText()[:3].lower()
        commands = self.builders[convert].build(**settings)
        self.video_options.commands.update_commands(commands)
        return commands

    @reusables.log_exception('flix', show_traceback=False)
    def create_video(self):

        if not self.input_video:
            return error_message("Have to select a video first")

        if self.encoding_worker and self.encoding_worker.is_alive():
            return error_message("Still encoding something else")

        output_video = self.save_file(extension="gif")
        if not self.input_video:
            return error_message("Please provide a source video")
        if not output_video:
            logger.warning("No output video specified, canceling encoding")
            return

        commands = self.build_commands()
        for command in commands:
            command.command = command.command.format(ffmpeg=self.ffmpeg,
                                       ffprobe=self.ffprobe,
                                       svt_av1=self.svt_av1,
                                       output=output_video)

        self.command_runner = CW(self, commands)
        self.command_runner.start()
        return

        if not output_video.lower().endswith("gif"):
            return error_message("Output file must end with .gif")
        video_track = self.streams['video'][self.widgets.video_track.currentIndex()]['index']
        start_time = self.start_time
        duration = self.duration
        if Path(output_video).exists():
            em = QtWidgets.QMessageBox()
            em.setText("Output video already exists, overwrite?")
            em.addButton("Overwrite", QtWidgets.QMessageBox.YesRole)
            em.setStandardButtons(QtWidgets.QMessageBox.Close)
            em.exec_()
            if em.clickedButton().text() == "Overwrite":
                os.remove(output_video)
            else:
                return

        crop = self.build_crop()

        scale = None

            # try:
            #     scale = self.build_scale()
            # except ValueError:
            #     return error_message("Scale values are not numeric")
            # except AssertionError:
            #     return error_message("Scale values must be positive integers")

        #self.main.status.showMessage("Encoding...")

        filters = self.flix.generate_filters(scale=scale, crop=crop, disable_hdr=False)
        pal_cmd = self.flix.generate_pallet_command(source=self.input_video, output=self.pallet_file, filters=filters,
                                                    video_track=video_track, start_time=start_time, duration=duration)
        self.flix.execute(pal_cmd).check_returncode()
        cmd = self.flix.generate_gif_command(source=self.input_video, output=output_video, filters=filters,
                                             video_track=video_track, pallet_file=self.pallet_file,
                                             start_time=start_time, duration=duration, fps=15)
        #self.create_button.setDisabled(True)
        #self.kill_button.show()

        self.encoding_worker = Worker(self, cmd, cmd_type="convert")
        self.encoding_worker.start()