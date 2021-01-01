#!/usr/bin/env python
# -*- coding: utf-8 -*-
import copy
import importlib.machinery  # Needed for pyinstaller
import logging
import math
import os
import secrets
import shutil
import time
from dataclasses import asdict, dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Tuple, Union

import pkg_resources
import reusables
from box import Box
from qtpy import QtCore, QtGui, QtWidgets

from fastflix.encoders.common import helpers
from fastflix.exceptions import FastFlixInternalException, FlixError
from fastflix.flix import (
    detect_interlaced,
    extract_attachments,
    generate_thumbnail_command,
    get_auto_crop,
    parse,
    parse_hdr_details,
)
from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.models.video import Status, Video, VideoSettings
from fastflix.resources import (
    black_x_icon,
    folder_icon,
    play_round_icon,
    profile_add_icon,
    settings_icon,
    video_add_icon,
    video_playlist_icon,
)
from fastflix.shared import error_message, time_to_number, yes_no_message
from fastflix.widgets.progress_bar import ProgressBar, Task
from fastflix.widgets.background_tasks import ThumbnailCreator, SubtitleFix
from fastflix.widgets.video_options import VideoOptions

logger = logging.getLogger("fastflix")

root = os.path.abspath(os.path.dirname(__file__))

only_int = QtGui.QIntValidator()


@dataclass
class CropWidgets:
    top: QtWidgets.QLineEdit = None
    bottom: QtWidgets.QLineEdit = None
    left: QtWidgets.QLineEdit = None
    right: QtWidgets.QLineEdit = None


@dataclass
class ScaleWidgets:
    width: QtWidgets.QLineEdit = None
    height: QtWidgets.QLineEdit = None
    keep_aspect: QtWidgets.QCheckBox = None


@dataclass
class MainWidgets:
    start_time: QtWidgets.QLineEdit = None
    end_time: QtWidgets.QLineEdit = None
    video_track: QtWidgets.QComboBox = None
    rotate: QtWidgets.QComboBox = None
    flip: QtWidgets.QComboBox = None
    crop: CropWidgets = field(default_factory=CropWidgets)
    scale: ScaleWidgets = field(default_factory=ScaleWidgets)
    remove_metadata: QtWidgets.QCheckBox = None
    chapters: QtWidgets.QCheckBox = None
    fast_time: QtWidgets.QComboBox = None
    preview: QtWidgets.QLabel = None
    convert_to: QtWidgets.QComboBox = None
    convert_button: QtWidgets.QPushButton = None
    deinterlace: QtWidgets.QCheckBox = None
    remove_hdr: QtWidgets.QCheckBox = None
    video_title: QtWidgets.QLineEdit = None
    profile_box: QtWidgets.QComboBox = None

    def items(self):
        for key in dir(self):
            if key.startswith("_"):
                continue
            if key in ("crop", "scale"):
                for sub_field in dir(getattr(self, key)):
                    if sub_field.startswith("_"):
                        continue
                    yield sub_field, getattr(getattr(self, key), sub_field)
            else:
                yield key, getattr(self, key)


class Main(QtWidgets.QWidget):
    completed = QtCore.Signal(int)
    thumbnail_complete = QtCore.Signal(int)
    cancelled = QtCore.Signal(str)
    close_event = QtCore.Signal()
    status_update_signal = QtCore.Signal(str)
    thread_logging_signal = QtCore.Signal(str)

    def __init__(self, parent, app: FastFlixApp):
        super().__init__(parent)
        self.app: FastFlixApp = app
        self.container = parent
        self.video: Video = Video(Path(), 0, 0, 0)

        self.initialized = False
        self.loading_video = True
        self.scale_updating = False

        self.notifier = Notifier(self, self.app, self.app.fastflix.status_queue)
        self.notifier.start()

        self.input_defaults = Box(scale=None, crop=None)
        self.initial_duration = 0

        self.temp_dir = self.get_temp_work_path()

        self.setAcceptDrops(True)

        self.input_video = None
        self.video_path_widget = QtWidgets.QLineEdit(t("No Source Selected"))
        self.output_video_path_widget = QtWidgets.QLineEdit("")
        self.output_video_path_widget.setDisabled(True)
        self.output_video_path_widget.textChanged.connect(lambda x: self.page_update(build_thumbnail=False))
        self.video_path_widget.setEnabled(False)

        self.widgets: MainWidgets = MainWidgets()

        self.buttons = []

        self.thumb_file = Path(self.app.fastflix.config.work_path, "thumbnail_preview.png")

        self.video_options = VideoOptions(
            self,
            app=self.app,
            available_audio_encoders=self.app.fastflix.audio_encoders,
        )

        self.completed.connect(self.conversion_complete)
        self.cancelled.connect(self.conversion_cancelled)
        self.close_event.connect(self.close)
        self.thumbnail_complete.connect(self.thumbnail_generated)
        self.status_update_signal.connect(self.status_update)
        self.thread_logging_signal.connect(self.thread_logger)
        self.encoding_worker = None
        self.command_runner = None
        self.converting = False
        self.side_data = Box()
        self.default_options = Box()

        self.grid = QtWidgets.QGridLayout()

        self.grid.addLayout(self.init_top_bar(), 0, 0, 1, 14)
        self.grid.addLayout(self.init_video_area(), 1, 0, 6, 6)
        self.grid.addLayout(self.init_scale_and_crop(), 1, 6, 5, 4)
        self.grid.addWidget(self.init_preview_image(), 1, 10, 5, 4, (QtCore.Qt.AlignTop | QtCore.Qt.AlignRight))

        spacer = QtWidgets.QLabel()
        spacer.setFixedHeight(5)
        self.grid.addWidget(spacer, 6, 0, 1, 14)
        self.grid.addWidget(self.video_options, 7, 0, 10, 14)

        self.grid.setSpacing(5)
        self.paused = False

        self.disable_all()
        self.setLayout(self.grid)
        self.set_profile()
        self.show()
        self.initialized = True
        self.last_page_update = time.time()

    def init_top_bar(self):
        top_bar = QtWidgets.QHBoxLayout()

        source = QtWidgets.QPushButton(QtGui.QIcon(video_add_icon), f"  {t('Source')}")
        source.setIconSize(QtCore.QSize(22, 20))
        source.setFixedHeight(40)
        source.setDefault(True)
        source.clicked.connect(lambda: self.open_file())

        queue = QtWidgets.QPushButton(QtGui.QIcon(video_playlist_icon), f"{t('Add to Queue')}  ")
        queue.setIconSize(QtCore.QSize(22, 20))
        queue.setFixedHeight(40)
        queue.setStyleSheet("padding: 0 10px;")
        queue.setLayoutDirection(QtCore.Qt.RightToLeft)
        queue.clicked.connect(lambda: self.add_to_queue())

        self.widgets.convert_button = QtWidgets.QPushButton(QtGui.QIcon(play_round_icon), f"{t('Convert')}  ")
        self.widgets.convert_button.setIconSize(QtCore.QSize(22, 20))
        self.widgets.convert_button.setFixedHeight(40)
        self.widgets.convert_button.setStyleSheet("padding: 0 10px;")
        self.widgets.convert_button.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.widgets.convert_button.clicked.connect(lambda: self.encode_video())

        self.widgets.profile_box = QtWidgets.QComboBox()
        self.widgets.profile_box.setStyleSheet("text-align: center;")
        self.widgets.profile_box.addItems(self.app.fastflix.config.profiles.keys())
        self.widgets.profile_box.setCurrentText(self.app.fastflix.config.selected_profile)
        self.widgets.profile_box.currentIndexChanged.connect(self.set_profile)
        self.widgets.profile_box.setMinimumWidth(150)
        self.widgets.profile_box.setFixedHeight(40)

        top_bar.addWidget(source)
        top_bar.addWidget(QtWidgets.QSplitter(QtCore.Qt.Horizontal))
        top_bar.addLayout(self.init_encoder_drop_down())
        top_bar.addWidget(QtWidgets.QSplitter(QtCore.Qt.Horizontal))
        top_bar.addWidget(self.widgets.profile_box)
        top_bar.addWidget(QtWidgets.QSplitter(QtCore.Qt.Horizontal))
        top_bar.addWidget(queue)
        top_bar.addWidget(self.widgets.convert_button)
        top_bar.addStretch(1)

        add_profile = QtWidgets.QPushButton(QtGui.QIcon(profile_add_icon), t("New Profile"))
        # add_profile.setFixedSize(QtCore.QSize(40, 40))
        add_profile.setFixedHeight(40)
        add_profile.setIconSize(QtCore.QSize(22, 22))
        add_profile.setToolTip(t("Profile"))
        add_profile.setLayoutDirection(QtCore.Qt.RightToLeft)
        add_profile.clicked.connect(lambda: self.container.new_profile())

        options = QtWidgets.QPushButton(QtGui.QIcon(settings_icon), "")
        options.setFixedSize(QtCore.QSize(40, 40))
        options.setIconSize(QtCore.QSize(22, 22))
        options.setToolTip(t("Settings"))
        options.clicked.connect(lambda: self.container.show_setting())

        top_bar.addWidget(add_profile)
        top_bar.addWidget(options)

        return top_bar

    def get_temp_work_path(self):
        new_temp = self.app.fastflix.config.work_path / f"temp_{secrets.token_hex(12)}"
        if new_temp.exists():
            return self.get_temp_work_path()
        new_temp.mkdir()
        return new_temp

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

    def config_update(self):
        self.thumb_file = Path(self.app.fastflix.config.work_path, "thumbnail_preview.png")
        self.change_output_types()
        self.page_update(build_thumbnail=True)

    def init_video_area(self):
        layout = QtWidgets.QVBoxLayout()
        spacer = QtWidgets.QLabel()
        spacer.setFixedHeight(2)
        layout.addWidget(spacer)
        # layout.addLayout(self.init_button_menu())
        # layout.addWidget(self.video_path_widget)
        # layout.addLayout(self.init_encoder_drop_down())

        output_layout = QtWidgets.QHBoxLayout()

        output_label = QtWidgets.QLabel(t("Output"))
        output_label.setFixedWidth(70)
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_video_path_widget, stretch=True)
        self.output_path_button = QtWidgets.QPushButton(icon=QtGui.QIcon(folder_icon))
        self.output_path_button.clicked.connect(lambda: self.save_file())
        self.output_path_button.setDisabled(True)

        output_layout.addWidget(self.output_path_button)
        layout.addLayout(output_layout)

        layout.addLayout(self.init_video_track_select())

        title_layout = QtWidgets.QHBoxLayout()

        title_label = QtWidgets.QLabel(t("Title"))
        title_label.setFixedWidth(70)
        title_label.setToolTip(t('Set the "title" tag, sometimes shown as "Movie Name"'))
        self.widgets.video_title = QtWidgets.QLineEdit()
        self.widgets.video_title.setToolTip(t('Set the "title" tag, sometimes shown as "Movie Name"'))
        self.widgets.video_title.textChanged.connect(lambda: self.page_update(build_thumbnail=False))

        title_layout.addWidget(title_label)
        title_layout.addWidget(self.widgets.video_title)

        layout.addLayout(title_layout)

        transform_layout = QtWidgets.QHBoxLayout()
        transform_layout.addWidget(self.init_rotate(), stretch=True)
        transform_layout.addWidget(self.init_flip(), stretch=True)

        metadata_layout = QtWidgets.QVBoxLayout()
        self.widgets.remove_metadata = QtWidgets.QCheckBox(t("Remove Metadata"))
        self.widgets.remove_metadata.setChecked(True)
        self.widgets.remove_metadata.toggled.connect(self.page_update)
        self.widgets.remove_metadata.setToolTip(
            t("Scrub away all incoming metadata, like video titles, unique markings and so on.")
        )
        self.widgets.chapters = QtWidgets.QCheckBox(t("Copy Chapters"))
        self.widgets.chapters.setChecked(True)
        self.widgets.chapters.toggled.connect(self.page_update)
        self.widgets.chapters.setToolTip(t("Copy the chapter markers as is from incoming source."))

        metadata_layout.addWidget(self.widgets.remove_metadata)
        metadata_layout.addWidget(self.widgets.chapters)

        transform_layout.addLayout(metadata_layout)

        self.widgets.deinterlace = QtWidgets.QCheckBox(t("Deinterlace"))
        self.widgets.deinterlace.setChecked(False)
        self.widgets.deinterlace.toggled.connect(self.interlace_update)
        self.widgets.deinterlace.setToolTip(
            f'{t("Enables the yadif filter.")}\n' f'{t("Automatically enabled when an interlaced video is detected")}'
        )

        self.widgets.remove_hdr = QtWidgets.QCheckBox(t("Remove HDR"))
        self.widgets.remove_hdr.setChecked(False)
        self.widgets.remove_hdr.toggled.connect(self.encoder_settings_update)
        self.widgets.remove_hdr.setToolTip(
            f"{t('Convert BT2020 colorspace into bt709')}\n"
            f"{t('WARNING: This will take much longer and result in a larger file')}"
        )

        extra_details_layout = QtWidgets.QVBoxLayout()
        extra_details_layout.addWidget(self.widgets.deinterlace)
        extra_details_layout.addWidget(self.widgets.remove_hdr)

        transform_layout.addLayout(extra_details_layout)

        layout.addLayout(transform_layout)
        layout.addWidget(self.init_start_time())

        layout.addStretch()
        return layout

    def init_scale_and_crop(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.init_scale())
        layout.addWidget(self.init_crop())
        layout.addStretch()
        return layout

    def init_video_track_select(self):
        layout = QtWidgets.QHBoxLayout()
        self.widgets.video_track = QtWidgets.QComboBox()
        self.widgets.video_track.addItems([])
        self.widgets.video_track.currentIndexChanged.connect(lambda: self.page_update())

        track_label = QtWidgets.QLabel(t("Video Track"))
        track_label.setFixedWidth(65)
        layout.addWidget(track_label)
        layout.addWidget(self.widgets.video_track, stretch=1)
        layout.setSpacing(10)
        return layout

    def set_profile(self):
        if self.loading_video:
            return
        # self.video_options.new_source()
        # previous_auto_crop = self.app.fastflix.config.opt("auto_crop")
        self.app.fastflix.config.selected_profile = self.widgets.profile_box.currentText()
        self.app.fastflix.config.save()
        self.widgets.convert_to.setCurrentText(f"   {self.app.fastflix.config.opt('encoder')}")
        if self.app.fastflix.config.opt("auto_crop") and not self.build_crop():
            self.get_auto_crop()
        self.loading_video = True
        self.widgets.scale.keep_aspect.setChecked(self.app.fastflix.config.opt("keep_aspect_ratio"))
        self.widgets.rotate.setCurrentIndex(self.app.fastflix.config.opt("rotate") or 0 // 90)

        v_flip = self.app.fastflix.config.opt("vertical_flip")
        h_flip = self.app.fastflix.config.opt("horizontal_flip")

        self.widgets.flip.setCurrentIndex(self.flip_to_int(v_flip, h_flip))
        self.video_options.change_conversion(self.app.fastflix.config.opt("encoder"))
        self.video_options.update_profile()
        if self.app.fastflix.current_video:
            self.video_options.new_source()
        # Hack to prevent a lot of thumbnail generation
        self.loading_video = False
        self.page_update()

    def save_profile(self):
        self.video_options.get_settings()

    def init_flip(self):
        self.widgets.flip = QtWidgets.QComboBox()
        rotation_folder = "../data/rotations/FastFlix"

        no_rot_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder}.png")).resolve())
        vert_flip_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder} VF.png")).resolve())
        hoz_flip_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder} HF.png")).resolve())
        rot_180_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder} 180.png")).resolve())

        self.widgets.flip.addItems([t("No Flip"), t("Vertical Flip"), t("Horizontal Flip"), t("Vert + Hoz Flip")])
        self.widgets.flip.setItemIcon(0, QtGui.QIcon(no_rot_file))
        self.widgets.flip.setItemIcon(1, QtGui.QIcon(vert_flip_file))
        self.widgets.flip.setItemIcon(2, QtGui.QIcon(hoz_flip_file))
        self.widgets.flip.setItemIcon(3, QtGui.QIcon(rot_180_file))
        self.widgets.flip.setIconSize(QtCore.QSize(35, 35))
        self.widgets.flip.currentIndexChanged.connect(lambda: self.page_update())
        self.widgets.flip.setFixedWidth(130)
        return self.widgets.flip

    def get_flips(self) -> Tuple[bool, bool]:
        mapping = {0: (False, False), 1: (True, False), 2: (False, True), 3: (True, True)}
        return mapping[self.widgets.flip.currentIndex()]

    def flip_to_int(self, vertical_flip: bool, horizontal_flip: bool) -> int:
        mapping = {(False, False): 0, (True, False): 1, (False, True): 2, (True, True): 3}
        return mapping[(vertical_flip, horizontal_flip)]

    def init_rotate(self):
        self.widgets.rotate = QtWidgets.QComboBox()
        rotation_folder = "../data/rotations/FastFlix"

        no_rot_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder}.png")).resolve())
        rot_90_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder} C90.png")).resolve())
        rot_270_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder} CC90.png")).resolve())
        rot_180_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder} 180.png")).resolve())

        self.widgets.rotate.addItems([t("No Rotation"), "90°", "180°", "270°"])
        self.widgets.rotate.setItemIcon(0, QtGui.QIcon(no_rot_file))
        self.widgets.rotate.setItemIcon(1, QtGui.QIcon(rot_90_file))
        self.widgets.rotate.setItemIcon(2, QtGui.QIcon(rot_180_file))
        self.widgets.rotate.setItemIcon(3, QtGui.QIcon(rot_270_file))
        self.widgets.rotate.setIconSize(QtCore.QSize(35, 35))
        self.widgets.rotate.currentIndexChanged.connect(lambda: self.page_update())
        self.widgets.rotate.setFixedWidth(140)

        return self.widgets.rotate

    def rotation_to_transpose(self):
        mapping = {0: None, 1: 1, 2: 4, 3: 2}
        return mapping[self.widgets.rotate.currentIndex()]

    def transpose_to_rotation(self, transpose):
        mapping = {None: 0, 1: 1, 4: 2, 2: 3}
        return mapping[int(transpose) if transpose else None]

    def change_output_types(self):
        self.widgets.convert_to.clear()
        self.widgets.convert_to.addItems([f"   {x}" for x in self.app.fastflix.encoders.keys()])
        for i, plugin in enumerate(self.app.fastflix.encoders.values()):
            if getattr(plugin, "icon", False):
                self.widgets.convert_to.setItemIcon(i, QtGui.QIcon(plugin.icon))
        self.widgets.convert_to.setFont(QtGui.QFont("helvetica", 10, weight=57))
        self.widgets.convert_to.setIconSize(QtCore.QSize(40, 40))

    def init_encoder_drop_down(self):
        layout = QtWidgets.QHBoxLayout()
        self.widgets.convert_to = QtWidgets.QComboBox()
        self.change_output_types()
        self.widgets.convert_to.currentTextChanged.connect(self.change_encoder)

        encoder_label = QtWidgets.QLabel(f"{t('Encoder')}: ")
        encoder_label.setFixedWidth(65)
        layout.addWidget(self.widgets.convert_to, stretch=0)
        layout.setSpacing(10)

        return layout

    def change_encoder(self):
        if not self.initialized or not self.app.fastflix.current_video or not self.convert_to:
            return
        self.video_options.change_conversion(self.convert_to)
        if not self.output_video_path_widget.text().endswith(self.current_encoder.video_extension):
            # Make sure it's using the right file extension
            self.output_video_path_widget.setText(self.generate_output_filename)

    @property
    def current_encoder(self):
        try:
            return self.app.fastflix.encoders[
                self.app.fastflix.current_video.video_settings.video_encoder_settings.name
            ]
        except AttributeError:
            return self.app.fastflix.encoders[self.convert_to]

    def init_start_time(self):
        group_box = QtWidgets.QGroupBox()
        group_box.setStyleSheet("QGroupBox{padding-top:18px; margin-top:-18px}")
        self.widgets.start_time, layout = self.build_hoz_int_field(
            f"{t('Start')}  ", right_stretch=False, left_stretch=True, time_field=True
        )
        self.widgets.end_time, layout = self.build_hoz_int_field(
            f"  {t('End')}  ", left_stretch=True, right_stretch=True, layout=layout, time_field=True
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
        self.widgets.fast_time.setFixedWidth(75)
        layout.addWidget(QtWidgets.QLabel(" "))
        layout.addWidget(self.widgets.fast_time, QtCore.Qt.AlignRight)
        group_box.setLayout(layout)
        return group_box

    def init_scale(self):
        scale_area = QtWidgets.QGroupBox(self)
        scale_area.setFont(self.app.font())
        scale_area.setStyleSheet("QGroupBox{padding-top:15px; margin-top:-18px}")
        scale_layout = QtWidgets.QVBoxLayout()

        self.widgets.scale.width, new_scale_layout = self.build_hoz_int_field(f"{t('Width')}  ", right_stretch=False)
        self.widgets.scale.height, new_scale_layout, lb, rb = self.build_hoz_int_field(
            f"  {t('Height')}  ", left_stretch=False, layout=new_scale_layout, return_buttons=True
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
        self.widgets.scale.keep_aspect = QtWidgets.QCheckBox(t("Keep aspect ratio"))
        self.widgets.scale.keep_aspect.setMaximumHeight(40)
        self.widgets.scale.keep_aspect.setChecked(True)
        self.widgets.scale.keep_aspect.toggled.connect(lambda: self.toggle_disable((self.widgets.scale.height, lb, rb)))
        self.widgets.scale.keep_aspect.toggled.connect(lambda: self.keep_aspect_update())

        label = QtWidgets.QLabel(t("Scale"), alignment=(QtCore.Qt.AlignBottom | QtCore.Qt.AlignRight))
        label.setStyleSheet("QLabel{color:#777}")
        label.setMaximumHeight(40)
        bottom_row.addWidget(self.widgets.scale.keep_aspect, alignment=QtCore.Qt.AlignCenter)

        scale_layout.addLayout(new_scale_layout)
        bottom_row.addWidget(label)
        scale_layout.addLayout(bottom_row)

        scale_area.setLayout(scale_layout)

        return scale_area

    def init_crop(self):
        crop_box = QtWidgets.QGroupBox()
        crop_box.setStyleSheet("QGroupBox{padding-top:17px; margin-top:-18px}")
        crop_layout = QtWidgets.QVBoxLayout()
        self.widgets.crop.top, crop_top_layout = self.build_hoz_int_field(f"       {t('Top')}  ")
        self.widgets.crop.left, crop_hz_layout = self.build_hoz_int_field(f"{t('Left')}  ", right_stretch=False)
        self.widgets.crop.right, crop_hz_layout = self.build_hoz_int_field(
            f"    {t('Right')}  ", left_stretch=False, layout=crop_hz_layout
        )
        self.widgets.crop.bottom, crop_bottom_layout = self.build_hoz_int_field(f"{t('Bottom')}  ", right_stretch=True)

        self.widgets.crop.top.textChanged.connect(lambda: self.page_update())
        self.widgets.crop.left.textChanged.connect(lambda: self.page_update())
        self.widgets.crop.right.textChanged.connect(lambda: self.page_update())
        self.widgets.crop.bottom.textChanged.connect(lambda: self.page_update())

        label = QtWidgets.QLabel(t("Crop"), alignment=(QtCore.Qt.AlignBottom | QtCore.Qt.AlignRight))
        label.setStyleSheet("QLabel{color:#777}")
        label.setMaximumHeight(40)

        auto_crop = QtWidgets.QPushButton(t("Auto"))
        auto_crop.setMaximumHeight(40)
        auto_crop.setFixedWidth(50)
        auto_crop.setToolTip(t("Automatically detect black borders"))
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
        self.widgets.preview.setFixedSize(320, 190)
        self.widgets.preview.setAlignment(QtCore.Qt.AlignCenter)
        self.widgets.preview.setStyleSheet("border: 2px solid #dddddd;")  # background-color:#f0f0f0

        # buttons = self.init_preview_buttons()

        return self.widgets.preview

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
            modifier = getattr(self.current_encoder, "video_dimension_divisor", 1)
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
            return f"{self.input_video.parent / self.input_video.stem}-fastflix-{secrets.token_hex(2)}.{self.current_encoder.video_extension}"
        return f"{Path('~').expanduser()}{os.sep}fastflix-{secrets.token_hex(2)}.{self.current_encoder.video_extension}"

    @property
    def output_video(self):
        return self.output_video_path_widget.text()

    @reusables.log_exception("fastflix", show_traceback=False)
    def save_file(self, extension="mkv"):
        filename = QtWidgets.QFileDialog.getSaveFileName(
            self, caption="Save Video As", directory=self.generate_output_filename, filter=f"Save File (*.{extension})"
        )
        if filename and filename[0]:
            self.output_video_path_widget.setText(filename[0])

    def get_auto_crop(self):
        if not self.input_video or not self.initialized or self.loading_video:
            return

        start_pos = self.start_time or self.app.fastflix.current_video.duration // 10

        blocks = math.ceil((self.app.fastflix.current_video.duration - start_pos) / 5)

        times = [
            x
            for x in range(int(start_pos), int(self.app.fastflix.current_video.duration), blocks)
            if x < self.app.fastflix.current_video.duration
        ][:4]

        self.app.processEvents()
        result_list = []
        tasks = [
            Task(
                f"{t('Auto Crop - Finding black bars at')} {self.number_to_time(x)}",
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

        r, b, l, tp = selected

        if tp + b > self.app.fastflix.current_video.height * 0.9 or r + l > self.app.fastflix.current_video.width * 0.9:
            logger.warning(
                f"{t('Autocrop tried to crop too much')}"
                f" ({t('left')} {l}, {t('top')} {tp}, {t('right')} {r}, {t('bottom')} {b}), {t('ignoring')}"
            )
            return

        # Hack to stop thumb gen
        self.loading_video = True
        self.widgets.crop.top.setText(str(tp))
        self.widgets.crop.left.setText(str(l))
        self.widgets.crop.right.setText(str(r))
        self.loading_video = False
        self.widgets.crop.bottom.setText(str(b))

    def build_crop(self) -> Union[str, None]:
        if not self.initialized or not self.app.fastflix.current_video:
            return None
        try:
            top = int(self.widgets.crop.top.text())
            left = int(self.widgets.crop.left.text())
            right = int(self.widgets.crop.right.text())
            bottom = int(self.widgets.crop.bottom.text())
        except (ValueError, AttributeError):
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
                    self.widgets.scale.height.setText("-8")
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
        if self.scale_updating or self.loading_video:
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
            # TODO add better colors / way
            # self.widgets.scale.width.setStyleSheet("background-color: red;")
            self.widgets.scale.width.setToolTip(
                f"{t('Width must be divisible by 2 - Source width')}: {self.app.fastflix.current_video.width}"
            )
            return logger.warning(t("Width must be divisible by 2"))
            # return self.scale_warning_message.setText("Width must be divisible by 8")
        else:
            self.widgets.scale.width.setToolTip(f"{t('Source width')}: {self.app.fastflix.current_video.width}")

        if keep_aspect:
            self.widgets.scale.height.setText("Auto")
            # self.widgets.scale.width.setStyleSheet("background-color: white;")
            # self.widgets.scale.height.setStyleSheet("background-color: white;")
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
            scale_height = -8 if scale_height == "Auto" else int(scale_height)
            assert scale_height == -8 or scale_height > 0
        except (ValueError, AssertionError):
            self.scale_updating = False
            return logger.warning(t("Invalid height"))
            # return self.scale_warning_message.setText("Invalid height")

        if scale_height != -8 and scale_height % 2:
            # self.widgets.scale.height.setStyleSheet("background-color: red;")
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
        # self.widgets.scale.width.setStyleSheet("background-color: white;")
        # self.widgets.scale.height.setStyleSheet("background-color: white;")
        self.page_update()
        self.scale_updating = False

    def clear_current_video(self):
        self.loading_video = True
        self.app.fastflix.current_video = None
        self.input_video = None
        self.video_path_widget.setText(t("No Source Selected"))
        self.output_video_path_widget.setText("")
        self.output_path_button.setDisabled(True)
        self.output_video_path_widget.setDisabled(True)
        for i in range(self.widgets.video_track.count()):
            self.widgets.video_track.removeItem(0)
        self.widgets.preview.setText(t("No Video File"))

        self.widgets.deinterlace.setChecked(False)
        self.widgets.remove_hdr.setChecked(False)
        self.widgets.remove_metadata.setChecked(True)
        self.widgets.chapters.setChecked(True)

        self.widgets.flip.setCurrentIndex(0)
        self.widgets.rotate.setCurrentIndex(0)
        self.widgets.video_title.setText("")

        self.widgets.crop.top.setText("0")
        self.widgets.crop.left.setText("0")
        self.widgets.crop.right.setText("0")
        self.widgets.crop.bottom.setText("0")
        self.widgets.start_time.setText(self.number_to_time(0))
        self.widgets.end_time.setText(self.number_to_time(0))
        self.widgets.scale.width.setText("0")
        self.widgets.scale.height.setText("Auto")
        self.widgets.preview.setPixmap(QtGui.QPixmap())
        self.video_options.clear_tracks()
        self.disable_all()
        self.loading_video = False

    @reusables.log_exception("fastflix", show_traceback=True)
    def reload_video_from_queue(self, video: Video):
        self.loading_video = True

        self.app.fastflix.current_video = video
        self.input_video = video.source

        text_video_tracks = [
            f'{x.index}: {t("codec")} {x.codec_name} - {x.get("pix_fmt")} - {t("profile")} {x.get("profile")}'
            for x in self.app.fastflix.current_video.streams.video
        ]
        self.widgets.video_track.clear()
        self.widgets.video_track.addItems(text_video_tracks)

        if self.app.fastflix.current_video.video_settings.crop:
            width, height, left, top = self.app.fastflix.current_video.video_settings.crop.split(":")
            right = str(self.app.fastflix.current_video.width - (int(width) + int(left)))
            bottom = str(self.app.fastflix.current_video.height - (int(height) + int(top)))
        else:
            top, left, right, bottom = "0", "0", "0", "0"

        end_time = self.app.fastflix.current_video.video_settings.end_time or video.duration

        self.widgets.crop.top.setText(top)
        self.widgets.crop.left.setText(left)
        self.widgets.crop.right.setText(right)
        self.widgets.crop.bottom.setText(bottom)
        self.widgets.start_time.setText(self.number_to_time(video.video_settings.start_time))
        self.widgets.end_time.setText(self.number_to_time(end_time))
        self.widgets.video_title.setText(self.app.fastflix.current_video.video_settings.video_title)
        self.output_video_path_widget.setText(str(video.video_settings.output_path))
        self.widgets.deinterlace.setChecked(self.app.fastflix.current_video.video_settings.deinterlace)
        self.widgets.remove_metadata.setChecked(self.app.fastflix.current_video.video_settings.remove_metadata)
        self.widgets.chapters.setChecked(self.app.fastflix.current_video.video_settings.copy_chapters)
        self.widgets.remove_hdr.setChecked(self.app.fastflix.current_video.video_settings.remove_hdr)
        self.widgets.rotate.setCurrentIndex(self.transpose_to_rotation(video.video_settings.rotate))
        self.widgets.fast_time.setCurrentIndex(0 if video.video_settings.fast_seek else 1)

        if video.video_settings.vertical_flip:
            self.widgets.flip.setCurrentIndex(1)
        if video.video_settings.horizontal_flip:
            self.widgets.flip.setCurrentIndex(2)
        if video.video_settings.vertical_flip and video.video_settings.horizontal_flip:
            self.widgets.flip.setCurrentIndex(3)

        if self.app.fastflix.current_video.video_settings.scale:
            w, h = self.app.fastflix.current_video.video_settings.scale.split(":")

            self.widgets.scale.width.setText(w)
            if h.startswith("-"):
                self.widgets.scale.height.setText("Auto")
                self.widgets.scale.keep_aspect.setChecked(True)
            else:
                self.widgets.scale.height.setText(h)
        else:
            self.widgets.scale.width.setText(str(self.app.fastflix.current_video.width))
            self.widgets.scale.height.setText("Auto")
            self.widgets.scale.keep_aspect.setChecked(True)

        self.video_options.reload()
        self.enable_all()

        self.app.fastflix.current_video.status = Status()

        self.loading_video = False
        self.page_update()

    @reusables.log_exception("fastflix", show_traceback=False)
    def update_video_info(self):
        self.loading_video = True
        self.app.fastflix.current_video = Video(source=self.input_video, work_path=self.get_temp_work_path())
        tasks = [
            Task(t("Parse Video details"), parse),
            Task(t("Extract covers"), extract_attachments),
            Task(t("Determine HDR details"), parse_hdr_details),
            Task(t("Detecting Interlace"), detect_interlaced, dict(source=self.input_video)),
        ]

        try:
            ProgressBar(self.app, tasks)
        except FlixError:
            error_message(f"{t('Not a video file')}<br>{self.input_video}")
            self.clear_current_video()
            return

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
                + (self.app.fastflix.current_video.width % self.current_encoder.video_dimension_divisor)
            )
        )
        self.widgets.scale.width.setToolTip(f"{t('Source width')}: {self.app.fastflix.current_video.width}")
        self.widgets.scale.height.setText(
            str(
                self.app.fastflix.current_video.height
                + (self.app.fastflix.current_video.height % self.current_encoder.video_dimension_divisor)
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

        self.widgets.deinterlace.setChecked(self.app.fastflix.current_video.video_settings.deinterlace)

        self.video_options.new_source()
        self.enable_all()
        # self.widgets.convert_button.setDisabled(False)
        # self.widgets.convert_button.setStyleSheet("background-color:green;")
        self.loading_video = False
        if self.app.fastflix.config.opt("auto_crop"):
            self.get_auto_crop()

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
        return str(timedelta(seconds=round(number, 2)))[:10]

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

    @property
    def remove_hdr(self) -> bool:
        return self.widgets.remove_hdr.isChecked()

    @reusables.log_exception("fastflix", show_traceback=False)
    def generate_thumbnail(self):
        if not self.input_video or self.loading_video:
            return

        settings = asdict(self.app.fastflix.current_video.video_settings)

        if (
            self.app.fastflix.current_video.video_settings.video_encoder_settings.pix_fmt == "yuv420p10le"
            and self.app.fastflix.current_video.color_space.startswith("bt2020")
        ):
            settings["remove_hdr"] = True

        custom_filters = "scale='min(320\\,iw):-8'"
        if self.app.fastflix.current_video.color_transfer == "arib-std-b67":
            custom_filters += ",select=eq(pict_type\\,I)"

        filters = helpers.generate_filters(custom_filters=custom_filters, **settings)

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

    @staticmethod
    def thread_logger(text):
        try:
            level, message = text.split(":", 1)
            logger.log(["", "debug", "info", "warning", "error", "critical"].index(level.lower()) * 10, message)
        except Exception:
            logger.warning(text)

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
            height = -8
        return f"{width}:{height}"

    def get_all_settings(self):
        if not self.initialized:
            return
        stream_info = self.app.fastflix.current_video.streams.video[self.video_track]

        end_time = self.end_time
        if self.end_time == float(self.app.fastflix.current_video.format.get("duration", 0)):
            end_time = 0
        if self.end_time and self.end_time - 0.1 <= self.app.fastflix.current_video.duration <= self.end_time + 0.1:
            end_time = 0

        scale = self.build_scale()
        if scale in (
            f"{stream_info.width}:-8",
            f"-8:{stream_info.height}",
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
            fast_seek=self.fast_time,
            rotate=self.rotation_to_transpose(),
            vertical_flip=v_flip,
            horizontal_flip=h_flip,
            output_path=Path(self.output_video),
            deinterlace=self.widgets.deinterlace.isChecked(),
            remove_metadata=self.remove_metadata,
            copy_chapters=self.copy_chapters,
            video_title=self.title,
            remove_hdr=self.remove_hdr,
        )

        self.video_options.get_settings()

    def build_commands(self) -> bool:
        if (
            not self.initialized
            or not self.app.fastflix.current_video
            or not self.app.fastflix.current_video.streams
            or self.loading_video
        ):
            return False
        try:
            self.get_all_settings()
        except FastFlixInternalException as err:
            error_message(str(err))
            return False

        commands = self.current_encoder.build(fastflix=self.app.fastflix)
        if not commands:
            return False
        self.video_options.commands.update_commands(commands)
        self.app.fastflix.current_video.video_settings.conversion_commands = commands
        return True

    def interlace_update(self):
        if self.loading_video:
            return
        deinterlace = self.widgets.deinterlace.isChecked()
        if not deinterlace and self.app.fastflix.current_video.interlaced:
            error_message(
                f"{t('This video has been detected to have an interlaced video.')}\n"
                f"{t('Not deinterlacing will result in banding after encoding.')}",
                title="Warning",
            )
        self.page_update()

    def encoder_settings_update(self):
        self.video_options.settings_update()

    def page_update(self, build_thumbnail=True):
        if not self.initialized or self.loading_video or not self.app.fastflix.current_video:
            return
        self.last_page_update = time.time()
        self.video_options.refresh()
        self.build_commands()
        if build_thumbnail:
            self.generate_thumbnail()

    def close(self, no_cleanup=False, from_container=False):
        if not no_cleanup:
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            except Exception:
                pass
        self.video_options.cleanup()
        self.notifier.terminate()
        super().close()
        if not from_container:
            self.container.close()

    @property
    def convert_to(self):
        if self.widgets.convert_to:
            return self.widgets.convert_to.currentText().strip()
        return list(self.app.fastflix.encoders.keys())[0]

    # @property
    # def current_encoder(self):
    #     return self.app.fastflix.encoders[self.convert_to]

    def encoding_checks(self):
        if not self.input_video:
            error_message(t("Have to select a video first"))
            return False
        if not self.output_video:
            error_message(t("Please specify output video"))
            return False
        if self.input_video.resolve().absolute() == Path(self.output_video).resolve().absolute():
            error_message(t("Output video path is same as source!"))
            return False

        if not self.output_video.lower().endswith(self.current_encoder.video_extension):
            sm = QtWidgets.QMessageBox()
            sm.setText(
                f"{t('Output video file does not have expected extension')} ({self.current_encoder.video_extension}), "
                f"{t('which can case issues')}."
            )
            # TODO translate
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
                return False

        out_file_path = Path(self.output_video)
        if out_file_path.exists() and out_file_path.stat().st_size > 0:
            sm = QtWidgets.QMessageBox()
            sm.setText("That output file already exists and is not empty!")
            sm.addButton("Cancel", QtWidgets.QMessageBox.DestructiveRole)
            sm.addButton("Overwrite", QtWidgets.QMessageBox.RejectRole)
            sm.exec_()
            if sm.clickedButton().text() == "Cancel":
                return False
        return True

    def set_convert_button(self, convert=True):
        if convert:
            self.widgets.convert_button.setText(f"{t('Convert')}  ")
            self.widgets.convert_button.setIcon(QtGui.QIcon(play_round_icon))
            self.widgets.convert_button.setIconSize(QtCore.QSize(22, 20))

        else:
            self.widgets.convert_button.setText(f"{t('Cancel')}  ")
            self.widgets.convert_button.setIcon(QtGui.QIcon(black_x_icon))
            self.widgets.convert_button.setIconSize(QtCore.QSize(22, 20))

    @reusables.log_exception("fastflix", show_traceback=False)
    def encode_video(self):

        if self.converting:
            logger.debug(t("Canceling current encode"))
            self.app.fastflix.worker_queue.put(["cancel"])
            self.video_options.queue.reset_pause_encode()
            return
        else:
            logger.debug(t("Starting conversion process"))

        if not self.app.fastflix.queue or self.app.fastflix.current_video:
            add_current = True
            if self.app.fastflix.queue and self.app.fastflix.current_video:
                add_current = yes_no_message("Add current video to queue?", yes_text="Yes", no_text="No")
            if add_current:
                if not self.add_to_queue():
                    return

        # Command looks like (video_uuid, command_uuid, command, work_dir, filename)
        # Request looks like (queue command, log_dir, (commands))
        requests = ["add_items", str(self.app.fastflix.log_path)]
        commands = self.get_commands()

        if not commands:
            return error_message(t("No new items in queue to convert"))

        requests.append(tuple(commands))

        self.converting = True
        self.set_convert_button(False)
        self.app.fastflix.worker_queue.put(tuple(requests))
        self.disable_all()
        self.video_options.show_status()

    def get_commands(self):
        commands = []
        for video in self.app.fastflix.queue:
            if video.status.complete or video.status.error:
                continue
            for command in video.video_settings.conversion_commands:
                commands.append(
                    (
                        video.uuid,
                        command.uuid,
                        command.command,
                        str(video.work_path),
                        str(video.video_settings.output_path.stem),
                    )
                )
        return commands

    def add_to_queue(self):
        if not self.encoding_checks():
            return False

        if not self.build_commands():
            return False

        source_in_queue = False
        for video in self.app.fastflix.queue:
            if video.status.complete:
                continue
            if self.app.fastflix.current_video.source == video.source:
                source_in_queue = True
            if self.app.fastflix.current_video.video_settings.output_path == video.video_settings.output_path:
                error_message(f"{video.video_settings.output_path} {t('out file is already in queue')}")
                return False

        # if source_in_queue:
        # TODO ask if ok
        # return

        video = self.app.fastflix.current_video

        self.app.fastflix.queue.append(copy.deepcopy(video))
        self.video_options.update_queue()
        self.video_options.show_queue()

        if self.converting:
            commands = self.get_commands()
            requests = ["add_items", str(self.app.fastflix.log_path), tuple(commands)]
            self.app.fastflix.worker_queue.put(tuple(requests))

        self.clear_current_video()
        return True

    @reusables.log_exception("fastflix", show_traceback=False)
    def conversion_complete(self, return_code):
        self.converting = False
        self.paused = False
        self.set_convert_button()

        if return_code:
            error_message(t("There was an error during conversion and the queue has stopped"), title=t("Error"))
        else:
            self.video_options.show_queue()
            error_message(t("All queue items have completed"), title=t("Success"))

    @reusables.log_exception("fastflix", show_traceback=False)
    def conversion_cancelled(self, data):
        self.converting = False
        self.paused = False
        self.set_convert_button()

        try:
            video_uuid, command_uuid = data.split(":")
            cancelled_video = self.find_video(video_uuid)
        except Exception:
            return

        sm = QtWidgets.QMessageBox()
        sm.setWindowTitle(t("Cancelled"))
        sm.setText(
            f"{t('Conversion cancelled, delete incomplete file')}\n" f"{cancelled_video.video_settings.output_path}?"
        )
        sm.addButton(t("Delete"), QtWidgets.QMessageBox.YesRole)
        sm.addButton(t("Keep"), QtWidgets.QMessageBox.NoRole)
        sm.exec_()
        if sm.clickedButton().text() == t("Delete"):
            try:
                video_uuid, command_uuid = data.split(":")
                cancelled_video = self.find_video(video_uuid)
                cancelled_video.video_settings.output_path.unlink(missing_ok=True)
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
        event.accept() if event.mimeData().hasUrls else event.ignoreAF()

    def status_update(self, status):
        logger.debug(f"Updating status from command worker: {status}")
        try:
            command, video_uuid, command_uuid = status.split(":")
        except ValueError:
            logger.exception(f"Could not process status update from the command worker: {status}")
            return

        try:
            video = self.find_video(video_uuid)
            command_index = self.find_command(video, command_uuid)
        except FlixError as err:
            logger.error(f"Could not update queue status due to not found video/command - {err}")
            return

        if command == "converted":
            if command_index == len(video.video_settings.conversion_commands):
                video.status.complete = True
                video.status.success = True
                video.status.running = False
                if video.video_settings.subtitle_tracks and not video.video_settings.subtitle_tracks[0].disposition:
                    if mkv_prop_edit := shutil.which("mkvpropedit"):
                        worker = SubtitleFix(self, mkv_prop_edit, video.video_settings.output_path)
                        worker.start()
                self.video_options.update_queue()
            else:
                logger.error(f"This should not happen? {status} - {video}")

        elif command == "running":
            video.status.current_command = command_index
            video.status.running = True
            self.video_options.update_queue(currently_encoding=True)

        elif command == "error":
            video.status.error = True
            video.status.running = False
            self.video_options.update_queue()

        elif command == "cancelled":
            video.status.cancelled = True
            video.status.running = False
            self.video_options.update_queue()

        elif command in ("paused encode", "resumed encode"):
            pass
        else:
            logger.warning(f"status worker received unknown command: {command}")

    def find_video(self, uuid) -> Video:
        for video in self.app.fastflix.queue:
            if uuid == video.uuid:
                return video
        raise FlixError(f'{t("No video found for")} {uuid}')

    def find_command(self, video: Video, uuid) -> int:
        for i, command in enumerate(video.video_settings.conversion_commands, start=1):
            if uuid == command.uuid:
                return i
        raise FlixError(f'{t("No command found for")} {uuid}')


class Notifier(QtCore.QThread):
    def __init__(self, parent, app, status_queue):
        super().__init__(parent)
        self.app = app
        self.main: Main = parent
        self.status_queue = status_queue

    def __del__(self):
        self.wait()

    def run(self):
        while True:
            # Message looks like (command, video_uuid, command_uuid)
            status = self.status_queue.get()
            if status[0] == "complete":
                self.main.completed.emit(0)
            elif status[0] == "error":
                self.main.status_update_signal.emit(":".join(status))
                self.main.completed.emit(1)
            elif status[0] == "cancelled":
                self.main.cancelled.emit(":".join(status[1:]))
                self.main.status_update_signal.emit(":".join(status))
            elif status[0] == "exit":
                try:
                    self.terminate()
                finally:
                    self.main.close_event.emit()
                return
            else:
                self.main.status_update_signal.emit(":".join(status))
