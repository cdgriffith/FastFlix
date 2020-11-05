#!/usr/bin/env python
# -*- coding: utf-8 -*-
import importlib.machinery  # Needed for pyinstaller
from dataclasses import asdict
import logging
import os
import secrets
import tempfile
import time
from datetime import timedelta
from pathlib import Path
from queue import Queue
import copy
from typing import Union, Tuple, List, Dict

import pkg_resources
import reusables
from box import Box
from qtpy import QtCore, QtGui, QtWidgets
from appdirs import user_data_dir

from fastflix.encoders.common import helpers
from fastflix.flix import (
    FlixError,
    generate_thumbnail_command,
    parse,
    parse_hdr_details,
    get_auto_crop,
    extract_attachments,
)
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.models.video import Video, VideoSettings
from fastflix.shared import FastFlixInternalException, error_message, file_date, time_to_number
from fastflix.widgets.thumbnail_generator import ThumbnailCreator
from fastflix.widgets.video_options import VideoOptions
from fastflix.language import t
from fastflix.widgets.progress_bar import ProgressBar, Task

logger = logging.getLogger("fastflix")

root = os.path.abspath(os.path.dirname(__file__))

only_int = QtGui.QIntValidator()


class Main(QtWidgets.QWidget):
    completed = QtCore.Signal(int)
    thumbnail_complete = QtCore.Signal(int)
    cancelled = QtCore.Signal()
    close_event = QtCore.Signal()

    def __init__(self, parent, app: FastFlixApp):
        super().__init__(parent)
        self.app: FastFlixApp = app
        self.video: Video = Video(Path(), 0, 0, 0)

        self.initialized = False
        self.loading_video = True
        self.scale_updating = False

        self.notifier = Notifier(self, self.app.fastflix.status_queue)
        self.notifier.start()

        self.input_defaults = Box(scale=None, crop=None)
        self.initial_duration = 0

        self.temp_dir = tempfile.TemporaryDirectory(prefix="temp_", dir=app.fastflix.config.work_path)
        self.temp_dir_name = self.temp_dir.name

        self.setAcceptDrops(True)

        self.input_video = None
        self.video_path_widget = QtWidgets.QLineEdit("No Source Selected")
        self.output_video_path_widget = QtWidgets.QLineEdit("")
        self.output_video_path_widget.setDisabled(True)
        self.output_video_path_widget.textChanged.connect(lambda x: self.page_update(build_thumbnail=False))
        self.video_path_widget.setEnabled(False)
        self.video_path_widget.setStyleSheet("QLineEdit{color:#222}")
        self.output_video_path_widget.setStyleSheet("QLineEdit{color:#222}")

        self.widgets = Box(
            start_time=None,
            end_time=None,
            video_track=None,
            rotate=None,
            flip=None,
            crop=Box(top=None, bottom=None, left=None, right=None),
            scale=Box(width=None, height=None, keep_aspect=None),
            remove_metadata=None,
            chapters=None,
            fast_time=None,
            preview=None,
            convert_to=None,
            convert_button=None,
            pause_resume=QtWidgets.QPushButton("Pause"),
        )
        self.buttons = []

        self.thumb_file = Path(self.app.fastflix.config.work_path, "thumbnail_preview.png")

        self.video_options = VideoOptions(
            self,
            app=self.app,
            available_audio_encoders=self.app.fastflix.audio_encoders,
            log_queue=self.app.fastflix.log_queue,
        )

        self.completed.connect(self.conversion_complete)
        self.cancelled.connect(self.conversion_cancelled)
        self.close_event.connect(self.close)
        self.thumbnail_complete.connect(self.thumbnail_generated)
        self.encoding_worker = None
        self.command_runner = None
        self.converting = False
        self.side_data = Box()
        self.default_options = Box()

        self.grid = QtWidgets.QGridLayout()

        self.init_video_area()
        self.init_scale_and_crop()
        self.init_preview_image()

        self.grid.addWidget(self.video_options, 5, 0, 10, 14)
        self.grid.setSpacing(5)
        self.paused = False

        self.disable_all()
        self.setLayout(self.grid)
        self.show()
        self.initialized = True
        self.last_page_update = time.time()

    def get_temp_work_path(self):
        return tempfile.TemporaryDirectory(prefix="temp_", dir=self.app.fastflix.config.work_path)

    def pause_resume(self):
        if not self.paused:
            self.paused = True
            self.app.fastflix.worker_queue.put(["pause"])
            self.widgets.pause_resume.setText("Resume")
            self.widgets.pause_resume.setStyleSheet("background-color: green;")
            logger.info("Pausing FFmpeg conversion via pustils")
        else:
            self.paused = False
            self.app.fastflix.worker_queue.put(["resume"])
            self.widgets.pause_resume.setText("Pause")
            self.widgets.pause_resume.setStyleSheet("background-color: orange;")
            logger.info("Resuming FFmpeg conversion")

    def config_update(self, ffmpeg, ffprobe):
        # TODO change to full app restart
        # self.flix.update(ffmpeg, ffprobe)
        # self.app.fastflix.encoders = load_plugins(self.flix.config)
        self.thumb_file = Path(self.app.fastflix.config.work_path, "thumbnail_preview.png")
        self.change_output_types()
        self.page_update(build_thumbnail=True)

    def init_video_area(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(self.init_button_menu())
        # layout.addWidget(self.video_path_widget)

        output_layout = QtWidgets.QHBoxLayout()

        output_label = QtWidgets.QLabel("Output")
        output_label.setFixedWidth(70)
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_video_path_widget, stretch=True)
        self.output_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirHomeIcon))
        self.output_path_button.clicked.connect(lambda: self.save_file())
        self.output_path_button.setDisabled(True)

        output_layout.addWidget(self.output_path_button)
        layout.addLayout(output_layout)

        layout.addLayout(self.init_video_track_select())

        title_layout = QtWidgets.QHBoxLayout()

        title_label = QtWidgets.QLabel("Title")
        title_label.setFixedWidth(70)
        title_label.setToolTip('Set the "title" tag, sometimes shown as "Movie Name"')
        self.widgets.video_title = QtWidgets.QLineEdit()
        self.widgets.video_title.setToolTip('Set the "title" tag, sometimes shown as "Movie Name"')
        self.widgets.video_title.textChanged.connect(lambda: self.page_update(build_thumbnail=False))

        title_layout.addWidget(title_label)
        title_layout.addWidget(self.widgets.video_title)

        layout.addLayout(title_layout)

        transform_layout = QtWidgets.QHBoxLayout()
        transform_layout.addWidget(self.init_rotate(), stretch=True)
        transform_layout.addWidget(self.init_flip(), stretch=True)

        metadata_layout = QtWidgets.QVBoxLayout()
        self.widgets.remove_metadata = QtWidgets.QCheckBox("Remove Metadata")
        self.widgets.remove_metadata.setChecked(True)
        self.widgets.remove_metadata.toggled.connect(self.page_update)
        self.widgets.remove_metadata.setToolTip(
            "Scrub away all incoming metadata, like video titles, unique markings and so on."
        )
        self.widgets.chapters = QtWidgets.QCheckBox("Copy Chapters")
        self.widgets.chapters.setChecked(True)
        self.widgets.chapters.toggled.connect(self.page_update)
        self.widgets.chapters.setToolTip("Copy the chapter markers as is from incoming source.")

        metadata_layout.addWidget(self.widgets.remove_metadata)
        metadata_layout.addWidget(self.widgets.chapters)

        transform_layout.addLayout(metadata_layout)

        layout.addLayout(transform_layout)

        layout.addLayout(self.init_profile())
        layout.addStretch()
        self.grid.addLayout(layout, 0, 0, 6, 6)

    def init_scale_and_crop(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.init_scale())
        layout.addWidget(self.init_crop())
        layout.addWidget(self.init_start_time())
        layout.addStretch()
        self.grid.addLayout(layout, 0, 6, 5, 4)

    def init_button_menu(self):
        layout = QtWidgets.QHBoxLayout()
        open_input_file = QtWidgets.QPushButton("🎞 Source")
        open_input_file.setFixedSize(95, 50)
        open_input_file.setDefault(True)
        open_input_file.clicked.connect(lambda: self.open_file())
        open_input_file.setStyleSheet("background: blue")
        convert = QtWidgets.QPushButton("Convert 🎥")
        convert.setFixedSize(95, 50)
        convert.setStyleSheet("background: green")
        convert.clicked.connect(lambda: self.create_video())
        convert.setDisabled(True)
        self.widgets.convert_button = convert
        self.widgets.convert_button.setStyleSheet("background-color:grey;")

        self.widgets.pause_resume.setDisabled(True)
        self.widgets.pause_resume.setStyleSheet("background-color: gray;")
        self.widgets.pause_resume.clicked.connect(self.pause_resume)
        self.widgets.pause_resume.setFixedSize(60, 50)

        layout.addWidget(open_input_file)
        layout.addStretch()
        layout.addLayout(self.init_output_type())
        layout.addStretch()
        layout.addWidget(self.widgets.pause_resume)
        layout.addWidget(convert)
        return layout

    # def init_input_file(self):
    #     layout = QtWidgets.QHBoxLayout()
    #     self.widgets.input_file = QtWidgets.QLineEdit("")
    #     self.widgets.input_file.setReadOnly(True)
    #     open_input_file = QtWidgets.QPushButton("...")
    #     open_input_file.setFixedWidth(50)
    #     open_input_file.setMaximumHeight(22)
    #     open_input_file.setDefault(True)
    #     layout.addWidget(QtWidgets.QLabel("Source File:"))
    #     layout.addWidget(self.widgets.input_file)
    #     layout.addWidget(open_input_file)
    #     layout.setSpacing(10)
    #     open_input_file.clicked.connect(lambda: self.open_file())
    #     return layout

    def init_video_track_select(self):
        layout = QtWidgets.QHBoxLayout()
        self.widgets.video_track = QtWidgets.QComboBox()
        self.widgets.video_track.addItems([])
        self.widgets.video_track.currentIndexChanged.connect(lambda: self.page_update())

        track_label = QtWidgets.QLabel("Video Track")
        track_label.setFixedWidth(65)
        layout.addWidget(track_label)
        layout.addWidget(self.widgets.video_track, stretch=1)
        layout.setSpacing(10)
        return layout

    def init_profile(self):
        layout = QtWidgets.QHBoxLayout()
        self.widgets.profile_box = QtWidgets.QComboBox()
        self.widgets.profile_box.addItems(self.app.fastflix.config.profiles.keys())
        self.widgets.profile_box.currentIndexChanged.connect(self.set_profile)
        layout.addWidget(QtWidgets.QLabel(t("Profile")))
        layout.addWidget(self.widgets.profile_box)
        layout.addStretch()
        return layout

    def set_profile(self):
        # TODO Have to update all the defaults
        # self.video_options.new_source()
        previous_auto_crop = self.app.fastflix.config.opt("auto_crop")
        self.app.fastflix.config.default_profile = self.widgets.profile_box.currentText()
        self.app.fastflix.config.save()
        if not previous_auto_crop and self.app.fastflix.config.opt("auto_crop"):
            self.get_auto_crop()
        self.loading_video = True
        self.widgets.scale.keep_aspect.setChecked(self.app.fastflix.config.opt("keep_aspect_ratio"))
        self.widgets.rotate.setCurrentIndex(self.app.fastflix.config.opt("rotate") // 90)
        self.widgets.flip.setCurrentIndex(self.app.fastflix.config.opt("flip"))
        self.video_options.update_profile()
        # Hack to prevent a lot of thumbnail generation
        self.loading_video = False
        self.page_update()

    def init_flip(self):
        self.widgets.flip = QtWidgets.QComboBox()
        rotation_folder = "../data/rotations/FastFlix"

        no_rot_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder}.png")).resolve())
        vert_flip_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder} VF.png")).resolve())
        hoz_flip_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder} HF.png")).resolve())
        rot_180_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder} 180.png")).resolve())

        self.widgets.flip.addItems(["No Flip", "Vertical Flip", "Horizontal Flip", "Vert + Hoz Flip"])
        self.widgets.flip.setItemIcon(0, QtGui.QIcon(no_rot_file))
        self.widgets.flip.setItemIcon(1, QtGui.QIcon(vert_flip_file))
        self.widgets.flip.setItemIcon(2, QtGui.QIcon(hoz_flip_file))
        self.widgets.flip.setItemIcon(3, QtGui.QIcon(rot_180_file))
        self.widgets.flip.setIconSize(QtCore.QSize(35, 35))
        self.widgets.flip.currentIndexChanged.connect(lambda: self.page_update())
        return self.widgets.flip

    def get_flips(self) -> Tuple[bool, bool]:
        mapping = {0: (False, False), 1: (True, False), 2: (False, True), 3: (True, True)}
        return mapping[self.widgets.flip.currentIndex()]

    def init_rotate(self):
        self.widgets.rotate = QtWidgets.QComboBox()
        rotation_folder = "../data/rotations/FastFlix"

        no_rot_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder}.png")).resolve())
        rot_90_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder} C90.png")).resolve())
        rot_270_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder} CC90.png")).resolve())
        rot_180_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder} 180.png")).resolve())

        self.widgets.rotate.addItems(["No Rotation", "90°", "180°", "270°"])
        self.widgets.rotate.setItemIcon(0, QtGui.QIcon(no_rot_file))
        self.widgets.rotate.setItemIcon(1, QtGui.QIcon(rot_90_file))
        self.widgets.rotate.setItemIcon(2, QtGui.QIcon(rot_180_file))
        self.widgets.rotate.setItemIcon(3, QtGui.QIcon(rot_270_file))
        self.widgets.rotate.setIconSize(QtCore.QSize(35, 35))
        self.widgets.rotate.currentIndexChanged.connect(lambda: self.page_update())
        return self.widgets.rotate

    def rotation_to_transpose(self):
        mapping = {0: None, 1: 1, 2: 4, 3: 2}
        return mapping[self.widgets.rotate.currentIndex()]

    def change_output_types(self):
        self.widgets.convert_to.clear()
        self.widgets.convert_to.addItems([f"   {x}" for x in self.app.fastflix.encoders.keys()])
        for i, plugin in enumerate(self.app.fastflix.encoders.values()):
            if getattr(plugin, "icon", False):
                self.widgets.convert_to.setItemIcon(i, QtGui.QIcon(plugin.icon))
        self.widgets.convert_to.setFont(QtGui.QFont("helvetica", 10, weight=57))
        self.widgets.convert_to.setIconSize(QtCore.QSize(40, 40))

    def init_output_type(self):
        layout = QtWidgets.QHBoxLayout()
        self.widgets.convert_to = QtWidgets.QComboBox()
        self.change_output_types()
        self.widgets.convert_to.currentTextChanged.connect(self.change_conversion)
        # layout.addWidget(QtWidgets.QLabel("Encoder: "), stretch=0)
        layout.addWidget(self.widgets.convert_to, stretch=0)
        layout.addStretch()
        layout.setSpacing(10)

        return layout

    def change_conversion(self):
        if not self.output_video_path_widget.text().endswith(
            self.app.fastflix.encoders[self.convert_to].video_extension
        ):
            self.output_video_path_widget.setText(self.generate_output_filename)
        self.video_options.change_conversion(self.widgets.convert_to.currentText())

    def init_start_time(self):
        group_box = QtWidgets.QGroupBox()
        group_box.setStyleSheet("QGroupBox{padding-top:18px; margin-top:-18px}")
        self.widgets.start_time, layout = self.build_hoz_int_field(
            "Start  ", right_stretch=False, left_stretch=True, time_field=True
        )
        self.widgets.end_time, layout = self.build_hoz_int_field(
            "  End  ", left_stretch=False, right_stretch=True, layout=layout, time_field=True
        )
        self.widgets.start_time.textChanged.connect(lambda: self.page_update())
        self.widgets.end_time.textChanged.connect(lambda: self.page_update())
        self.widgets.fast_time = QtWidgets.QComboBox()
        self.widgets.fast_time.addItems(["fast", "exact"])
        self.widgets.fast_time.setCurrentIndex(0)
        self.widgets.fast_time.setToolTip(
            "uses [fast] seek to a rough position ahead of timestamp, "
            "vs a specific [exact] frame lookup. (GIF encodings use [fast])"
        )
        self.widgets.fast_time.currentIndexChanged.connect(lambda: self.page_update(build_thumbnail=False))
        self.widgets.fast_time.setFixedWidth(55)
        layout.addWidget(QtWidgets.QLabel(" "))
        layout.addWidget(self.widgets.fast_time, QtCore.Qt.AlignRight)
        group_box.setLayout(layout)
        return group_box

    def init_scale(self):
        scale_area = QtWidgets.QGroupBox(self)
        scale_area.setFont(self.app.font())
        scale_area.setStyleSheet("QGroupBox{padding-top:15px; margin-top:-18px}")
        scale_layout = QtWidgets.QVBoxLayout()

        self.widgets.scale.width, new_scale_layout = self.build_hoz_int_field("Width  ", right_stretch=False)
        self.widgets.scale.height, new_scale_layout, lb, rb = self.build_hoz_int_field(
            "  Height  ", left_stretch=False, layout=new_scale_layout, return_buttons=True
        )
        self.widgets.scale.height.setDisabled(True)
        self.widgets.scale.height.setText("Auto")
        lb.setDisabled(True)
        rb.setDisabled(True)
        QtWidgets.QPushButton()

        # TODO scale 0 error

        self.widgets.scale.width.textChanged.connect(lambda: self.scale_update())
        self.widgets.scale.height.textChanged.connect(lambda: self.scale_update())

        bottom_row = QtWidgets.QHBoxLayout()
        self.widgets.scale.keep_aspect = QtWidgets.QCheckBox("Keep aspect ratio")
        self.widgets.scale.keep_aspect.setMaximumHeight(40)
        self.widgets.scale.keep_aspect.setChecked(True)
        self.widgets.scale.keep_aspect.toggled.connect(lambda: self.toggle_disable((self.widgets.scale.height, lb, rb)))
        self.widgets.scale.keep_aspect.toggled.connect(lambda: self.keep_aspect_update())

        label = QtWidgets.QLabel("Scale", alignment=(QtCore.Qt.AlignBottom | QtCore.Qt.AlignRight))
        label.setStyleSheet("QLabel{color:#777}")
        label.setMaximumHeight(40)
        bottom_row.addWidget(self.widgets.scale.keep_aspect, alignment=QtCore.Qt.AlignCenter)

        scale_layout.addLayout(new_scale_layout)
        bottom_row.addWidget(label)
        scale_layout.addLayout(bottom_row)

        scale_area.setLayout(scale_layout)

        return scale_area

    def init_crop(self):
        # TODO don't let people put in letters to boxes
        crop_box = QtWidgets.QGroupBox()
        crop_box.setStyleSheet("QGroupBox{padding-top:17px; margin-top:-18px}")
        crop_layout = QtWidgets.QVBoxLayout()
        self.widgets.crop.top, crop_top_layout = self.build_hoz_int_field("       Top  ")
        self.widgets.crop.left, crop_hz_layout = self.build_hoz_int_field("Left  ", right_stretch=False)
        self.widgets.crop.right, crop_hz_layout = self.build_hoz_int_field(
            "    Right  ", left_stretch=False, layout=crop_hz_layout
        )
        self.widgets.crop.bottom, crop_bottom_layout = self.build_hoz_int_field("Bottom  ", right_stretch=True)

        self.widgets.crop.top.textChanged.connect(lambda: self.page_update())
        self.widgets.crop.left.textChanged.connect(lambda: self.page_update())
        self.widgets.crop.right.textChanged.connect(lambda: self.page_update())
        self.widgets.crop.bottom.textChanged.connect(lambda: self.page_update())

        label = QtWidgets.QLabel("Crop", alignment=(QtCore.Qt.AlignBottom | QtCore.Qt.AlignRight))
        label.setStyleSheet("QLabel{color:#777}")
        label.setMaximumHeight(40)

        auto_crop = QtWidgets.QPushButton("Auto")
        auto_crop.setMaximumHeight(40)
        auto_crop.setFixedWidth(50)
        auto_crop.setToolTip(
            "Automatically detect black borders at current start time (or at 10% in if start time is 0)"
        )
        auto_crop.clicked.connect(self.get_auto_crop)
        self.buttons.append(auto_crop)

        # crop_bottom_layout.addWidget(label)
        l2 = QtWidgets.QVBoxLayout()
        l2.addWidget(auto_crop, alignment=(QtCore.Qt.AlignTop | QtCore.Qt.AlignRight))
        l2.addWidget(label, alignment=(QtCore.Qt.AlignBottom | QtCore.Qt.AlignRight))

        crop_layout.addLayout(crop_top_layout)
        crop_layout.addLayout(crop_hz_layout)
        crop_layout.addLayout(crop_bottom_layout)
        outer = QtWidgets.QHBoxLayout()
        outer.addLayout(crop_layout)
        outer.addLayout(l2)
        crop_box.setLayout(outer)

        return crop_box

    @staticmethod
    def toggle_disable(widget_list):
        for widget in widget_list:
            widget.setDisabled(widget.isEnabled())

    @property
    def title(self):
        return self.widgets.video_title.text()

    def build_hoz_int_field(
        self,
        name,
        button_size=22,
        left_stretch=True,
        right_stretch=True,
        layout=None,
        return_buttons=False,
        time_field=False,
    ):

        widget = QtWidgets.QLineEdit(self.number_to_time(0) if time_field else "0")
        widget.setObjectName(name)
        if not time_field:
            widget.setValidator(only_int)
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
        minus_button.clicked.connect(
            lambda: [
                self.modify_int(widget, "minus", time_field),
                self.page_update(),
            ]
        )
        plus_button = QtWidgets.QPushButton("+")
        plus_button.setAutoRepeat(True)
        plus_button.setFixedSize(button_size, button_size)
        plus_button.clicked.connect(
            lambda: [
                self.modify_int(widget, "add", time_field),
                self.page_update(),
            ]
        )
        self.buttons.append(minus_button)
        self.buttons.append(plus_button)
        if not time_field:
            widget.setFixedWidth(45)
        else:
            widget.setFixedWidth(65)
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
        self.widgets.preview.setFixedSize(320, 213)
        self.widgets.preview.setAlignment(QtCore.Qt.AlignCenter)
        self.widgets.preview.setStyleSheet("border: 2px solid #dddddd;")  # background-color:#f0f0f0

        # buttons = self.init_preview_buttons()

        self.grid.addWidget(self.widgets.preview, 0, 10, 5, 4, (QtCore.Qt.AlignTop | QtCore.Qt.AlignRight))

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

        refresh.clicked.connect(lambda: self.page_update())

        layout.addWidget(refresh)
        layout.addWidget(preview)
        layout.addWidget(one)
        layout.addWidget(two)
        layout.addStretch()
        return layout

    def modify_int(self, widget, method="add", time_field=False):
        modifier = 1
        if time_field:
            value = time_to_number(widget.text())
            if value is None:
                return
        else:
            modifier = getattr(self.app.fastflix.encoders[self.convert_to], "video_dimension_divisor", 1)
            try:
                value = int(widget.text())
                value = int(value + (value % modifier))
            except ValueError:
                logger.exception("This shouldn't be possible, but you somehow put in not an integer")
                return

        modifier = modifier if method == "add" else -modifier
        new_value = value + modifier
        if time_field and new_value < 0:
            return
        widget.setText(str(new_value) if not time_field else self.number_to_time(new_value))
        self.build_commands()

    @reusables.log_exception("fastflix", show_traceback=False)
    def open_file(self):
        filename = QtWidgets.QFileDialog.getOpenFileName(
            self,
            caption="Open Video",
            filter="Video Files (*.mkv *.mp4 *.m4v *.mov *.avi *.divx *.webm *.mpg *.mp2 *.mpeg *.mpe *.mpv *.ogg *.m4p"
            " *.wmv *.mov *.qt *.flv *.hevc *.gif *.webp *.vob *.ogv *.ts *.mts *.m2ts *.yuv *.rm *.svi *.3gp *.3g2)",
            directory=str(
                self.app.fastflix.current_video.source.parent if self.app.fastflix.current_video else Path.home()
            ),
        )
        if not filename or not filename[0]:
            return
        self.input_video = Path(filename[0])
        self.video_path_widget.setText(str(self.input_video))
        self.output_video_path_widget.setText(self.generate_output_filename)
        self.output_video_path_widget.setDisabled(False)
        self.output_path_button.setDisabled(False)
        self.update_video_info()
        self.page_update()

    @property
    def generate_output_filename(self):
        if self.input_video:
            return f"{self.input_video.parent / self.input_video.stem}-fastflix-{secrets.token_hex(2)}.{self.app.fastflix.encoders[self.convert_to].video_extension}"
        return f"{Path('~').expanduser()}{os.sep}fastflix-{secrets.token_hex(2)}.{self.app.fastflix.encoders[self.convert_to].video_extension}"

    @property
    def output_video(self):
        return self.output_video_path_widget.text()

    @reusables.log_exception("fastflix", show_traceback=False)
    def save_file(self, extension="mkv"):
        filename = QtWidgets.QFileDialog.getSaveFileName(
            self, caption="Save Video As", directory=self.generate_output_filename, filter=f"Save File (*.{extension})"
        )
        self.output_video_path_widget.setText(filename[0] if filename else "")

    def get_auto_crop(self):
        if not self.input_video or not self.initialized or self.loading_video:
            return

        start_pos = self.start_time or self.app.fastflix.current_video.duration // 10

        blocks = int((self.app.fastflix.current_video.duration - start_pos) // 5)
        times = [
            x
            for x in range(int(start_pos), int(self.app.fastflix.current_video.duration), blocks)
            if x < self.app.fastflix.current_video.duration
        ][:4]

        self.app.processEvents()
        result_list = []
        tasks = [
            Task(
                f"Finding black bars at {timedelta(seconds=x)}",
                get_auto_crop,
                dict(
                    source=self.input_video,
                    video_width=self.app.fastflix.current_video.width,
                    video_height=self.app.fastflix.current_video.height,
                    input_track=self.original_video_track,
                    start_time=x,
                    end_time=self.end_time,
                    result_list=result_list,
                ),
            )
            for x in times
        ]
        ProgressBar(self.app, tasks)

        smallest = (self.app.fastflix.current_video.height + self.app.fastflix.current_video.width) * 2
        selected = result_list[0]
        for result in result_list:
            if (total := sum(result)) < smallest:
                selected = result
                smallest = total

        r, b, l, t = selected

        if t + b > self.app.fastflix.current_video.height * 0.9 or r + l > self.app.fastflix.current_video.width * 0.9:
            logger.warning(
                f"{t('Autocrop tried to crop too much')}"
                f" ({t('left')} {l}, {t('top')} {t}, {t('right')} {r}, {t('bottom')} {b}), {t('ignoring')}"
            )
            return

        # Hack to stop thumb gen
        self.loading_video = True
        self.widgets.crop.top.setText(str(t))
        self.widgets.crop.left.setText(str(l))
        self.widgets.crop.right.setText(str(r))
        self.loading_video = False
        self.widgets.crop.bottom.setText(str(b))

    def build_crop(self) -> Union[str, None]:
        try:
            top = int(self.widgets.crop.top.text())
            left = int(self.widgets.crop.left.text())
            right = int(self.widgets.crop.right.text())
            bottom = int(self.widgets.crop.bottom.text())
        except ValueError:
            logger.error("Invalid crop")
            return None
        width = self.app.fastflix.current_video.width - right - left
        height = self.app.fastflix.current_video.height - bottom - top
        if (top + left + right + bottom) == 0:
            return None
        try:
            assert top >= 0, t("Top must be positive number")
            assert left >= 0, t("Left must be positive number")
            assert width > 0, t("Total video width must be greater than 0")
            assert height > 0, t("Total video height must be greater than 0")
            assert width <= self.app.fastflix.current_video.width, t("Width must be smaller than video width")
            assert height <= self.app.fastflix.current_video.height, t("Height must be smaller than video height")
        except AssertionError as err:
            error_message(f"{t('Invalid Crop')}: {err}")
            return
        return f"{width}:{height}:{left}:{top}"

    def keep_aspect_update(self) -> None:
        keep_aspect = self.widgets.scale.keep_aspect.isChecked()

        if keep_aspect:
            # TODO need to find way to translate and keep logic
            self.widgets.scale.height.setText("Auto")
        else:
            try:
                scale_width = int(self.widgets.scale.width.text())
                assert scale_width > 0
            except (ValueError, AssertionError):
                self.scale_updating = False
                if self.widgets.scale.height.text() == "Auto":
                    self.widgets.scale.height.setText("-1")
                return logger.warning("Invalid width")

            if self.app.fastflix.current_video.height == 0 or self.app.fastflix.current_video.width == 0:
                return logger.warning("Input video does not exist or has 0 dimension")

            ratio = self.app.fastflix.current_video.height / self.app.fastflix.current_video.width
            scale_height = ratio * scale_width
            mod = int(scale_height % 2)
            if mod:
                scale_height -= mod
                logger.info(f"Have to adjust scale height by {mod} pixels")
            self.widgets.scale.height.setText(str(int(scale_height)))
        self.scale_update()

    def disable_all(self):
        for name, widget in self.widgets.items():
            if name in ("preview", "convert_button", "pause_resume"):
                continue
            if isinstance(widget, dict):
                for sub_widget in widget.values():
                    if isinstance(sub_widget, QtWidgets.QWidget):
                        sub_widget.setDisabled(True)
            elif isinstance(widget, QtWidgets.QWidget):
                widget.setDisabled(True)
        for button in self.buttons:
            button.setDisabled(True)
        self.output_path_button.setDisabled(True)
        self.output_video_path_widget.setDisabled(True)

    def enable_all(self):
        for name, widget in self.widgets.items():
            if name in ("preview", "convert_button", "pause_resume"):
                continue
            if isinstance(widget, dict):
                for sub_widget in widget.values():
                    if isinstance(sub_widget, QtWidgets.QWidget):
                        sub_widget.setDisabled(False)
            elif isinstance(widget, QtWidgets.QWidget):
                widget.setDisabled(False)
        for button in self.buttons:
            button.setDisabled(False)
        if self.widgets.scale.keep_aspect.isChecked():
            self.widgets.scale.height.setDisabled(True)
        self.output_path_button.setDisabled(False)
        self.output_video_path_widget.setDisabled(False)

    @reusables.log_exception("fastflix", show_traceback=False)
    def scale_update(self):
        if self.scale_updating:
            return False

        self.scale_updating = True

        keep_aspect = self.widgets.scale.keep_aspect.isChecked()

        self.widgets.scale.height.setDisabled(keep_aspect)
        height = self.app.fastflix.current_video.height
        width = self.app.fastflix.current_video.width
        if self.build_crop():
            width, height, *_ = (int(x) for x in self.build_crop().split(":"))

        if keep_aspect and (not height or not width):
            self.scale_updating = False
            return logger.warning(t("Invalid source dimensions"))
            # return self.scale_warning_message.setText("Invalid source dimensions")

        try:
            scale_width = int(self.widgets.scale.width.text())
            assert scale_width > 0
        except (ValueError, AssertionError):
            self.scale_updating = False
            return logger.warning(t("Invalid width"))
            # return self.scale_warning_message.setText("Invalid main_width")

        if scale_width % 2:
            self.scale_updating = False
            self.widgets.scale.width.setStyleSheet("background-color: red;")
            self.widgets.scale.width.setToolTip(
                f"{t('Width must be divisible by 2 - Source width')}: {self.app.fastflix.current_video.width}"
            )
            return logger.warning(t("Width must be divisible by 2"))
            # return self.scale_warning_message.setText("Width must be divisible by 8")
        else:
            self.widgets.scale.width.setToolTip(f"{t('Source width')}: {self.app.fastflix.current_video.width}")

        if keep_aspect:
            self.widgets.scale.height.setText("Auto")
            self.widgets.scale.width.setStyleSheet("background-color: white;")
            self.widgets.scale.height.setStyleSheet("background-color: white;")
            self.page_update()
            self.scale_updating = False
            return
            # ratio = self.app.fastflix.current_video.height / self.app.fastflix.current_video.width
            # scale_height = ratio * scale_width
            # self.widgets.scale.height.setText(str(int(scale_height)))
            # mod = int(scale_height % 2)
            # if mod:
            #     scale_height -= mod
            #     logger.info(f"Have to adjust scale height by {mod} pixels")
            #     # self.scale_warning_message.setText()
            # logger.info(f"height has -{mod}px off aspect")
            # self.widgets.scale.height.setText(str(int(scale_height)))
            # self.widgets.scale.width.setStyleSheet("background-color: white;")
            # self.widgets.scale.height.setStyleSheet("background-color: white;")
            # self.page_update()
            # self.scale_updating = False
            # return

        scale_height = self.widgets.scale.height.text()
        try:
            scale_height = -1 if scale_height == "Auto" else int(scale_height)
            assert scale_height == -1 or scale_height > 0
        except (ValueError, AssertionError):
            self.scale_updating = False
            return logger.warning(t("Invalid height"))
            # return self.scale_warning_message.setText("Invalid height")

        if scale_height != -1 and scale_height % 2:
            self.widgets.scale.height.setStyleSheet("background-color: red;")
            self.widgets.scale.height.setToolTip(
                f"{t('Height must be divisible by 2 - Source height')}: {self.app.fastflix.current_video.height}"
            )
            self.scale_updating = False
            return logger.warning(
                f"{t('Height must be divisible by 2 - Source height')}: {self.app.fastflix.current_video.height}"
            )
        else:
            self.widgets.scale.height.setToolTip(f"{t('Source height')}: {self.app.fastflix.current_video.height}")
            # return self.scale_warning_message.setText("Height must be divisible by 8")
        # self.scale_warning_message.setText("")
        self.widgets.scale.width.setStyleSheet("background-color: white;")
        self.widgets.scale.height.setStyleSheet("background-color: white;")
        self.page_update()
        self.scale_updating = False

    def clear_current_video(self):
        self.app.fastflix.current_video = None
        self.input_video = None
        self.video_path_widget.setText(t("No Source Selected"))
        self.output_video_path_widget.setText("")
        self.output_path_button.setDisabled(True)
        self.output_video_path_widget.setDisabled(True)
        for i in range(self.widgets.video_track.count()):
            self.widgets.video_track.removeItem(0)
        self.widgets.convert_button.setDisabled(True)
        self.widgets.convert_button.setStyleSheet("background-color:gray;")
        self.widgets.preview.setText(t("No Video File"))
        self.page_update()

    @reusables.log_exception("fastflix", show_traceback=False)
    def update_video_info(self):
        self.loading_video = True
        self.app.fastflix.current_video = Video(source=self.input_video, work_path=self.get_temp_work_path())
        tasks = [
            Task(t("Parse Video details"), parse),
            Task(t("Extract covers"), extract_attachments),
            Task(t("Determine HDR details"), parse_hdr_details),
        ]

        try:
            ProgressBar(self.app, tasks)
        except FlixError:
            error_message(f"{t('Not a video file')}<br>{self.input_video}")
            self.clear_current_video()

        text_video_tracks = [
            f'{x.index}: {t("codec")} {x.codec_name} - {x.get("pix_fmt")} - {t("profile")} {x.get("profile")}'
            for x in self.app.fastflix.current_video.streams.video
        ]
        self.widgets.video_track.clear()
        self.widgets.crop.top.setText("0")
        self.widgets.crop.left.setText("0")
        self.widgets.crop.right.setText("0")
        self.widgets.crop.bottom.setText("0")
        self.widgets.start_time.setText("0:00:00")

        self.widgets.scale.width.setText(
            str(
                self.app.fastflix.current_video.width
                + (
                    self.app.fastflix.current_video.width
                    % self.app.fastflix.encoders[self.convert_to].video_dimension_divisor
                )
            )
        )
        self.widgets.scale.width.setToolTip(f"{t('Source width')}: {self.app.fastflix.current_video.width}")
        self.widgets.scale.height.setText(
            str(
                self.app.fastflix.current_video.height
                + (
                    self.app.fastflix.current_video.height
                    % self.app.fastflix.encoders[self.convert_to].video_dimension_divisor
                )
            )
        )
        self.widgets.scale.height.setToolTip(f"{t('Source height')}: {self.app.fastflix.current_video.height}")
        self.widgets.video_track.addItems(text_video_tracks)

        self.widgets.video_track.setDisabled(bool(len(self.app.fastflix.current_video.streams.video) == 1))

        logger.debug(f"{len(self.app.fastflix.current_video.streams['video'])} {t('video tracks found')}")
        logger.debug(f"{len(self.app.fastflix.current_video.streams['audio'])} {t('audio tracks found')}")

        if self.app.fastflix.current_video.streams["subtitle"]:
            logger.debug(f"{len(self.app.fastflix.current_video.streams['subtitle'])} {t('subtitle tracks found')}")
        if self.app.fastflix.current_video.streams["attachment"]:
            logger.debug(f"{len(self.app.fastflix.current_video.streams['attachment'])} {t('attachment tracks found')}")
        if self.app.fastflix.current_video.streams["data"]:
            logger.debug(f"{len(self.app.fastflix.current_video.streams['data'])} {t('data tracks found')}")

        self.widgets.end_time.setText(self.number_to_time(self.app.fastflix.current_video.duration))
        title_name = [
            v for k, v in self.app.fastflix.current_video.format.get("tags", {}).items() if k.lower() == "title"
        ]
        if title_name:
            self.widgets.video_title.setText(title_name[0])
        else:
            self.widgets.video_title.setText("")

        self.video_options.new_source()
        if self.app.fastflix.config.opt("auto_crop"):
            self.get_auto_crop()
        self.enable_all()
        self.widgets.convert_button.setDisabled(False)
        self.widgets.convert_button.setStyleSheet("background-color:green;")
        self.loading_video = False

    @property
    def video_track(self) -> int:
        return int(self.widgets.video_track.currentIndex())

    @property
    def original_video_track(self) -> int:
        return int(self.widgets.video_track.currentText().split(":", 1)[0])

    @property
    def pix_fmt(self) -> str:
        return self.app.fastflix.current_video.streams.video[self.video_track].pix_fmt

    @staticmethod
    def number_to_time(number) -> str:
        return str(timedelta(seconds=float(number)))[:10]

    @property
    def start_time(self) -> float:
        return time_to_number(self.widgets.start_time.text())

    @property
    def end_time(self) -> float:
        return time_to_number(self.widgets.end_time.text())

    @property
    def fast_time(self) -> bool:
        return self.widgets.fast_time.currentText() == "fast"

    @property
    def remove_metadata(self) -> bool:
        return self.widgets.remove_metadata.isChecked()

    @property
    def copy_chapters(self) -> bool:
        return self.widgets.chapters.isChecked()

    @reusables.log_exception("fastflix", show_traceback=False)
    def generate_thumbnail(self):
        if not self.input_video or self.loading_video:
            return

        remove_hdr = False
        if self.app.fastflix.current_video.video_settings.pix_fmt == "yuv420p10le" and self.pix_fmt in (
            "yuv420p10le",
            "yuv420p12le",
        ):
            remove_hdr = True
        filters = helpers.generate_filters(
            custom_filters="scale='min(320\\,iw):-1'",
            remove_hdr=remove_hdr,
            **asdict(self.app.fastflix.current_video.video_settings),
        )

        preview_place = (
            self.app.fastflix.current_video.duration // 10
            if self.app.fastflix.current_video.video_settings.start_time == 0
            else self.app.fastflix.current_video.video_settings.start_time
        )

        thumb_command = generate_thumbnail_command(
            config=self.app.fastflix.config,
            source=self.input_video,
            output=self.thumb_file,
            filters=filters,
            start_time=preview_place,
            input_track=self.app.fastflix.current_video.video_settings.selected_track,
        )
        try:
            self.thumb_file.unlink()
        except OSError:
            pass
        worker = ThumbnailCreator(self, thumb_command)
        worker.start()

    @reusables.log_exception("fastflix", show_traceback=False)
    def thumbnail_generated(self, success=False):
        if not success or not self.thumb_file.exists():
            self.widgets.preview.setText(t("Error Updating Thumbnail"))
            return

        pixmap = QtGui.QPixmap(str(self.thumb_file))
        pixmap = pixmap.scaled(320, 213, QtCore.Qt.KeepAspectRatio)
        self.widgets.preview.setPixmap(pixmap)

    def build_scale(self):
        width = self.widgets.scale.width.text()
        height = self.widgets.scale.height.text()
        if height == "Auto":
            height = -1
        return f"{width}:{height}"

    def get_all_settings(self):
        if not self.initialized:
            return
        stream_info = self.app.fastflix.current_video.streams.video[self.video_track]

        end_time = self.end_time
        if self.end_time == float(self.app.fastflix.current_video.format.get("duration", 0)):
            end_time = None
        if self.end_time and self.end_time - 0.1 <= self.app.fastflix.current_video.duration <= self.end_time + 0.1:
            end_time = None

        scale = self.build_scale()
        if scale in (
            f"{stream_info.width}:-1",
            f"-1:{stream_info.height}",
            f"{stream_info.width}:{stream_info.height}",
        ):
            scale = None

        v_flip, h_flip = self.get_flips()
        self.app.fastflix.current_video.video_settings = VideoSettings(
            crop=self.build_crop(),
            scale=scale,
            start_time=self.start_time,
            end_time=end_time,
            selected_track=self.original_video_track,
            # stream_track=self.video_track,
            pix_fmt=self.pix_fmt,
            rotate=self.rotation_to_transpose(),
            vertical_flip=v_flip,
            horizontal_flip=h_flip,
            output_path=Path(self.output_video),
            # streams=self.app.fastflix.current_video.streams,
            # format_info=self.app.fastflix.current_video.format,
            # work_dir=self.app.fastflix.current_video.work_path,
            # side_data=self.side_data,
            # ffmpeg=self.app.fastflix.config.ffmpeg,
            # ffprobe=self.app.fastflix.config.ffprobe,
            # temp_dir=self.temp_dir_name,
            # output_video=self.output_video,
            # remove_metadata=self.remove_metadata,
            # copy_chapters=self.copy_chapters,
            # fast_time=self.fast_time,
            video_title=self.title,
        )

        self.app.fastflix.current_video.video_settings.encoder_options = self.video_options.get_settings()

    @property
    def current_encoder(self):
        try:
            return self.app.fastflix.encoders[
                self.app.fastflix.current_video.video_settings.video_encoder_settings.name
            ]
        except AttributeError:
            return self.app.fastflix.encoders[self.convert_to]

    def build_commands(self) -> bool:
        if not self.initialized or not self.app.fastflix.current_video.streams or self.loading_video:
            return False
        try:
            self.get_all_settings()
        except FastFlixInternalException as err:
            error_message(str(err))
            return False

        commands = self.current_encoder.build(fastflix=self.app.fastflix)
        if not commands:
            return False
        after_done = self.video_options.commands.after_done(builder=True)
        if after_done is not None:
            commands.append(after_done)
        self.video_options.commands.update_commands(commands)
        self.app.fastflix.current_video.video_settings.conversion_commands = commands
        return True

    def page_update(self, build_thumbnail=True):
        if not self.initialized or self.loading_video:
            return
        self.last_page_update = time.time()
        self.video_options.refresh()
        self.build_commands()
        if build_thumbnail:
            self.generate_thumbnail()

    def close(self, no_cleanup=False):
        try:
            self.app.fastflix.status_queue.put("exit")
        except KeyboardInterrupt:
            if not no_cleanup:
                try:
                    self.temp_dir.cleanup()
                except Exception:
                    pass
            self.notifier.terminate()
            super().close()
            self.container.close()
            raise

    @property
    def convert_to(self):
        if self.widgets.convert_to:
            return self.widgets.convert_to.currentText().strip()
        return list(self.app.fastflix.encoders.keys())[0]

    # @property
    # def current_encoder(self):
    #     return self.app.fastflix.encoders[self.convert_to]

    @reusables.log_exception("fastflix", show_traceback=False)
    def create_video(self):
        if self.converting:
            self.app.fastflix.worker_queue.put(["cancel"])
            return

        if not self.input_video:
            return error_message(t("Have to select a video first"))
        if self.encoding_worker and self.encoding_worker.is_alive():
            return error_message(t("Still encoding something else"))
        if not self.output_video:
            return error_message(t("Please specify output video"))
        if self.input_video.resolve().absolute() == Path(self.output_video).resolve().absolute():
            return error_message(t("Output video path is same as source!"))

        if not self.output_video.lower().endswith(self.current_encoder.video_extension):
            sm = QtWidgets.QMessageBox()
            sm.setText(
                f"Output video file does not have expected extension ({self.current_encoder.video_extension}), which can case issues."
            )
            sm.addButton("Continue anyways", QtWidgets.QMessageBox.DestructiveRole)
            sm.addButton(f"Append ({self.current_encoder.video_extension}) for me", QtWidgets.QMessageBox.YesRole)
            sm.setStandardButtons(QtWidgets.QMessageBox.Close)
            for button in sm.buttons():
                if button.text().startswith("Append"):
                    button.setStyleSheet("background-color:green;")
                elif button.text().startswith("Continue"):
                    button.setStyleSheet("background-color:red;")
            sm.exec_()
            if sm.clickedButton().text().startswith("Append"):
                self.output_video_path_widget.setText(f"{self.output_video}.{self.current_encoder.video_extension}")
                self.output_video_path_widget.setDisabled(False)
                self.output_path_button.setDisabled(False)
            elif not sm.clickedButton().text().startswith("Continue"):
                return

        Path(self.temp_dir_name).mkdir(parents=True, exist_ok=True)

        out_file_path = Path(self.output_video)
        if out_file_path.exists() and out_file_path.stat().st_size > 0:
            sm = QtWidgets.QMessageBox()
            sm.setText("That output file already exists and is not empty!")
            sm.addButton("Cancel", QtWidgets.QMessageBox.DestructiveRole)
            sm.addButton("Overwrite", QtWidgets.QMessageBox.RejectRole)
            sm.exec_()
            if sm.clickedButton().text() == "Cancel":
                return

        if not self.build_commands():
            return

        self.widgets.convert_button.setText("⛔ Cancel")
        self.widgets.convert_button.setStyleSheet("background-color:red;")
        self.widgets.pause_resume.setDisabled(False)
        self.widgets.pause_resume.setStyleSheet("background-color:orange;")
        self.converting = True

        self.app.fastflix.queue.append(copy.deepcopy(self.app.fastflix.current_video))
        for command in self.app.fastflix.current_video.video_settings.conversion_commands:
            self.app.fastflix.worker_queue.put(("command", command.command, self.temp_dir_name, command.shell))
        self.disable_all()
        self.video_options.setCurrentWidget(self.video_options.status)

    @reusables.log_exception("fastflix", show_traceback=False)
    def conversion_complete(self, return_code):
        self.widgets.convert_button.setStyleSheet("background-color:green;")
        self.converting = False
        self.paused = False
        self.enable_all()
        self.widgets.convert_button.setText("Convert 🎥")
        self.widgets.pause_resume.setDisabled(True)
        self.widgets.pause_resume.setText("Pause")
        self.widgets.pause_resume.setStyleSheet("background-color:gray;")
        output = Path(self.output_video)

        if return_code or not output.exists() or output.stat().st_size <= 500:
            error_message("Could not encode video due to an error, please view the logs for more details!")
        else:
            sm = QtWidgets.QMessageBox()
            sm.setText("Encoded successfully, view now?")
            sm.addButton("View", QtWidgets.QMessageBox.YesRole)
            sm.setStandardButtons(QtWidgets.QMessageBox.Close)
            sm.exec_()
            if sm.clickedButton().text() == "View":
                QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(self.output_video))

    @reusables.log_exception("fastflix", show_traceback=False)
    def conversion_cancelled(self):
        self.widgets.convert_button.setStyleSheet("background-color:green;")
        self.converting = False
        self.paused = False
        self.enable_all()
        self.widgets.convert_button.setText("Convert 🎥")
        self.widgets.pause_resume.setDisabled(True)
        self.widgets.pause_resume.setText("Pause")
        self.widgets.pause_resume.setStyleSheet("background-color:gray;")

        sm = QtWidgets.QMessageBox()
        sm.setText("Conversion cancelled, delete incomplete file?")
        sm.addButton("Delete", QtWidgets.QMessageBox.YesRole)
        sm.addButton("Keep", QtWidgets.QMessageBox.NoRole)
        sm.exec_()
        if sm.clickedButton().text() == "Delete":
            try:
                os.remove(self.output_video)
            except OSError:
                pass

    @reusables.log_exception("fastflix", show_traceback=False)
    def dropEvent(self, event):
        if not event.mimeData().hasUrls:
            return event.ignore()

        event.setDropAction(QtCore.Qt.CopyAction)
        event.accept()
        try:
            self.input_video = Path(event.mimeData().urls()[0].toLocalFile())
        except (ValueError, IndexError):
            return event.ignore()
        else:
            self.video_path_widget.setText(str(self.input_video))
            self.output_video_path_widget.setText(self.generate_output_filename)
            self.output_video_path_widget.setDisabled(False)
            self.output_path_button.setDisabled(False)
            self.update_video_info()
            self.page_update()

    def dragEnterEvent(self, event):
        event.accept() if event.mimeData().hasUrls else event.ignore()

    def dragMoveEvent(self, event):
        event.accept() if event.mimeData().hasUrls else event.ignore()


class Notifier(QtCore.QThread):
    def __init__(self, parent, status_queue):
        super().__init__(parent)
        self.main = parent
        self.status_queue = status_queue

    def __del__(self):
        self.wait()

    def run(self):
        while True:
            status = self.status_queue.get()
            if status == "complete":
                self.main.completed.emit(0)
            if status == "error":
                self.main.completed.emit(1)
            elif status == "cancelled":
                self.main.cancelled.emit()
            elif status == "exit":
                self.main.close_event.emit()
                return
