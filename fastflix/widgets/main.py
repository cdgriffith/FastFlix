#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import logging
import math
import os
import random
import secrets
import shutil
import time
from collections import namedtuple
from datetime import timedelta
from pathlib import Path
from queue import Empty
from typing import Tuple, Union, Optional

import importlib.resources
import reusables
from box import Box
from pydantic import ConfigDict, BaseModel, Field
from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.encoders.common import helpers
from fastflix.exceptions import FastFlixInternalException, FlixError
from fastflix.ui_scale import scaler
from fastflix.ui_constants import WIDTHS, HEIGHTS, ICONS
from fastflix.ui_styles import ONYX_COLORS, get_onyx_combobox_style, get_onyx_button_style
from fastflix.flix import (
    detect_hdr10_plus,
    detect_interlaced,
    extract_attachments,
    generate_thumbnail_command,
    get_auto_crop,
    parse,
    parse_hdr_details,
    get_concat_item,
)
from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.models.video import Status, Video, VideoSettings, Crop
from fastflix.resources import (
    get_icon,
    group_box_style,
    onyx_convert_icon,
    onyx_queue_add_icon,
    get_text_color,
)
from fastflix.shared import (
    error_message,
    message,
    time_to_number,
    yes_no_message,
    clean_file_string,
    get_filesafe_datetime,
)
from fastflix.windows_tools import prevent_sleep_mode, allow_sleep_mode
from fastflix.widgets.background_tasks import ThumbnailCreator
from fastflix.widgets.progress_bar import ProgressBar, Task
from fastflix.widgets.video_options import VideoOptions
from fastflix.widgets.windows.large_preview import LargePreview

logger = logging.getLogger("fastflix")

root = os.path.abspath(os.path.dirname(__file__))

only_int = QtGui.QIntValidator()

Request = namedtuple(
    "Request",
    ["request", "video_uuid", "command_uuid", "command", "work_dir", "log_name", "shell"],
    defaults=[None, None, None, None, None, False],
)

Response = namedtuple("Response", ["status", "video_uuid", "command_uuid"])

resolutions = {
    t("Auto"): {"method": "auto"},
    t("Long Edge"): {"method": "long edge"},
    t("Width"): {"method": "width"},
    t("Height"): {"method": "height"},
    t("Custom (w:h)"): {"method": "custom"},
    "4320 LE": {"method": "long edge", "pixels": 4320},
    "2160 LE": {"method": "long edge", "pixels": 2160},
    "1920 LE": {"method": "long edge", "pixels": 1920},
    "1440 LE": {"method": "long edge", "pixels": 1440},
    "1280 LE": {"method": "long edge", "pixels": 1280},
    "1080 LE": {"method": "long edge", "pixels": 1080},
    "720 LE": {"method": "long edge", "pixels": 720},
    "480 LE": {"method": "long edge", "pixels": 480},
    "4320 H": {"method": "height", "pixels": 4320},
    "2160 H": {"method": "height", "pixels": 2160},
    "1920 H": {"method": "height", "pixels": 1920},
    "1440 H": {"method": "height", "pixels": 1440},
    "1080 H": {"method": "height", "pixels": 1080},
    "720 H": {"method": "height", "pixels": 720},
    "480 H": {"method": "height", "pixels": 480},
    "7680 W": {"method": "width", "pixels": 7680},
    "3840 W": {"method": "width", "pixels": 3840},
    "2560 W": {"method": "width", "pixels": 2560},
    "1920 W": {"method": "width", "pixels": 1920},
    "1280 W": {"method": "width", "pixels": 1280},
    "1024 W": {"method": "width", "pixels": 1024},
    "640 W": {"method": "width", "pixels": 640},
}


class CropWidgets(BaseModel):
    top: QtWidgets.QLineEdit = None
    bottom: QtWidgets.QLineEdit = None
    left: QtWidgets.QLineEdit = None
    right: QtWidgets.QLineEdit = None
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ScaleWidgets(BaseModel):
    width: QtWidgets.QLineEdit = None
    height: QtWidgets.QLineEdit = None
    model_config = ConfigDict(arbitrary_types_allowed=True)


class MainWidgets(BaseModel):
    start_time: QtWidgets.QLineEdit = None
    end_time: QtWidgets.QLineEdit = None
    video_track: QtWidgets.QComboBox = None
    video_track_widget: QtWidgets.QWidget = None
    rotate: QtWidgets.QComboBox = None
    flip: QtWidgets.QComboBox = None
    crop: CropWidgets = Field(default_factory=CropWidgets)
    scale: ScaleWidgets = Field(default_factory=ScaleWidgets)
    remove_metadata: QtWidgets.QCheckBox = None
    chapters: QtWidgets.QCheckBox = None
    fast_time: QtWidgets.QComboBox = None
    preview: QtWidgets.QLabel = None
    convert_to: QtWidgets.QComboBox = None
    convert_button: QtWidgets.QPushButton = None
    deinterlace: QtWidgets.QCheckBox = None
    remove_hdr: QtWidgets.QCheckBox = None
    profile_box: QtWidgets.QComboBox = None
    thumb_time: QtWidgets.QSlider = None
    preview_time_label: QtWidgets.QLabel = None
    resolution_drop_down: QtWidgets.QComboBox = None
    resolution_custom: QtWidgets.QLineEdit = None
    video_res_label: QtWidgets.QLabel = None
    output_res_label: QtWidgets.QLabel = None
    output_directory: QtWidgets.QPushButton = None
    output_directory_combo: QtWidgets.QComboBox = None
    output_type_combo: QtWidgets.QComboBox = Field(default_factory=QtWidgets.QComboBox)
    output_directory_select: QtWidgets.QPushButton = None
    model_config = ConfigDict(arbitrary_types_allowed=True)
    copy_data: QtWidgets.QCheckBox = None

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
    close_event = QtCore.Signal()
    status_update_signal = QtCore.Signal(tuple)
    thread_logging_signal = QtCore.Signal(str)

    def __init__(self, parent, app: FastFlixApp):
        super().__init__(parent)
        self.app: FastFlixApp = app
        self.setObjectName("Main")
        self.container = parent
        self.video: Video = Video(source=Path(), width=0, height=0, duration=0)

        self.initialized = False
        self.loading_video = True
        self.scale_updating = False
        self.last_thumb_hash = ""
        self.page_updating = False
        self.previous_encoder_no_audio = False

        self.large_preview = LargePreview(self)

        self.notifier = Notifier(self, self.app, self.app.fastflix.status_queue)
        self.notifier.start()

        self.input_defaults = Box(scale=None, crop=None)
        self.initial_duration = 0

        self.temp_dir = self.get_temp_work_path()

        self.setAcceptDrops(True)

        self.input_video = None
        self.video_path_widget = QtWidgets.QLineEdit(t("No Source Selected"))
        motto = ""
        if self.app.fastflix.config.language == "eng":
            motto = random.choice(
                [
                    "Welcome to FastFlix!",
                    "Hope your encoding goes well!",
                    "<Drag and drop your vid here>",
                    "Encoding faster than the speed of light is against the law",
                    "4K HDR is important. Good content is importanter",
                    "Water is wet, the sky is blue, FastFlix is Free",
                    "Grab onto your trousers, it's time for an encode!",
                    "It's cold in here, lets warm up the room with a nice encoding",
                    "It's a good day to encode",
                    "Encode Hard",
                    "Where there's an encode, there's a way",
                    "Start your day off right with a nice encode",
                    "Encoding, encoding, always with the encoding!",
                    "Try VP9 this time, no wait, HEVC, or maybe a GIF?",
                    "Something, Something, Dark Theme",
                    "Where we're going, we don't need transcodes",
                    "May the FastFlix be with you",
                    "Handbrake didn't do it for ya?",
                    "Did you select the right audio track?",
                    "FastFlix? In this economy?",
                    "The name's Flix. FastFlix",
                    "It's pronounced gif",
                    "I'm not trying to convert you, just your video",
                    "I <3 Billionaires (Sponsor link on Github)",
                    "I'm going to make you an encode you can't refuse",
                ]
            )
        self.source_video_path_widget = QtWidgets.QLineEdit(motto)
        self.source_video_path_widget.setFixedHeight(scaler.scale(HEIGHTS.PATH_WIDGET))
        self.source_video_path_widget.setFont(QtGui.QFont(self.app.font().family(), 9))
        self.source_video_path_widget.setDisabled(True)
        self.source_video_path_widget.setStyleSheet(
            f"padding: 0 0 -1px 5px; color: rgb({get_text_color(self.app.fastflix.config.theme)})"
        )

        self.output_video_path_widget = QtWidgets.QLineEdit("")
        self.output_video_path_widget.setDisabled(True)
        self.output_video_path_widget.setFixedHeight(scaler.scale(HEIGHTS.PATH_WIDGET))
        self.output_video_path_widget.setFont(QtGui.QFont(self.app.font().family(), 9))
        self.output_video_path_widget.setStyleSheet(
            f"padding: 0 0 -1px 5px; color: rgb({get_text_color(self.app.fastflix.config.theme)})"
        )
        self.output_video_path_widget.setMaxLength(220)

        # self.output_video_path_widget.textChanged.connect(lambda x: self.page_update(build_thumbnail=False))
        self.video_path_widget.setEnabled(False)

        QtCore.QTimer.singleShot(6_000, self.fade_loop)

        self.widgets: MainWidgets = MainWidgets()

        self.buttons = []

        self.thumb_file = Path(self.app.fastflix.config.work_path, "thumbnail_preview.jpg")

        self.video_options = VideoOptions(
            self,
            app=self.app,
            available_audio_encoders=self.app.fastflix.audio_encoders,
        )

        # self.completed.connect(self.conversion_complete)
        # self.cancelled.connect(self.conversion_cancelled)
        self.close_event.connect(self.close)
        self.thumbnail_complete.connect(self.thumbnail_generated)
        self.status_update_signal.connect(self.status_update)
        self.thread_logging_signal.connect(self.thread_logger)
        self.encoding_worker = None
        self.command_runner = None
        self.side_data = Box()
        self.default_options = Box()

        self.grid = QtWidgets.QGridLayout()

        # Set column stretch factors:
        # Left (cols 0-5) and Right (cols 11-13) stay fixed (stretch=0)
        # Preview area (cols 6-10) expands to fill available space (stretch=1)
        for col in range(6):
            self.grid.setColumnStretch(col, 0)
        for col in range(6, 11):
            self.grid.setColumnStretch(col, 1)
        for col in range(11, 14):
            self.grid.setColumnStretch(col, 0)

        # row: int, column: int, rowSpan: int, columnSpan: int

        self.grid.addLayout(self.init_top_bar(), 0, 0, 1, 6)
        self.grid.addLayout(self.init_top_bar_right(), 0, 11, 1, 3)
        self.grid.addLayout(self.init_video_area(), 1, 0, 6, 6)
        self.grid.addLayout(self.init_right_col(), 1, 11, 6, 3)

        # pi = QtWidgets.QVBoxLayout()
        # pi.addWidget(self.init_preview_image())
        # pi.addLayout(self.())

        self.grid.addWidget(self.init_preview_image(), 0, 6, 7, 5)
        # self.grid.addLayout(pi, 0, 6, 7, 5)

        spacer = QtWidgets.QLabel()
        spacer.setFixedHeight(scaler.scale(HEIGHTS.SPACER_SMALL))
        self.grid.addWidget(spacer, 8, 0, 1, 14)

        self.grid.addWidget(self.video_options, 9, 0, 10, 14)

        self.grid.setSpacing(5)
        self.paused = False

        self.disable_all()
        self.setLayout(self.grid)

        if self.app.fastflix.config.theme == "onyx":
            self.setStyleSheet(
                "QLabel{ color: white; } "
                "QLineEdit{ color: white; } "
                "QCheckBox{ color: white; } "
                "QGroupBox{ color: white; } "
            )

        self.show()
        self.initialized = True
        self.loading_video = False
        self.last_page_update = time.time()

    def fade_loop(self, percent=90):
        if self.input_video:
            self.source_video_path_widget.setStyleSheet(
                f"color: rgb({get_text_color(self.app.fastflix.config.theme)}); padding: 0 0 -1px 5px;"
            )
            return
        if percent > 0:
            op = QtWidgets.QGraphicsOpacityEffect()
            op.setOpacity(percent)
            self.source_video_path_widget.setStyleSheet(
                f"color: rgba({get_text_color(self.app.fastflix.config.theme)}, {percent / 100}); padding: 0 0 -1px 5px;"
            )
            self.source_video_path_widget.setGraphicsEffect(op)
            QtCore.QTimer.singleShot(200, lambda: self.fade_loop(percent - 10))
        else:
            self.source_video_path_widget.setStyleSheet(
                f"color: rgb({get_text_color(self.app.fastflix.config.theme)}); padding: 0 0 -1px 5px;"
            )
            self.source_video_path_widget.setText("")

    def init_top_bar(self):
        top_bar = QtWidgets.QHBoxLayout()

        source = QtWidgets.QPushButton(QtGui.QIcon(self.get_icon("onyx-source")), f"  {t('Source')}")
        source.setIconSize(scaler.scale_size(ICONS.MEDIUM, ICONS.MEDIUM))
        source.setFixedHeight(scaler.scale(HEIGHTS.TOP_BAR_BUTTON))
        source.setStyleSheet("font-size: 14px;")
        source.setDefault(True)
        source.clicked.connect(lambda: self.open_file())

        self.widgets.profile_box = QtWidgets.QComboBox()
        self.widgets.profile_box.setStyleSheet("text-align: center; font-size: 14px;")
        self.widgets.profile_box.addItems(self.app.fastflix.config.profiles.keys())
        self.widgets.profile_box.view().setFixedWidth(
            self.widgets.profile_box.minimumSizeHint().width() + scaler.scale(50)
        )
        self.widgets.profile_box.setCurrentText(self.app.fastflix.config.selected_profile)
        self.widgets.profile_box.currentIndexChanged.connect(self.set_profile)
        self.widgets.profile_box.setFixedWidth(scaler.scale(WIDTHS.PROFILE_BOX))
        self.widgets.profile_box.setFixedHeight(scaler.scale(HEIGHTS.TOP_BAR_BUTTON))

        top_bar.addWidget(source)
        top_bar.addWidget(QtWidgets.QSplitter(QtCore.Qt.Horizontal))
        top_bar.addLayout(self.init_encoder_drop_down())
        top_bar.addWidget(QtWidgets.QSplitter(QtCore.Qt.Horizontal))
        top_bar.addWidget(self.widgets.profile_box)
        top_bar.addWidget(QtWidgets.QSplitter(QtCore.Qt.Horizontal))

        self.add_profile = QtWidgets.QPushButton(QtGui.QIcon(self.get_icon("onyx-new-profile")), "")
        self.add_profile.setFixedHeight(scaler.scale(HEIGHTS.TOP_BAR_BUTTON))
        self.add_profile.setIconSize(scaler.scale_size(ICONS.SMALL + 4, ICONS.SMALL + 4))
        self.add_profile.setToolTip(t("New Profile"))
        # add_profile.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.add_profile.clicked.connect(lambda: self.container.new_profile())
        self.add_profile.setDisabled(True)
        # options = QtWidgets.QPushButton(QtGui.QIcon(self.get_icon("settings")), "")
        # options.setFixedSize(QtCore.QSize(40, 40))
        # options.setIconSize(QtCore.QSize(22, 22))
        # options.setToolTip(t("Settings"))
        # options.clicked.connect(lambda: self.container.show_setting())

        top_bar.addWidget(self.add_profile)
        top_bar.addStretch(1)
        # top_bar.addWidget(options)

        return top_bar

    def init_top_bar_right(self):
        top_bar_right = QtWidgets.QHBoxLayout()
        theme = "QPushButton{ padding: 0 10px; font-size: 14px; }"
        if self.app.fastflix.config.theme in ("dark", "onyx"):
            theme = """
            QPushButton {
              padding: 0 10px;
              font-size: 14px;
              background-color: #4f4f4f;
              border: none;
              color: white; }
            QPushButton:hover {
              background-color: #6b6b6b; }"""

        queue = QtWidgets.QPushButton(QtGui.QIcon(onyx_queue_add_icon), f"{t('Add to Queue')}  ")
        queue.setIconSize(scaler.scale_size(ICONS.LARGE, ICONS.LARGE))
        queue.setFixedHeight(scaler.scale(HEIGHTS.TOP_BAR_BUTTON))
        queue.setStyleSheet(theme)
        queue.setLayoutDirection(QtCore.Qt.RightToLeft)
        queue.clicked.connect(lambda: self.add_to_queue())

        self.widgets.convert_button = QtWidgets.QPushButton(QtGui.QIcon(onyx_convert_icon), f"{t('Convert')}  ")
        self.widgets.convert_button.setIconSize(scaler.scale_size(ICONS.LARGE, ICONS.LARGE))
        self.widgets.convert_button.setFixedHeight(scaler.scale(HEIGHTS.TOP_BAR_BUTTON))
        self.widgets.convert_button.setStyleSheet(theme)
        self.widgets.convert_button.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.widgets.convert_button.clicked.connect(lambda: self.encode_video())
        top_bar_right.addStretch(1)
        top_bar_right.addWidget(queue)
        top_bar_right.addWidget(self.widgets.convert_button)
        return top_bar_right

    def init_thumb_time_selector(self):
        """Create the preview time slider overlay widget with time display."""
        container = QtWidgets.QWidget()
        container.setStyleSheet("background-color: rgba(0, 0, 0, 50); border-radius: 5px;")
        container.setFixedHeight(scaler.scale(32))

        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(scaler.scale(10), scaler.scale(4), scaler.scale(10), scaler.scale(4))

        self.widgets.thumb_time = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.widgets.thumb_time.setMinimum(1)
        self.widgets.thumb_time.setMaximum(100)
        self.widgets.thumb_time.setValue(25)
        self.widgets.thumb_time.setSingleStep(1)
        self.widgets.thumb_time.setPageStep(10)
        self.widgets.thumb_time.setAutoFillBackground(False)
        self.widgets.thumb_time.sliderReleased.connect(self.thumb_time_change)
        self.widgets.thumb_time.valueChanged.connect(self.update_preview_time_label)
        self.widgets.thumb_time.installEventFilter(self)
        self.widgets.thumb_time.setStyleSheet("""
            QSlider {
                background: rgba(255, 255, 255, 0);
            }

            QSlider::groove:horizontal {
                background: rgba(255, 255, 255, 40);
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: rgba(255, 255, 255, 255);
                width: 12px;
                height: 16px;
                margin: -5px 0;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: transparent;
            }
        """)

        self.widgets.preview_time_label = QtWidgets.QLabel("0:00:00")
        self.widgets.preview_time_label.setStyleSheet("color: white; font-weight: bold; background: transparent;")
        self.widgets.preview_time_label.setFixedWidth(scaler.scale(70))
        self.widgets.preview_time_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        layout.addWidget(self.widgets.thumb_time)
        layout.addWidget(self.widgets.preview_time_label)

        return container

    def update_preview_time_label(self):
        """Update the time label when slider value changes."""
        if not self.app.fastflix.current_video:
            self.widgets.preview_time_label.setText("0:00:00")
            return
        time_seconds = self.preview_place
        self.widgets.preview_time_label.setText(self.format_preview_time(time_seconds))

    @staticmethod
    def format_preview_time(seconds: float) -> str:
        """Convert seconds to H:MM:SS format."""
        if seconds < 0:
            seconds = 0
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}:{minutes:02d}:{secs:02d}"

    def thumb_time_change(self):
        self.generate_thumbnail()

    def eventFilter(self, obj, event):
        if obj == self.widgets.thumb_time:
            if event.type() == QtCore.QEvent.KeyRelease and event.key() in (
                QtCore.Qt.Key_Left,
                QtCore.Qt.Key_Right,
                QtCore.Qt.Key_Up,
                QtCore.Qt.Key_Down,
                QtCore.Qt.Key_PageUp,
                QtCore.Qt.Key_PageDown,
            ):
                if not event.isAutoRepeat():
                    self.thumb_time_change()
        return super().eventFilter(obj, event)

    def get_temp_work_path(self):
        new_temp = self.app.fastflix.config.work_path / f"temp_{get_filesafe_datetime()}_{secrets.token_hex(8)}"
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
        self.thumb_file = Path(self.app.fastflix.config.work_path, "thumbnail_preview.jpg")
        self.change_output_types()
        self.page_update(build_thumbnail=True)

    def init_video_area(self):
        layout = QtWidgets.QVBoxLayout()
        spacer = QtWidgets.QLabel()
        spacer.setFixedHeight(scaler.scale(2))
        layout.addWidget(spacer)

        # Group box for Source/Folder/Filename
        file_group = QtWidgets.QGroupBox()
        file_group.setStyleSheet(group_box_style(bb="none"))
        file_group_layout = QtWidgets.QVBoxLayout(file_group)
        file_group_layout.setContentsMargins(0, 0, 0, scaler.scale(5))
        file_group_layout.setSpacing(scaler.scale(12))

        source_layout = QtWidgets.QHBoxLayout()
        source_label = QtWidgets.QLabel(t("Source"))
        source_label.setFixedWidth(scaler.scale(WIDTHS.SOURCE_LABEL))
        if self.app.fastflix.config.theme == "onyx":
            source_label.setStyleSheet("color: white;")
        self.source_video_path_widget.setFixedHeight(scaler.scale(HEIGHTS.COMBO_BOX))
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.source_video_path_widget, stretch=True)

        output_layout = QtWidgets.QHBoxLayout()
        output_label = QtWidgets.QLabel(t("Filename"))
        output_label.setFixedWidth(scaler.scale(WIDTHS.SOURCE_LABEL))
        if self.app.fastflix.config.theme == "onyx":
            output_label.setStyleSheet("color: white;")
        self.output_video_path_widget.setFixedHeight(scaler.scale(HEIGHTS.COMBO_BOX))
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_video_path_widget, stretch=True)

        self.widgets.output_type_combo.setFixedWidth(scaler.scale(WIDTHS.OUTPUT_TYPE))
        self.widgets.output_type_combo.addItems(self.current_encoder.video_extensions)
        self.widgets.output_type_combo.setFixedHeight(scaler.scale(HEIGHTS.COMBO_BOX))
        if self.app.fastflix.config.theme == "onyx":
            self.widgets.output_type_combo.setStyleSheet(get_onyx_combobox_style())
        self.widgets.output_type_combo.currentIndexChanged.connect(lambda: self.page_update(build_thumbnail=False))

        output_layout.addWidget(self.widgets.output_type_combo)

        out_dir_layout = QtWidgets.QHBoxLayout()
        out_dir_label = QtWidgets.QLabel(t("Folder"))
        out_dir_label.setFixedHeight(scaler.scale(HEIGHTS.COMBO_BOX))
        out_dir_label.setFixedWidth(scaler.scale(WIDTHS.SOURCE_LABEL))
        self.widgets.output_directory = QtWidgets.QPushButton()
        self.widgets.output_directory.setFixedHeight(scaler.scale(HEIGHTS.OUTPUT_DIR))
        self.widgets.output_directory.clicked.connect(self.save_directory)

        self.output_path_button = QtWidgets.QPushButton(icon=QtGui.QIcon(self.get_icon("onyx-output")))
        self.output_path_button.clicked.connect(lambda: self.save_file())
        self.output_path_button.setDisabled(True)
        self.output_path_button.setIconSize(scaler.scale_size(ICONS.SMALL + 3, ICONS.SMALL + 3))
        self.output_path_button.setFixedSize(scaler.scale_size(ICONS.SMALL + 3, ICONS.SMALL + 3))
        self.output_path_button.setStyleSheet("border: none; padding: 0; margin: 0")

        out_dir_layout.addWidget(out_dir_label)
        out_dir_layout.addWidget(self.widgets.output_directory, alignment=QtCore.Qt.AlignTop)
        out_dir_layout.addWidget(self.output_path_button)

        file_group_layout.addLayout(source_layout)
        file_group_layout.addLayout(out_dir_layout)
        file_group_layout.addLayout(output_layout)

        # Video info bar (bit depth, color space, chroma subsampling, HDR10, HDR10+)
        self.video_bit_depth_label = QtWidgets.QLabel()
        self.video_chroma_label = QtWidgets.QLabel()
        self.video_hdr10_label = QtWidgets.QLabel()
        self.video_hdr10plus_label = QtWidgets.QLabel()
        for lbl in (
            self.video_bit_depth_label,
            self.video_chroma_label,
            self.video_hdr10_label,
            self.video_hdr10plus_label,
        ):
            lbl.hide()

        info_layout = QtWidgets.QHBoxLayout()
        self.video_info_label = QtWidgets.QLabel(t("Video Info"))
        self.video_info_label.setFixedWidth(scaler.scale(WIDTHS.SOURCE_LABEL))
        if self.app.fastflix.config.theme == "onyx":
            self.video_info_label.setStyleSheet("color: white;")
        self.video_info_label.hide()
        info_layout.addWidget(self.video_info_label)
        info_layout.addWidget(self.video_bit_depth_label)
        info_layout.addSpacing(scaler.scale(12))
        info_layout.addWidget(self.video_chroma_label)
        info_layout.addSpacing(scaler.scale(12))
        info_layout.addWidget(self.video_hdr10_label)
        info_layout.addSpacing(scaler.scale(12))
        info_layout.addWidget(self.video_hdr10plus_label)
        info_layout.addStretch()
        file_group_layout.addLayout(info_layout)

        layout.addWidget(file_group)

        layout.addWidget(self.init_video_track_select())

        layout.addStretch(1)
        return layout

    def init_right_col(self):
        layout = QtWidgets.QVBoxLayout()
        # Add padding above the tabs
        layout.addSpacing(scaler.scale(8))
        layout.addWidget(self.init_options_tabs())
        layout.addStretch(1)
        return layout

    def init_options_tabs(self):
        """Create a tabbed widget with Size, Start/End Time, Crop, and Options tabs."""
        tabs = QtWidgets.QTabWidget()
        tabs.setIconSize(QtCore.QSize(scaler.scale(20), scaler.scale(20)))
        if self.app.fastflix.config.theme == "onyx":
            tabs.setStyleSheet("QLabel{ color: white; } QCheckBox{ color: white; }")

        # Tab 1: Size (Resolution + Transforms)
        size_tab = QtWidgets.QWidget()
        size_layout = QtWidgets.QVBoxLayout(size_tab)
        size_layout.setSpacing(scaler.scale(8))
        size_layout.setContentsMargins(scaler.scale(8), scaler.scale(8), scaler.scale(8), scaler.scale(8))

        # Resolution info labels
        self.widgets.video_res_label = QtWidgets.QLabel(t("Video Resolution") + ": --")
        self.widgets.output_res_label = QtWidgets.QLabel(t("Output Resolution") + ": --")
        size_layout.addWidget(self.widgets.video_res_label)
        size_layout.addWidget(self.widgets.output_res_label)

        # Resolution row
        res_row = QtWidgets.QHBoxLayout()
        res_row.setSpacing(scaler.scale(4))
        res_label = QtWidgets.QLabel(t("Resolution"))
        res_label.setFixedWidth(scaler.scale(68))
        res_row.addWidget(res_label)

        self.widgets.resolution_drop_down = QtWidgets.QComboBox()
        self.widgets.resolution_drop_down.addItems(list(resolutions.keys()))
        self.widgets.resolution_drop_down.currentIndexChanged.connect(self.update_resolution)
        if self.app.fastflix.config.theme == "onyx":
            self.widgets.resolution_drop_down.setStyleSheet(get_onyx_combobox_style())
        res_row.addWidget(self.widgets.resolution_drop_down)

        self.widgets.resolution_custom = QtWidgets.QLineEdit()
        self.widgets.resolution_custom.setFixedWidth(scaler.scale(WIDTHS.RESOLUTION_CUSTOM))
        self.widgets.resolution_custom.textChanged.connect(self.custom_res_update)
        res_row.addWidget(self.widgets.resolution_custom)

        size_layout.addLayout(res_row)

        # Transform row (rotate + flip)
        transform_row = QtWidgets.QHBoxLayout()
        transform_row.setSpacing(scaler.scale(4))

        rot_label = QtWidgets.QLabel(t("Rotate"))
        rot_label.setFixedWidth(scaler.scale(68))
        transform_row.addWidget(rot_label)
        transform_row.addWidget(self.init_rotate())

        flip_label = QtWidgets.QLabel(t("Flip"))
        flip_label.setFixedWidth(scaler.scale(30))
        transform_row.addWidget(flip_label)
        transform_row.addWidget(self.init_flip())
        transform_row.addStretch(1)

        size_layout.addLayout(transform_row)
        size_layout.addStretch(1)

        tabs.addTab(size_tab, t("Size"))

        # Tab 2: Start/End Time (compact 2-column layout)
        time_tab = QtWidgets.QWidget()
        time_layout = QtWidgets.QHBoxLayout(time_tab)
        time_layout.setSpacing(scaler.scale(12))
        time_layout.setContentsMargins(scaler.scale(8), scaler.scale(8), scaler.scale(8), scaler.scale(8))

        # Column 1: Reset button and Seek mode
        time_col1 = QtWidgets.QVBoxLayout()
        time_col1.setSpacing(scaler.scale(4))

        time_reset = QtWidgets.QPushButton(t("Reset"))
        time_reset.setFixedHeight(scaler.scale(22))
        time_reset.setToolTip(t("Reset start and end times"))
        time_reset.clicked.connect(self.reset_time)
        if self.app.fastflix.config.theme == "onyx":
            time_reset.setStyleSheet(get_onyx_button_style())
        self.buttons.append(time_reset)

        self.widgets.fast_time = QtWidgets.QComboBox()
        self.widgets.fast_time.addItems([t("Fast"), t("Exact")])
        self.widgets.fast_time.setCurrentIndex(0)
        self.widgets.fast_time.setFixedHeight(scaler.scale(22))
        if self.app.fastflix.config.theme == "onyx":
            self.widgets.fast_time.setStyleSheet(get_onyx_combobox_style())
        self.widgets.fast_time.setToolTip(
            t(
                "uses [fast] seek to a rough position ahead of timestamp, "
                "vs a specific [exact] frame lookup. (GIF encodings use [fast])"
            )
        )
        self.widgets.fast_time.currentIndexChanged.connect(lambda: self.page_update(build_thumbnail=False))

        time_col1.addWidget(time_reset)
        time_col1.addWidget(self.widgets.fast_time)
        time_col1.addStretch(1)

        # Column 2: Start and End times stacked vertically
        time_col2 = QtWidgets.QVBoxLayout()
        time_col2.setSpacing(scaler.scale(4))

        self.widgets.start_time, start_row = self.build_hoz_int_field(
            t("Start"),
            right_stretch=False,
            left_stretch=False,
            time_field=True,
        )
        self.widgets.start_time.textChanged.connect(lambda: self.page_update())
        start_from_preview = QtWidgets.QPushButton()
        start_from_preview.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DesktopIcon))
        start_from_preview.setFixedSize(scaler.scale(24), scaler.scale(28))
        start_from_preview.setToolTip(t("Set start time from preview position"))
        start_from_preview.clicked.connect(lambda: self.set_time_from_preview(self.widgets.start_time))
        self.buttons.append(start_from_preview)
        start_row.addWidget(start_from_preview)

        self.widgets.end_time, end_row = self.build_hoz_int_field(
            t("End"),
            left_stretch=False,
            right_stretch=False,
            time_field=True,
        )
        self.widgets.end_time.textChanged.connect(lambda: self.page_update())
        end_from_preview = QtWidgets.QPushButton()
        end_from_preview.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DesktopIcon))
        end_from_preview.setFixedSize(scaler.scale(24), scaler.scale(28))
        end_from_preview.setToolTip(t("Set end time from preview position"))
        end_from_preview.clicked.connect(lambda: self.set_time_from_preview(self.widgets.end_time))
        self.buttons.append(end_from_preview)
        end_row.addWidget(end_from_preview)

        time_col2.addLayout(start_row)
        time_col2.addLayout(end_row)
        time_col2.addStretch(1)

        time_layout.addLayout(time_col1)
        time_layout.addLayout(time_col2)
        time_layout.addStretch(1)

        tabs.addTab(time_tab, t("Start/End Time"))

        # Tab 3: Crop (3-column layout)
        crop_tab = QtWidgets.QWidget()
        crop_layout = QtWidgets.QHBoxLayout(crop_tab)
        crop_layout.setSpacing(scaler.scale(12))
        crop_layout.setContentsMargins(scaler.scale(8), scaler.scale(8), scaler.scale(8), scaler.scale(8))

        # Column 1: Auto and Reset buttons
        col1 = QtWidgets.QVBoxLayout()
        col1.setSpacing(scaler.scale(4))
        auto_crop = QtWidgets.QPushButton(t("Auto"))
        auto_crop.setFixedHeight(scaler.scale(22))
        auto_crop.setToolTip(t("Automatically detect black borders"))
        auto_crop.clicked.connect(self.get_auto_crop)
        if self.app.fastflix.config.theme == "onyx":
            auto_crop.setStyleSheet(get_onyx_button_style())
        self.buttons.append(auto_crop)
        reset = QtWidgets.QPushButton(t("Reset"))
        reset.setFixedHeight(scaler.scale(22))
        reset.setToolTip(t("Reset crop"))
        reset.clicked.connect(self.reset_crop)
        if self.app.fastflix.config.theme == "onyx":
            reset.setStyleSheet(get_onyx_button_style())
        self.buttons.append(reset)
        col1.addWidget(auto_crop)
        col1.addWidget(reset)
        col1.addStretch(1)

        # Crop input fields
        field_width = scaler.scale(50)
        field_height = scaler.scale(22)

        self.widgets.crop.top = QtWidgets.QLineEdit("0")
        self.widgets.crop.top.setValidator(only_int)
        self.widgets.crop.top.setFixedSize(field_width, field_height)
        self.widgets.crop.top.setAlignment(QtCore.Qt.AlignCenter)
        self.widgets.crop.top.textChanged.connect(lambda: self.page_update())

        self.widgets.crop.bottom = QtWidgets.QLineEdit("0")
        self.widgets.crop.bottom.setValidator(only_int)
        self.widgets.crop.bottom.setFixedSize(field_width, field_height)
        self.widgets.crop.bottom.setAlignment(QtCore.Qt.AlignCenter)
        self.widgets.crop.bottom.textChanged.connect(lambda: self.page_update())

        self.widgets.crop.left = QtWidgets.QLineEdit("0")
        self.widgets.crop.left.setValidator(only_int)
        self.widgets.crop.left.setFixedSize(field_width, field_height)
        self.widgets.crop.left.setAlignment(QtCore.Qt.AlignCenter)
        self.widgets.crop.left.textChanged.connect(lambda: self.page_update())

        self.widgets.crop.right = QtWidgets.QLineEdit("0")
        self.widgets.crop.right.setValidator(only_int)
        self.widgets.crop.right.setFixedSize(field_width, field_height)
        self.widgets.crop.right.setAlignment(QtCore.Qt.AlignCenter)
        self.widgets.crop.right.textChanged.connect(lambda: self.page_update())

        # Column 2: Top and Bottom
        col2 = QtWidgets.QVBoxLayout()
        col2.setSpacing(scaler.scale(4))
        top_row = QtWidgets.QHBoxLayout()
        top_row.addWidget(QtWidgets.QLabel(t("Top")))
        top_row.addWidget(self.widgets.crop.top)
        bottom_row = QtWidgets.QHBoxLayout()
        bottom_row.addWidget(QtWidgets.QLabel(t("Bottom")))
        bottom_row.addWidget(self.widgets.crop.bottom)
        col2.addLayout(top_row)
        col2.addLayout(bottom_row)
        col2.addStretch(1)

        # Column 3: Left and Right
        col3 = QtWidgets.QVBoxLayout()
        col3.setSpacing(scaler.scale(4))
        left_row = QtWidgets.QHBoxLayout()
        left_row.addWidget(QtWidgets.QLabel(t("Left")))
        left_row.addWidget(self.widgets.crop.left)
        right_row = QtWidgets.QHBoxLayout()
        right_row.addWidget(QtWidgets.QLabel(t("Right")))
        right_row.addWidget(self.widgets.crop.right)
        col3.addLayout(left_row)
        col3.addLayout(right_row)
        col3.addStretch(1)

        crop_layout.addLayout(col1)
        crop_layout.addLayout(col2)
        crop_layout.addLayout(col3)
        crop_layout.addStretch(1)

        tabs.addTab(crop_tab, t("Crop"))

        # Tab 4: Options (checkboxes)
        opts_tab = QtWidgets.QWidget()
        opts_layout = QtWidgets.QVBoxLayout(opts_tab)
        opts_layout.setSpacing(scaler.scale(4))
        opts_layout.setContentsMargins(scaler.scale(8), scaler.scale(8), scaler.scale(8), scaler.scale(8))

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

        self.widgets.deinterlace = QtWidgets.QCheckBox(t("Deinterlace"))
        self.widgets.deinterlace.setChecked(False)
        self.widgets.deinterlace.toggled.connect(self.interlace_update)
        self.widgets.deinterlace.setToolTip(
            f"{t('Enables the yadif filter.')}\n{t('Automatically enabled when an interlaced video is detected')}"
        )

        self.widgets.remove_hdr = QtWidgets.QCheckBox(t("Remove HDR"))
        self.widgets.remove_hdr.setChecked(False)
        self.widgets.remove_hdr.toggled.connect(self.hdr_update)
        self.widgets.remove_hdr.setToolTip(
            f"{t('Convert BT2020 colorspace into bt709')}\n"
            f"{t('WARNING: This will take much longer and result in a larger file')}"
        )

        opts_layout.addWidget(self.widgets.remove_metadata)
        opts_layout.addWidget(self.widgets.chapters)
        opts_layout.addWidget(self.widgets.deinterlace)
        opts_layout.addWidget(self.widgets.remove_hdr)
        opts_layout.addStretch(1)

        tabs.addTab(opts_tab, t("Options"))

        return tabs

    def init_video_track_select(self):
        self.widgets.video_track_widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(self.widgets.video_track_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        self.widgets.video_track = QtWidgets.QComboBox()
        self.widgets.video_track.addItems([])
        self.widgets.video_track.setFixedHeight(scaler.scale(HEIGHTS.COMBO_BOX))
        self.widgets.video_track.currentIndexChanged.connect(self.video_track_update)
        self.widgets.video_track.setStyleSheet("height: 5px")
        if self.app.fastflix.config.theme == "onyx":
            self.widgets.video_track.setStyleSheet(f"border-radius: {scaler.scale(10)}px; color: white")

        track_label = QtWidgets.QLabel(t("Video Track"))
        track_label.setFixedWidth(scaler.scale(WIDTHS.VIDEO_TRACK_LABEL))
        layout.addWidget(track_label)
        layout.addWidget(self.widgets.video_track, stretch=1)
        layout.setSpacing(10)
        # Hidden by default, shown only when there's more than one video track
        self.widgets.video_track_widget.hide()
        return self.widgets.video_track_widget

    def set_profile(self):
        if self.loading_video:
            return
        self.app.fastflix.config.selected_profile = self.widgets.profile_box.currentText()
        self.app.fastflix.config.save()
        self.widgets.convert_to.setCurrentText(self.app.fastflix.config.opt("encoder"))
        if self.app.fastflix.config.opt("auto_crop") and not self.build_crop():
            self.get_auto_crop()
        self.loading_video = True
        try:
            # self.widgets.scale.keep_aspect.setChecked(self.app.fastflix.config.opt("keep_aspect_ratio"))
            self.widgets.rotate.setCurrentIndex((self.app.fastflix.config.opt("rotate") or 0) // 90)

            v_flip = self.app.fastflix.config.opt("vertical_flip")
            h_flip = self.app.fastflix.config.opt("horizontal_flip")

            self.widgets.flip.setCurrentIndex(self.flip_to_int(v_flip, h_flip))

            res_method = self.app.fastflix.config.opt("resolution_method")
            res_pix = self.app.fastflix.config.opt("resolution_custom")
            if not res_pix:
                matcher = {"method": res_method}
            else:
                matcher = {"method": res_method, "pixels": res_pix}

            if matcher in resolutions.values():
                for k, v in resolutions.items():
                    if v == matcher:
                        self.widgets.resolution_drop_down.setCurrentText(k)
                        break
            else:
                if "pixels" in matcher:
                    del matcher["pixels"]
                    if matcher in resolutions.values():
                        for k, v in resolutions.items():
                            if v == matcher:
                                self.widgets.resolution_drop_down.setCurrentText(k)
                                self.widgets.resolution_custom.setText(str(res_pix))
                                break
                else:
                    self.widgets.resolution_drop_down.setCurrentIndex(0)

            try:
                self.video_options.change_conversion(self.app.fastflix.config.opt("encoder"))
                self.video_options.update_profile()
            except KeyError:
                logger.error(
                    f"Profile not set properly as we don't have encoder: {self.app.fastflix.config.opt('encoder')}"
                )

            self.widgets.remove_hdr.setChecked(self.app.fastflix.config.opt("remove_hdr"))
            # self.widgets.deinterlace.setChecked(self.app.fastflix.config.opt("deinterlace"))
            self.widgets.chapters.setChecked(self.app.fastflix.config.opt("copy_chapters"))
            self.widgets.remove_metadata.setChecked(self.app.fastflix.config.opt("remove_metadata"))

            if self.app.fastflix.current_video:
                self.video_options.new_source()
            self.update_output_type()
        finally:
            # Hack to prevent a lot of thumbnail generation
            self.loading_video = False
        self.page_update()
        # Ensure window stays within screen bounds after profile change
        self.container.ensure_window_in_bounds()

    def save_profile(self):
        self.video_options.get_settings()

    def init_flip(self):
        self.widgets.flip = QtWidgets.QComboBox()
        rotation_folder = "data/rotations/FastFlix"

        ref = importlib.resources.files("fastflix") / f"{rotation_folder}.png"
        with importlib.resources.as_file(ref) as f:
            no_rot_file = str(f.resolve())

        ref = importlib.resources.files("fastflix") / f"{rotation_folder} VF.png"
        with importlib.resources.as_file(ref) as f:
            vert_flip_file = str(f.resolve())

        ref = importlib.resources.files("fastflix") / f"{rotation_folder} HF.png"
        with importlib.resources.as_file(ref) as f:
            hoz_flip_file = str(f.resolve())

        ref = importlib.resources.files("fastflix") / f"{rotation_folder} 180.png"
        with importlib.resources.as_file(ref) as f:
            rot_180_file = str(f.resolve())

        self.widgets.flip.addItems([t("No Flip"), t("V Flip"), t("H Flip"), t("V+H Flip")])
        self.widgets.flip.setItemIcon(0, QtGui.QIcon(no_rot_file))
        self.widgets.flip.setItemIcon(1, QtGui.QIcon(vert_flip_file))
        self.widgets.flip.setItemIcon(2, QtGui.QIcon(hoz_flip_file))
        self.widgets.flip.setItemIcon(3, QtGui.QIcon(rot_180_file))
        self.widgets.flip.setIconSize(scaler.scale_size(ICONS.MEDIUM, ICONS.MEDIUM))
        self.widgets.flip.currentIndexChanged.connect(lambda: self.page_update())
        if self.app.fastflix.config.theme == "onyx":
            self.widgets.flip.setStyleSheet(get_onyx_combobox_style())
        return self.widgets.flip

    def get_flips(self) -> Tuple[bool, bool]:
        mapping = {0: (False, False), 1: (True, False), 2: (False, True), 3: (True, True)}
        return mapping[self.widgets.flip.currentIndex()]

    def flip_to_int(self, vertical_flip: bool, horizontal_flip: bool) -> int:
        mapping = {(False, False): 0, (True, False): 1, (False, True): 2, (True, True): 3}
        return mapping[(vertical_flip, horizontal_flip)]

    def init_rotate(self):
        self.widgets.rotate = QtWidgets.QComboBox()
        rotation_folder = "data/rotations/FastFlix"

        ref = importlib.resources.files("fastflix") / f"{rotation_folder}.png"
        with importlib.resources.as_file(ref) as f:
            no_rot_file = str(f.resolve())

        ref = importlib.resources.files("fastflix") / f"{rotation_folder} C90.png"
        with importlib.resources.as_file(ref) as f:
            rot_90_file = str(f.resolve())

        ref = importlib.resources.files("fastflix") / f"{rotation_folder} CC90.png"
        with importlib.resources.as_file(ref) as f:
            rot_270_file = str(f.resolve())

        ref = importlib.resources.files("fastflix") / f"{rotation_folder} 180.png"
        with importlib.resources.as_file(ref) as f:
            rot_180_file = str(f.resolve())

        self.widgets.rotate.addItems(["0°", "90°", "180°", "270°"])
        self.widgets.rotate.setItemIcon(0, QtGui.QIcon(no_rot_file))
        self.widgets.rotate.setItemIcon(1, QtGui.QIcon(rot_90_file))
        self.widgets.rotate.setItemIcon(2, QtGui.QIcon(rot_180_file))
        self.widgets.rotate.setItemIcon(3, QtGui.QIcon(rot_270_file))
        self.widgets.rotate.setIconSize(scaler.scale_size(ICONS.MEDIUM, ICONS.MEDIUM))
        self.widgets.rotate.currentIndexChanged.connect(lambda: self.page_update())
        if self.app.fastflix.config.theme == "onyx":
            self.widgets.rotate.setStyleSheet(get_onyx_combobox_style())
        return self.widgets.rotate

    def change_output_types(self):
        self.widgets.convert_to.clear()
        self.widgets.convert_to.addItems(self.app.fastflix.encoders.keys())
        for i, plugin in enumerate(self.app.fastflix.encoders.values()):
            if getattr(plugin, "icon", False):
                self.widgets.convert_to.setItemIcon(i, QtGui.QIcon(plugin.icon))
        icon_size = scaler.scale(33) if self.app.fastflix.config.flat_ui else scaler.scale(ICONS.XLARGE)
        self.widgets.convert_to.setIconSize(QtCore.QSize(icon_size, icon_size))

    def init_encoder_drop_down(self):
        layout = QtWidgets.QHBoxLayout()
        self.widgets.convert_to = QtWidgets.QComboBox()
        self.widgets.convert_to.setFixedWidth(scaler.scale(WIDTHS.ENCODER_MIN))
        self.widgets.convert_to.setFixedHeight(scaler.scale(HEIGHTS.TOP_BAR_BUTTON))
        self.widgets.convert_to.setStyleSheet("font-size: 14px;")
        self.change_output_types()
        self.widgets.convert_to.view().setMinimumWidth(
            self.widgets.convert_to.minimumSizeHint().width() + scaler.scale(50)
        )
        self.widgets.convert_to.currentTextChanged.connect(self.change_encoder)

        encoder_label = QtWidgets.QLabel(f"{t('Encoder')}: ")
        encoder_label.setFixedWidth(scaler.scale(54))
        layout.addWidget(self.widgets.convert_to, stretch=0)
        layout.setSpacing(10)

        return layout

    def change_encoder(self):
        if not self.initialized or not self.convert_to:
            return
        self.video_options.change_conversion(self.convert_to, previous_encoder_no_audio=self.previous_encoder_no_audio)
        self.update_output_type()
        self.previous_encoder_no_audio = self.convert_to.lower() in ("copy", "modify", "gif")

    def update_output_type(self):
        self.widgets.output_type_combo.clear()
        self.widgets.output_type_combo.addItems(self.current_encoder.video_extensions)
        self.widgets.output_type_combo.setCurrentText(self.app.fastflix.config.opt("output_type"))

    @property
    def current_encoder(self):
        try:
            return self.app.fastflix.encoders[
                self.app.fastflix.current_video.video_settings.video_encoder_settings.name
            ]
        except (AttributeError, KeyError):
            return self.app.fastflix.encoders[self.convert_to]

    def reset_time(self):
        self.widgets.start_time.setText(self.number_to_time(0))
        self.widgets.end_time.setText(self.number_to_time(self.app.fastflix.current_video.duration))

    def custom_res_update(self):
        self.page_update(build_thumbnail=True)

    def update_resolution(self):
        if self.widgets.resolution_drop_down.currentIndex() == 0:
            self.widgets.resolution_custom.setDisabled(True)
            self.widgets.resolution_custom.setText("")
            self.widgets.resolution_custom.setPlaceholderText(t("Auto"))
        elif self.widgets.resolution_drop_down.currentIndex() in {1, 2, 3, 4}:
            self.widgets.resolution_custom.setDisabled(False)
            self.widgets.resolution_custom.setPlaceholderText(self.widgets.resolution_drop_down.currentText())
            if self.app.fastflix.current_video:
                match resolutions[self.widgets.resolution_drop_down.currentText()]["method"]:
                    case "long edge":
                        self.widgets.resolution_custom.setText(
                            str(self.app.fastflix.current_video.width)
                            if self.app.fastflix.current_video.width > self.app.fastflix.current_video.height
                            else str(self.app.fastflix.current_video.height)
                        )
                    case "width":
                        self.widgets.resolution_custom.setText(str(self.app.fastflix.current_video.width))
                    case "height":
                        self.widgets.resolution_custom.setText(str(self.app.fastflix.current_video.height))
                    case "custom":
                        self.widgets.resolution_custom.setText(
                            f"{self.app.fastflix.current_video.width}:{self.app.fastflix.current_video.height}"
                        )
                    case _:
                        self.widgets.resolution_custom.setText("")
        else:
            self.widgets.resolution_custom.setDisabled(True)
            self.widgets.resolution_custom.setText("")
            self.widgets.resolution_custom.setPlaceholderText(
                str(resolutions[self.widgets.resolution_drop_down.currentText()]["pixels"])
            )

        self.page_update(build_thumbnail=False)

    def update_resolution_labels(self):
        if not self.initialized or not self.app.fastflix.current_video:
            self.widgets.video_res_label.setText(t("Video Resolution") + ": --")
            self.widgets.output_res_label.setText(t("Output Resolution") + ": --")
            return

        src_w = self.app.fastflix.current_video.width
        src_h = self.app.fastflix.current_video.height
        self.widgets.video_res_label.setText(t("Video Resolution") + f": {src_w}w {src_h}h")

        # Start with source dimensions, apply crop
        out_w = src_w
        out_h = src_h
        try:
            crop_top = int(self.widgets.crop.top.text() or 0)
            crop_bottom = int(self.widgets.crop.bottom.text() or 0)
            crop_left = int(self.widgets.crop.left.text() or 0)
            crop_right = int(self.widgets.crop.right.text() or 0)
            out_w -= crop_left + crop_right
            out_h -= crop_top + crop_bottom
        except (ValueError, AttributeError):
            pass

        if out_w <= 0 or out_h <= 0:
            self.widgets.output_res_label.setText(t("Output Resolution") + ": --")
            return

        # Apply scale based on resolution method
        method = self.resolution_method()
        custom = self.resolution_custom()

        if method != "auto" and custom:
            try:
                if method == "custom":
                    parts = custom.split(":")
                    if len(parts) == 2:
                        cw, ch = int(parts[0]), int(parts[1])
                        if cw > 0 and ch > 0:
                            out_w, out_h = cw, ch
                elif method == "width":
                    new_w = int(custom)
                    out_h = ((out_h * new_w // out_w) // 8) * 8
                    out_w = new_w
                elif method == "height":
                    new_h = int(custom)
                    out_w = ((out_w * new_h // out_h) // 8) * 8
                    out_h = new_h
                elif method == "long edge":
                    pixels = int(custom)
                    if out_w >= out_h:
                        out_h = ((out_h * pixels // out_w) // 8) * 8
                        out_w = pixels
                    else:
                        out_w = ((out_w * pixels // out_h) // 8) * 8
                        out_h = pixels
            except (ValueError, ZeroDivisionError):
                pass

        self.widgets.output_res_label.setText(t("Output Resolution") + f": {out_w}w {out_h}h")

    def reset_crop(self):
        self.loading_video = True
        self.widgets.crop.top.setText("0")
        self.widgets.crop.left.setText("0")
        self.widgets.crop.right.setText("0")
        self.loading_video = False
        self.widgets.crop.bottom.setText("0")

    @staticmethod
    def toggle_disable(widget_list):
        for widget in widget_list:
            widget.setDisabled(widget.isEnabled())

    # @property
    # def title(self):
    #     return self.widgets.video_title.text()

    def build_hoz_int_field(
        self,
        name,
        button_size=28,
        left_stretch=True,
        right_stretch=True,
        layout=None,
        return_buttons=False,
        time_field=False,
        right_side_label=False,
    ):
        scaled_button_size = scaler.scale(button_size)
        widget = QtWidgets.QLineEdit(self.number_to_time(0) if time_field else "0")
        widget.setObjectName(name)
        if not time_field:
            widget.setValidator(only_int)
        widget.setFixedHeight(scaled_button_size)
        if not layout:
            layout = QtWidgets.QHBoxLayout()
            layout.setSpacing(0)
        if left_stretch:
            layout.addStretch(1)
        layout.addWidget(QtWidgets.QLabel(name))
        minus_button = QtWidgets.QPushButton("-")
        minus_button.setAutoRepeat(True)
        minus_button.setFixedSize(QtCore.QSize(scaled_button_size - scaler.scale(4), scaled_button_size))
        minus_button.setStyleSheet("padding: 0; border: none;")
        minus_button.clicked.connect(
            lambda: [
                self.modify_int(widget, "minus", time_field),
                self.page_update(),
            ]
        )
        plus_button = QtWidgets.QPushButton("+")
        plus_button.setAutoRepeat(True)
        plus_button.setFixedSize(scaled_button_size, scaled_button_size)
        plus_button.setStyleSheet("padding: 0; border: none;")
        plus_button.clicked.connect(
            lambda: [
                self.modify_int(widget, "add", time_field),
                self.page_update(),
            ]
        )
        self.buttons.append(minus_button)
        self.buttons.append(plus_button)
        if not time_field:
            widget.setFixedWidth(scaler.scale(38))
        else:
            widget.setFixedWidth(scaler.scale(79))
        widget.setStyleSheet("text-align: center")
        layout.addWidget(minus_button)
        layout.addWidget(widget)
        layout.addWidget(plus_button)
        if right_stretch:
            layout.addStretch(1)
        if return_buttons:
            return widget, layout, minus_button, plus_button
        return widget, layout

    def init_preview_image(self):
        class PreviewImage(QtWidgets.QLabel):
            def __init__(self, parent):
                super().__init__()
                self.main = parent
                self._original_pixmap = None
                self.setBackgroundRole(QtGui.QPalette.Base)
                self.setAlignment(QtCore.Qt.AlignCenter)
                self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
                self._update_scaled_sizes()
                # Register for scale factor changes
                scaler.add_listener(self._on_scale_changed)

            def _update_scaled_sizes(self):
                """Update minimum size, cursor, and stylesheet based on current scale factors."""
                self.setMinimumSize(scaler.scale(WIDTHS.PREVIEW_MIN), scaler.scale(HEIGHTS.PREVIEW_MIN))
                self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
                border_width = scaler.scale(2)
                margin = scaler.scale(7)
                self.setStyleSheet(f"border: {border_width}px solid {ONYX_COLORS['primary']}; margin: {margin}px;")

            def _on_scale_changed(self, factors):
                """Called when scale factors change."""
                self._update_scaled_sizes()
                self._update_scaled_pixmap()

            def setPixmap(self, pixmap):
                self._original_pixmap = pixmap
                self._update_scaled_pixmap()

            def _update_scaled_pixmap(self):
                if self._original_pixmap is None or self._original_pixmap.isNull():
                    super(PreviewImage, self).setPixmap(QtGui.QPixmap())
                    return
                # Scale pixmap to fit widget while maintaining aspect ratio
                scaled = self._original_pixmap.scaled(
                    self.size(),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation,
                )
                super(PreviewImage, self).setPixmap(scaled)

            def resizeEvent(self, event):
                self._update_scaled_pixmap()
                super(PreviewImage, self).resizeEvent(event)

            def mousePressEvent(self, QMouseEvent):
                if not self.main.initialized or not self.main.app.fastflix.current_video:
                    return
                self.main.widgets.thumb_time.setFocus()
                super(PreviewImage, self).mousePressEvent(QMouseEvent)

        # Create container widget to hold preview image and overlay slider
        class PreviewContainer(QtWidgets.QWidget):
            def __init__(self, main_widget):
                super().__init__()
                self.main_widget = main_widget
                self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)

            def resizeEvent(self, event):
                super().resizeEvent(event)
                self.main_widget.reposition_thumb_overlay()

            def showEvent(self, event):
                super().showEvent(event)
                self.main_widget.reposition_thumb_overlay()

        self.preview_container = PreviewContainer(self)

        # Use a stacked layout approach with a QVBoxLayout and overlay
        container_layout = QtWidgets.QVBoxLayout(self.preview_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        self.widgets.preview = PreviewImage(self)
        container_layout.addWidget(self.widgets.preview)

        # Create the slider overlay and position it at the bottom
        self.thumb_time_overlay = self.init_thumb_time_selector()
        self.thumb_time_overlay.setParent(self.preview_container)
        self.thumb_time_overlay.raise_()

        # Large preview button at top right
        self.large_preview_button = QtWidgets.QPushButton(self.preview_container)
        btn_size = scaler.scale(24)
        self.large_preview_button.setFixedSize(btn_size, btn_size)
        self.large_preview_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DesktopIcon))
        self.large_preview_button.setToolTip(t("Large Preview"))
        self.large_preview_button.clicked.connect(self.open_large_preview)
        self.large_preview_button.setStyleSheet(
            "QPushButton { background: rgba(0,0,0,128); border: none; border-radius: 4px; }"
            "QPushButton:hover { background: rgba(0,0,0,180); }"
        )
        self.large_preview_button.raise_()

        return self.preview_container

    def open_large_preview(self):
        if not self.initialized or not self.app.fastflix.current_video or self.large_preview.isVisible():
            return
        self.large_preview.generate_image()
        self.large_preview.show()

    def reposition_thumb_overlay(self):
        """Reposition the thumb time overlay and large preview button."""
        if hasattr(self, "thumb_time_overlay") and hasattr(self, "preview_container"):
            container_rect = self.preview_container.rect()
            overlay_height = self.thumb_time_overlay.height()
            margin = scaler.scale(15)
            self.thumb_time_overlay.setGeometry(
                margin,
                container_rect.height() - overlay_height - margin,
                container_rect.width() - (2 * margin),
                overlay_height,
            )
        if hasattr(self, "large_preview_button") and hasattr(self, "preview_container"):
            btn_margin = scaler.scale(15)
            btn_size = self.large_preview_button.width()
            self.large_preview_button.move(
                self.preview_container.width() - btn_size - btn_margin,
                btn_margin,
            )

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
            " *.wmv *.mov *.qt *.flv *.hevc *.gif *.webp *.vob *.ogv *.ts *.mts *.m2ts *.yuv *.rm *.svi *.3gp *.3g2"
            " *.y4m *.avs *.vpy);;"
            "Concatenation Text File (*.txt *.concat);; All Files (*)",
            dir=str(
                self.app.fastflix.config.source_directory
                or (self.app.fastflix.current_video.source.parent if self.app.fastflix.current_video else Path.home())
            ),
        )
        if not filename or not filename[0]:
            return

        if self.app.fastflix.current_video:
            discard = yes_no_message(
                f"{t('There is already a video being processed')}<br>{t('Are you sure you want to discard it?')}",
                title="Discard current video",
            )
            if not discard:
                return

        self.input_video = Path(clean_file_string(filename[0]))
        if not self.input_video.exists():
            logger.error(f"Could not find the input file, does it exist at: {self.input_video}")
            return
        self.source_video_path_widget.setText(str(self.input_video))
        self.video_path_widget.setText(str(self.input_video))
        try:
            self.update_video_info()
        except Exception:
            logger.exception(f"Could not load video {self.input_video}")
            self.video_path_widget.setText("")
            self.output_video_path_widget.setText("")
            self.output_video_path_widget.setDisabled(True)
            self.widgets.output_directory.setText("")
            self.output_path_button.setDisabled(True)
        self.page_update()

    def open_many(self, paths: list):
        if self.app.fastflix.current_video:
            discard = yes_no_message(
                f"{t('There is already a video being processed')}<br>{t('Are you sure you want to discard it?')}",
                title="Discard current video",
            )
            if not discard:
                return

        def open_em(signal, stop_signal, paths, **_):
            stop = False

            def stop_me():
                nonlocal stop
                stop = True

            stop_signal.connect(stop_me)

            total_items = len(paths)
            for i, path in enumerate(paths):
                if stop:
                    return
                self.input_video = path
                self.source_video_path_widget.setText(str(self.input_video))
                self.video_path_widget.setText(str(self.input_video))
                try:
                    self.update_video_info(hide_progress=True)
                except Exception:
                    logger.exception(f"Could not load video {self.input_video}")
                else:
                    self.page_update(build_thumbnail=False)
                    self.add_to_queue()
                signal.emit(int((i / total_items) * 100))

        self.disable_all()
        ProgressBar(self.app, [Task(t("Loading Videos"), open_em, {"paths": paths})], signal_task=True, can_cancel=True)
        self.enable_all()

    @property
    def generate_output_filename(self):
        source = self.input_video.stem
        iso_datetime = datetime.datetime.now().isoformat().replace(":", "-").split(".")[0]
        rand_4 = secrets.token_hex(2)
        rand_8 = secrets.token_hex(4)
        out_loc = f"{Path('~').expanduser()}{os.sep}"
        if tx := self.widgets.output_directory.text():
            out_loc = f"{tx}{os.sep}"
        if self.input_video:
            out_loc = f"{self.input_video.parent}{os.sep}"
        if self.app.fastflix.config.output_directory:
            out_loc = f"{self.app.fastflix.config.output_directory}{os.sep}"

        gen_string = self.app.fastflix.config.output_name_format or "{source}-fastflix-{rand_4}"

        return out_loc, gen_string.format(source=source, datetime=iso_datetime, rand_4=rand_4, rand_8=rand_8, ext="")

    @property
    def output_video(self):
        return clean_file_string(
            Path(
                self.widgets.output_directory.text(),
                f"{self.output_video_path_widget.text()}{self.widgets.output_type_combo.currentText()}",
            )
        )

    @reusables.log_exception("fastflix", show_traceback=False)
    def save_file(self, extension="mkv"):
        filename = QtWidgets.QFileDialog.getSaveFileName(
            self,
            caption="Save Video As",
            dir=str(Path(*self.generate_output_filename)) + f"{self.widgets.output_type_combo.currentText()}",
            filter=f"Save File (*.{extension})",
        )
        if filename and filename[0]:
            fn = Path(filename[0])
            self.widgets.output_directory.setText(str(fn.parent.absolute()).rstrip("/").rstrip("\\"))
            self.output_video_path_widget.setText(fn.stem)
            self.widgets.output_type_combo.setCurrentText(fn.suffix)

    def save_directory(self):
        dirname = QtWidgets.QFileDialog.getExistingDirectory(
            caption="Save Directory",
            dir=str(self.generate_output_filename[0]),
        )
        if dirname:
            self.widgets.output_directory.setText(dirname.rstrip("/").rstrip("\\"))

    def get_auto_crop(self):
        if not self.input_video or not self.initialized or self.loading_video:
            return

        start_pos = self.start_time or self.app.fastflix.current_video.duration // 10

        blocks = math.ceil(
            (self.app.fastflix.current_video.duration - start_pos) / (self.app.fastflix.config.crop_detect_points + 1)
        )
        if blocks < 1:
            blocks = 1

        times = [
            x
            for x in range(int(start_pos), int(self.app.fastflix.current_video.duration), blocks)
            if x < self.app.fastflix.current_video.duration
        ][: self.app.fastflix.config.crop_detect_points]

        if not times:
            return

        self.app.processEvents()
        result_list = []
        tasks = [
            Task(
                f"{t('Auto Crop - Finding black bars at')} {self.number_to_time(x)}",
                get_auto_crop,
                dict(
                    source=self.source_material,
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
        if not result_list:
            logger.warning("Autocrop did not return crop points, please use a ffmpeg version with cropdetect filter")
            return

        smallest = (self.app.fastflix.current_video.height + self.app.fastflix.current_video.width) * 2
        selected = result_list[0]
        for result in result_list:
            if (total := sum(result)) < smallest:
                selected = result
                smallest = total

        r, b, l, tp = selected  # noqa: E741

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

    def build_crop(self) -> Union[Crop, None]:
        if not self.initialized or not self.app.fastflix.current_video:
            return None
        try:
            crop = Crop(
                top=int(self.widgets.crop.top.text()),
                left=int(self.widgets.crop.left.text()),
                right=int(self.widgets.crop.right.text()),
                bottom=int(self.widgets.crop.bottom.text()),
            )
        except (ValueError, AttributeError):
            logger.error("Invalid crop")
            return None
        else:
            crop.width = self.app.fastflix.current_video.width - crop.right - crop.left
            crop.height = self.app.fastflix.current_video.height - crop.bottom - crop.top
            if (crop.top + crop.left + crop.right + crop.bottom) == 0:
                return None
            try:
                assert crop.top >= 0, t("Top must be positive number")
                assert crop.height > 0, t("Total video height must be greater than 0")
                assert crop.height <= self.app.fastflix.current_video.height, t(
                    "Height must be smaller than video height"
                )
            except AssertionError as err:
                logger.warning(f"{t('Invalid Crop')}: {err}")
                self.widgets.crop.top.setStyleSheet("color: red")
                self.widgets.crop.bottom.setStyleSheet("color: red")
                return None
            try:
                assert crop.left >= 0, t("Left must be positive number")
                assert crop.width > 0, t("Total video width must be greater than 0")

                assert crop.width <= self.app.fastflix.current_video.width, t("Width must be smaller than video width")

            except AssertionError as err:
                logger.warning(f"{t('Invalid Crop')}: {err}")
                self.widgets.crop.left.setStyleSheet("color: red")
                self.widgets.crop.right.setStyleSheet("color: red")
                # error_message(f"{t('Invalid Crop')}: {err}")
                return None
            crop_text_color = "color: white" if self.app.fastflix.config.theme in ("dark", "onyx") else "color: black"
            self.widgets.crop.left.setStyleSheet(crop_text_color)
            self.widgets.crop.right.setStyleSheet(crop_text_color)
            self.widgets.crop.top.setStyleSheet(crop_text_color)
            self.widgets.crop.bottom.setStyleSheet(crop_text_color)
            return crop

    def disable_all(self):
        for name, widget in self.widgets.items():
            if name in ("preview", "convert_button", "pause_resume", "convert_to", "profile_box"):
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
        self.add_profile.setDisabled(True)

    def enable_all(self):
        for name, widget in self.widgets.items():
            if name in {"preview", "convert_button", "pause_resume", "convert_to", "profile_box"}:
                continue
            if isinstance(widget, dict):
                for sub_widget in widget.values():
                    if isinstance(sub_widget, QtWidgets.QWidget):
                        sub_widget.setEnabled(True)
            elif isinstance(widget, QtWidgets.QWidget):
                widget.setEnabled(True)
        for button in self.buttons:
            button.setEnabled(True)
        self.output_path_button.setEnabled(True)
        self.output_video_path_widget.setEnabled(True)
        self.add_profile.setEnabled(True)
        self.update_resolution()

    def clear_current_video(self):
        self.loading_video = True
        self.app.fastflix.current_video = None
        self.input_video = None
        self.source_video_path_widget.setText("")
        self.video_path_widget.setText(t("No Source Selected"))
        self.output_video_path_widget.setText("")
        self.widgets.output_directory.setText("")
        self.output_path_button.setDisabled(True)
        self.output_video_path_widget.setDisabled(True)
        for i in range(self.widgets.video_track.count()):
            self.widgets.video_track.removeItem(0)
        self.widgets.preview.setText(t("No Video File"))

        # self.widgets.deinterlace.setChecked(False)
        # self.widgets.remove_hdr.setChecked(False)
        # self.widgets.remove_metadata.setChecked(True)
        # self.widgets.chapters.setChecked(True)

        self.widgets.flip.setCurrentIndex(0)
        self.widgets.rotate.setCurrentIndex(0)
        # self.widgets.video_title.setText("")

        self.widgets.crop.top.setText("0")
        self.widgets.crop.left.setText("0")
        self.widgets.crop.right.setText("0")
        self.widgets.crop.bottom.setText("0")
        self.widgets.start_time.setText(self.number_to_time(0))
        self.widgets.end_time.setText(self.number_to_time(0))
        # self.widgets.scale.width.setText("0")
        # self.widgets.scale.height.setText("Auto")
        self.widgets.preview.setPixmap(QtGui.QPixmap())
        self.video_options.clear_tracks()
        self.video_bit_depth_label.hide()
        self.video_chroma_label.hide()
        self.video_hdr10_label.hide()
        self.video_hdr10plus_label.hide()
        self.disable_all()
        self.loading_video = False

    @reusables.log_exception("fastflix", show_traceback=True)
    def reload_video_from_queue(self, video: Video):
        if video.video_settings.video_encoder_settings.name not in self.app.fastflix.encoders:
            error_message(
                t("That video was added with an encoder that is no longer available, unable to load from queue")
            )
            raise FastFlixInternalException(
                t("That video was added with an encoder that is no longer available, unable to load from queue")
            )

        self.loading_video = True

        self.app.fastflix.current_video = video
        self.app.fastflix.current_video.work_path.mkdir(parents=True, exist_ok=True)
        extract_attachments(app=self.app)
        self.input_video = video.source
        self.source_video_path_widget.setText(str(self.input_video))
        hdr10_indexes = [x.index for x in self.app.fastflix.current_video.hdr10_streams]
        text_video_tracks = [
            (
                f"{x.index}: {x.codec_name} {x.get('bit_depth', '8')}-bit "
                f"{x['color_primaries'] if x.get('color_primaries') else ''}"
                f"{' - HDR10' if x.index in hdr10_indexes else ''}"
                f"{' | HDR10+' if x.index in self.app.fastflix.current_video.hdr10_plus else ''}"
            )
            for x in self.app.fastflix.current_video.streams.video
        ]
        self.widgets.video_track.clear()
        self.widgets.video_track.addItems(text_video_tracks)
        # Show video track selector only when there's more than one video track
        if len(self.app.fastflix.current_video.streams.video) > 1:
            self.widgets.video_track_widget.show()
        else:
            self.widgets.video_track_widget.hide()
        for i, track in enumerate(text_video_tracks):
            if int(track.split(":")[0]) == self.app.fastflix.current_video.video_settings.selected_track:
                self.widgets.video_track.setCurrentIndex(i)
                break
        else:
            logger.warning(
                f"Could not find selected track {self.app.fastflix.current_video.video_settings.selected_track} "
                f"in {text_video_tracks}"
            )

        end_time = self.app.fastflix.current_video.video_settings.end_time or video.duration
        if self.app.fastflix.current_video.video_settings.crop:
            self.widgets.crop.top.setText(str(self.app.fastflix.current_video.video_settings.crop.top))
            self.widgets.crop.left.setText(str(self.app.fastflix.current_video.video_settings.crop.left))
            self.widgets.crop.right.setText(str(self.app.fastflix.current_video.video_settings.crop.right))
            self.widgets.crop.bottom.setText(str(self.app.fastflix.current_video.video_settings.crop.bottom))
        else:
            self.widgets.crop.top.setText("0")
            self.widgets.crop.left.setText("0")
            self.widgets.crop.right.setText("0")
            self.widgets.crop.bottom.setText("0")
        self.widgets.start_time.setText(self.number_to_time(video.video_settings.start_time))
        self.widgets.end_time.setText(self.number_to_time(end_time))
        # self.widgets.video_title.setText(self.app.fastflix.current_video.video_settings.video_title)

        fn = Path(video.video_settings.output_path)
        self.widgets.output_directory.setText(str(fn.parent.absolute()).rstrip("/").rstrip("\\"))
        self.output_video_path_widget.setText(fn.stem)
        self.widgets.output_type_combo.setCurrentText(fn.suffix)

        self.widgets.deinterlace.setChecked(self.app.fastflix.current_video.video_settings.deinterlace)
        self.widgets.remove_metadata.setChecked(self.app.fastflix.current_video.video_settings.remove_metadata)
        self.widgets.chapters.setChecked(self.app.fastflix.current_video.video_settings.copy_chapters)
        self.widgets.remove_hdr.setChecked(self.app.fastflix.current_video.video_settings.remove_hdr)
        self.widgets.rotate.setCurrentIndex(video.video_settings.rotate)
        self.widgets.fast_time.setCurrentIndex(0 if video.video_settings.fast_seek else 1)
        if video.video_settings.vertical_flip and video.video_settings.horizontal_flip:
            self.widgets.flip.setCurrentIndex(3)
        elif video.video_settings.vertical_flip:
            self.widgets.flip.setCurrentIndex(1)
        elif video.video_settings.horizontal_flip:
            self.widgets.flip.setCurrentIndex(2)

        self.video_options.advanced.video_title.setText(video.video_settings.video_title)
        self.video_options.advanced.video_track_title.setText(video.video_settings.video_track_title)

        self.video_options.reload()
        self.enable_all()

        self.app.fastflix.current_video.status = Status()
        self.update_video_info_labels()
        self.loading_video = False
        self.page_update(build_thumbnail=True, force_build_thumbnail=True)

    @reusables.log_exception("fastflix", show_traceback=False)
    def update_video_info(self, hide_progress=False):
        self.loading_video = True
        folder, name = self.generate_output_filename
        self.output_video_path_widget.setText(name)
        self.widgets.output_directory.setText(folder.rstrip("/").rstrip("\\"))
        self.output_video_path_widget.setDisabled(False)
        self.output_path_button.setDisabled(False)
        self.app.fastflix.current_video = Video(source=self.input_video, work_path=self.get_temp_work_path())
        tasks = [
            Task(t("Parse Video details"), parse),
            Task(t("Extract covers"), extract_attachments),
            Task(t("Determine HDR details"), parse_hdr_details),
            Task(t("Detect HDR10+"), detect_hdr10_plus),
        ]
        if not self.app.fastflix.config.disable_deinterlace_check:
            tasks.append(Task(t("Detecting Interlace"), detect_interlaced, dict(source=self.source_material)))

        try:
            ProgressBar(self.app, tasks, hidden=hide_progress)
        except FlixError:
            error_message(f"{t('Not a video file')}<br>{self.input_video}")
            self.clear_current_video()
            return
        except Exception:
            logger.exception(f"Could not properly read the files {self.input_video}")
            self.clear_current_video()
            error_message(f"Could not properly read the file {self.input_video}")
            return

        hdr10_indexes = [x.index for x in self.app.fastflix.current_video.hdr10_streams]
        text_video_tracks = [
            (
                f"{x.index}: {x.codec_name} {x.get('bit_depth', '8')}-bit "
                f"{x['color_primaries'] if x.get('color_primaries') else ''}"
                f"{' - HDR10' if x.index in hdr10_indexes else ''}"
                f"{' | HDR10+' if x.index in self.app.fastflix.current_video.hdr10_plus else ''}"
            )
            for x in self.app.fastflix.current_video.streams.video
        ]
        self.widgets.video_track.clear()
        self.widgets.crop.top.setText("0")
        self.widgets.crop.left.setText("0")
        self.widgets.crop.right.setText("0")
        self.widgets.crop.bottom.setText("0")
        self.widgets.start_time.setText("0:00:00")

        self.widgets.video_track.addItems(text_video_tracks)

        # Show video track selector only when there's more than one video track
        if len(self.app.fastflix.current_video.streams.video) > 1:
            self.widgets.video_track_widget.show()
        else:
            self.widgets.video_track_widget.hide()

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
            self.video_options.advanced.video_title.setText(title_name[0])
        else:
            self.video_options.advanced.video_title.setText("")

        video_track_title_name = [
            v
            for k, v in self.app.fastflix.current_video.streams.video[0].get("tags", {}).items()
            if k.upper() == "TITLE"
        ]

        if video_track_title_name:
            self.video_options.advanced.video_track_title.setText(video_track_title_name[0])
        else:
            self.video_options.advanced.video_track_title.setText("")

        self.widgets.deinterlace.setChecked(self.app.fastflix.current_video.video_settings.deinterlace)

        logger.info("Updating video info")
        self.video_options.new_source()
        self.enable_all()
        # self.widgets.convert_button.setDisabled(False)
        # self.widgets.convert_button.setStyleSheet("background-color:green;")

        self.loading_video = False
        self.update_resolution_labels()
        self.update_video_info_labels()

        # Set preview slider steps: ~1 per 10 seconds, minimum 100
        slider_steps = max(100, int(self.app.fastflix.current_video.duration / 10))
        self.widgets.thumb_time.setMaximum(slider_steps)
        self.widgets.thumb_time.setPageStep(max(1, slider_steps // 20))
        self.widgets.thumb_time.setValue(max(1, slider_steps // 4))

        if self.app.fastflix.config.opt("auto_crop"):
            self.get_auto_crop()

        if not getattr(self.current_encoder, "enable_concat", False) and self.app.fastflix.current_video.concat:
            error_message(f"{self.current_encoder.name} {t('does not support concatenating files together')}")

    @staticmethod
    def _chroma_from_pix_fmt(pix_fmt: str) -> str:
        if not pix_fmt:
            return ""
        fmt = pix_fmt.lower()
        if "444" in fmt:
            return "4:4:4"
        if "422" in fmt:
            return "4:2:2"
        if "420" in fmt or fmt in ("nv12", "nv12m", "nv21", "p010le"):
            return "4:2:0"
        if "411" in fmt:
            return "4:1:1"
        if "410" in fmt:
            return "4:1:0"
        if "440" in fmt:
            return "4:4:0"
        return ""

    def update_video_info_labels(self):
        if not self.app.fastflix.current_video:
            self.video_info_label.hide()
            self.video_bit_depth_label.hide()
            self.video_chroma_label.hide()
            self.video_hdr10_label.hide()
            self.video_hdr10plus_label.hide()
            return

        track_index = self.widgets.video_track.currentIndex()
        if track_index < 0:
            return
        stream = self.app.fastflix.current_video.streams.video[track_index]
        stream_idx = stream.index

        bit_depth = stream.get("bit_depth", "8")
        self.video_bit_depth_label.setText(f"{bit_depth}-bit")
        self.video_bit_depth_label.show()
        self.video_info_label.show()

        chroma = self._chroma_from_pix_fmt(stream.get("pix_fmt", ""))
        if chroma:
            self.video_chroma_label.setText(chroma)
            self.video_chroma_label.show()
        else:
            self.video_chroma_label.hide()

        hdr10_indexes = [x.index for x in self.app.fastflix.current_video.hdr10_streams]
        if stream_idx in hdr10_indexes:
            self.video_hdr10_label.setText("\u2714 HDR10")
            self.video_hdr10_label.setStyleSheet("color: #00cc00;")
            self.video_hdr10_label.show()
        else:
            self.video_hdr10_label.hide()

        if self.app.fastflix.config.hdr10plus_parser and stream_idx in self.app.fastflix.current_video.hdr10_plus:
            self.video_hdr10plus_label.setText("\u2714 HDR10+")
            self.video_hdr10plus_label.setStyleSheet("color: #00cc00;")
            self.video_hdr10plus_label.show()
        else:
            self.video_hdr10plus_label.hide()

    @property
    def video_track(self) -> int:
        return self.widgets.video_track.currentIndex()

    @property
    def original_video_track(self) -> int:
        if not self.app.fastflix.current_video or not self.widgets.video_track.currentText():
            return 0
        try:
            return int(self.widgets.video_track.currentText().split(":", 1)[0])
        except Exception:
            logger.exception("Could not get original_video_track")
            return 0

    @property
    def pix_fmt(self) -> str:
        return self.app.fastflix.current_video.streams.video[self.video_track].pix_fmt

    @staticmethod
    def number_to_time(number) -> str:
        return str(timedelta(seconds=round(number, 2)))[:10]

    def set_time_from_preview(self, widget):
        if not self.app.fastflix.current_video:
            return
        widget.setText(self.number_to_time(self.preview_place))

    @property
    def start_time(self) -> float:
        return time_to_number(self.widgets.start_time.text())

    @property
    def end_time(self) -> float:
        return time_to_number(self.widgets.end_time.text())

    @property
    def fast_time(self) -> bool:
        return self.widgets.fast_time.currentIndex() == 0

    @property
    def remove_metadata(self) -> bool:
        return self.widgets.remove_metadata.isChecked()

    @property
    def copy_chapters(self) -> bool:
        return self.widgets.chapters.isChecked()

    @property
    def remove_hdr(self) -> bool:
        return self.widgets.remove_hdr.isChecked()

    @property
    def preview_place(self) -> Union[float, int]:
        ticks = self.app.fastflix.current_video.duration / self.widgets.thumb_time.maximum()
        return (self.widgets.thumb_time.value() - 1) * ticks

    @reusables.log_exception("fastflix", show_traceback=False)
    def generate_thumbnail(self):
        if not self.input_video or self.loading_video:
            return

        settings = self.app.fastflix.current_video.video_settings.model_dump()

        if (
            self.app.fastflix.current_video.video_settings.video_encoder_settings.pix_fmt == "yuv420p10le"
            and self.app.fastflix.current_video.color_space.startswith("bt2020")
        ):
            settings["remove_hdr"] = True
            if not settings.get("color_transfer"):
                settings["color_transfer"] = self.app.fastflix.current_video.color_transfer

        custom_filters = "scale='min(440\\,iw):-8'"
        if self.resolution_method() == "custom":
            custom_filters = f"scale={self.resolution_custom()},setsar=1:1"

        # if self.app.fastflix.current_video.color_transfer == "arib-std-b67":
        #     custom_filters += ",select=eq(pict_type\\,I)"

        use_keyframes = (
            self.app.fastflix.config.use_keyframes_for_preview and self.app.fastflix.current_video.duration >= 60
        )
        filters = helpers.generate_filters(
            start_filters="select=eq(pict_type\\,I)" if use_keyframes else None,
            custom_filters=custom_filters,
            enable_opencl=False,
            **settings,
        )

        thumb_command = generate_thumbnail_command(
            config=self.app.fastflix.config,
            source=self.source_material,
            output=self.thumb_file,
            filters=filters,
            start_time=self.preview_place if not self.app.fastflix.current_video.concat else None,
            input_track=self.app.fastflix.current_video.video_settings.selected_track,
        )
        try:
            self.thumb_file.unlink()
        except OSError:
            pass
        worker = ThumbnailCreator(self, thumb_command)
        worker.start()

    @property
    def source_material(self):
        if self.app.fastflix.current_video.concat:
            return get_concat_item(self.input_video, self.widgets.thumb_time.value())
        return self.input_video

    @staticmethod
    def thread_logger(text):
        try:
            level, msg = text.split(":", 1)
            logger.log(["", "debug", "info", "warning", "error", "critical"].index(level.lower()) * 10, msg)
        except Exception:
            logger.warning(text)

    @reusables.log_exception("fastflix", show_traceback=False)
    def thumbnail_generated(self, status=0):
        if status == 2:
            self.app.fastflix.opencl_support = False
            self.generate_thumbnail()
            return
        if status == 0 or not status or not self.thumb_file.exists():
            self.widgets.preview.setText(t("Error Updating Thumbnail"))
            return

        pixmap = QtGui.QPixmap(str(self.thumb_file))
        pixmap = pixmap.scaled(420, 260, QtCore.Qt.KeepAspectRatio)
        self.widgets.preview.setPixmap(pixmap)

    def resolution_method(self):
        return resolutions[self.widgets.resolution_drop_down.currentText()]["method"]

    def resolution_custom(self):
        res = resolutions[self.widgets.resolution_drop_down.currentText()]
        if "pixels" in res:
            return str(res["pixels"])
        if self.widgets.resolution_custom.text().strip():
            return self.widgets.resolution_custom.text()

    def get_all_settings(self):
        if not self.initialized:
            return

        end_time = self.end_time
        if self.end_time == float(self.app.fastflix.current_video.format.get("duration", 0)):
            end_time = 0
        if self.end_time and (self.end_time - 0.1 <= self.app.fastflix.current_video.duration <= self.end_time + 0.1):
            end_time = 0

        v_flip, h_flip = self.get_flips()

        del self.app.fastflix.current_video.video_settings
        self.app.fastflix.current_video.video_settings = VideoSettings(
            crop=self.build_crop(),
            resolution_method=self.resolution_method(),
            resolution_custom=self.resolution_custom(),
            start_time=self.start_time,
            end_time=end_time,
            selected_track=self.original_video_track,
            fast_seek=self.fast_time,
            rotate=self.widgets.rotate.currentIndex(),
            vertical_flip=v_flip,
            horizontal_flip=h_flip,
            output_path=Path(clean_file_string(self.output_video)),
            deinterlace=self.widgets.deinterlace.isChecked(),
            remove_metadata=self.remove_metadata,
            copy_chapters=self.copy_chapters,
            video_title=self.video_options.advanced.video_title.text(),
            video_track_title=self.video_options.advanced.video_track_title.text(),
            remove_hdr=self.remove_hdr,
            # copy_data=self.widgets.copy_data.isChecked(),
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

    def hdr_update(self):
        self.video_options.advanced.hdr_settings()
        self.encoder_settings_update()

    def video_track_update(self):
        if not self.app.fastflix.current_video or self.loading_video:
            return
        self.loading_video = True
        self.app.fastflix.current_video.video_settings.selected_track = self.original_video_track
        self.widgets.crop.top.setText("0")
        self.widgets.crop.left.setText("0")
        self.widgets.crop.right.setText("0")
        self.widgets.crop.bottom.setText("0")
        # self.widgets.scale.width.setText(str(self.app.fastflix.current_video.width))
        # self.widgets.scale.height.setText(str(self.app.fastflix.current_video.height))
        self.loading_video = False
        self.page_update(build_thumbnail=True)

    def page_update(self, build_thumbnail=True, force_build_thumbnail=False):
        while self.page_updating:
            time.sleep(0.1)
        self.page_updating = True
        try:
            if not self.initialized or self.loading_video or not self.app.fastflix.current_video:
                return
            self.last_page_update = time.time()
            self.update_resolution_labels()
            self.video_options.refresh()
            self.build_commands()
            if build_thumbnail:
                new_hash = (
                    f"{self.build_crop()}:{self.resolution_custom()}:{self.start_time}:{self.end_time}:"
                    f"{self.app.fastflix.current_video.video_settings.selected_track}:"
                    f"{int(self.remove_hdr)}:{self.preview_place}:{self.widgets.rotate.currentIndex()}:"
                    f"{self.widgets.flip.currentIndex()}"
                )
                if new_hash == self.last_thumb_hash and not force_build_thumbnail:
                    return
                self.last_thumb_hash = new_hash
                self.generate_thumbnail()
        finally:
            self.page_updating = False

    def close(self, no_cleanup=False, from_container=False):
        self.app.fastflix.shutting_down = True

        # Signal worker process to shutdown gracefully
        try:
            self.app.fastflix.worker_queue.put(["shutdown"])
        except Exception:
            logger.debug("Could not send shutdown signal to worker")

        # Shutdown async queue saver and wait for pending saves
        from fastflix.ff_queue import shutdown_async_saver

        shutdown_async_saver(timeout=5.0)

        if not no_cleanup:
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            except Exception:
                pass
        self.video_options.cleanup()
        self.notifier.request_shutdown()
        self.notifier.wait(1000)  # Wait up to 1 second for graceful shutdown
        if self.notifier.isRunning():
            self.notifier.terminate()
        super().close()
        if not from_container:
            self.container.close()

    @property
    def convert_to(self):
        if self.widgets.convert_to:
            return self.widgets.convert_to.currentText().strip()
        return list(self.app.fastflix.encoders.keys())[0]

    def encoding_checks(self):
        if not self.input_video:
            error_message(t("Have to select a video first"))
            return False
        if not self.output_video:
            error_message(t("Please specify output video"))
            return False
        try:
            if self.input_video.resolve().absolute() == Path(self.output_video).resolve().absolute():
                error_message(t("Output video path is same as source!"))
                return False
        except OSError:
            # file system may not support resolving
            pass

        out_file_path = Path(self.output_video)
        if out_file_path.exists() and out_file_path.stat().st_size > 0:
            sm = QtWidgets.QMessageBox()
            sm.setText("That output file already exists and is not empty!")
            sm.addButton("Cancel", QtWidgets.QMessageBox.DestructiveRole)
            sm.addButton("Overwrite", QtWidgets.QMessageBox.RejectRole)
            sm.exec()
            if sm.clickedButton().text() == "Cancel":
                return False
        return True

    def set_convert_button(self):
        if not self.app.fastflix.currently_encoding:
            self.widgets.convert_button.setText(f"{t('Convert')}  ")
            self.widgets.convert_button.setIcon(QtGui.QIcon(self.get_icon("play-round")))
            self.widgets.convert_button.setIconSize(scaler.scale_size(ICONS.MEDIUM, ICONS.MEDIUM))

        else:
            self.widgets.convert_button.setText(f"{t('Cancel')}  ")
            self.widgets.convert_button.setIcon(QtGui.QIcon(self.get_icon("black-x")))
            self.widgets.convert_button.setIconSize(scaler.scale_size(ICONS.MEDIUM, ICONS.MEDIUM))

    def get_icon(self, name):
        return get_icon(name, self.app.fastflix.config.theme)

    @reusables.log_exception("fastflix", show_traceback=True)
    def encode_video(self):
        if self.app.fastflix.currently_encoding:
            sure = yes_no_message(t("Are you sure you want to stop the current encode?"), title="Confirm Stop Encode")
            if not sure:
                return
            logger.info(t("Canceling current encode"))
            self.app.fastflix.worker_queue.put(["cancel"])
            self.video_options.queue.reset_pause_encode()
            return

        if self.app.fastflix.conversion_paused:
            return error_message("Queue is currently paused")

        if self.app.fastflix.current_video:
            add_current = True
            if self.app.fastflix.conversion_list and self.app.fastflix.current_video:
                add_current = yes_no_message("Add current video to queue?", yes_text="Yes", no_text="No")
            if add_current:
                if not self.add_to_queue():
                    return

        for video in self.app.fastflix.conversion_list:
            if video.status.ready:
                video_to_send: Video = video
                break
        else:
            error_message(t("There are no videos to start converting"))
            return

        logger.debug(t("Starting conversion process"))

        self.app.fastflix.currently_encoding = True
        prevent_sleep_mode()
        self.set_convert_button()
        self.send_video_request_to_worker_queue(video_to_send)
        self.disable_all()
        self.video_options.show_status()

    def add_to_queue(self):
        try:
            code = self.video_options.queue.add_to_queue()
        except FastFlixInternalException as err:
            error_message(str(err))
            return
        else:
            if code is not None:
                return code
        # No update_queue() needed - add_to_queue() already called new_source()
        self.video_options.show_queue()

        # if self.converting:
        #     commands = self.get_commands()
        #     requests = ["add_items", str(self.app.fastflix.log_path), tuple(commands)]
        #     self.app.fastflix.worker_queue.put(tuple(requests))

        self.clear_current_video()
        return True

    # @reusables.log_exception("fastflix", show_traceback=False)
    def conversion_complete(self, success: bool):
        self.paused = False
        allow_sleep_mode()
        self.set_convert_button()

        if not success:
            if not self.app.fastflix.config.disable_complete_message:
                error_message(t("There was an error during conversion and the queue has stopped"), title=t("Error"))
            self.video_options.queue.new_source()
        else:
            self.video_options.show_queue()
            if not self.app.fastflix.config.disable_complete_message:
                message(t("All queue items have completed"), title=t("Success"))

    #
    # @reusables.log_exception("fastflix", show_traceback=False)
    def conversion_cancelled(self, video: Video):
        self.set_convert_button()

        exists = video.video_settings.output_path.exists()

        if exists:
            sm = QtWidgets.QMessageBox()
            sm.setWindowTitle(t("Cancelled"))
            sm.setText(f"{t('Conversion cancelled, delete incomplete file')}\n{video.video_settings.output_path}?")
            sm.addButton(t("Delete"), QtWidgets.QMessageBox.YesRole)
            sm.addButton(t("Keep"), QtWidgets.QMessageBox.NoRole)
            sm.exec()
            if sm.clickedButton().text() == t("Delete"):
                try:
                    video.video_settings.output_path.unlink(missing_ok=True)
                except OSError:
                    pass

    @reusables.log_exception("fastflix", show_traceback=True)
    def dropEvent(self, event):
        if not event.mimeData().hasUrls:
            return event.ignore()

        event.setDropAction(QtCore.Qt.CopyAction)
        event.accept()

        if self.app.fastflix.current_video:
            discard = yes_no_message(
                f"{t('There is already a video being processed')}<br>{t('Are you sure you want to discard it?')}",
                title="Discard current video",
            )
            if not discard:
                return

        location = Path(clean_file_string(event.mimeData().urls()[0].toLocalFile()))

        try:
            self.input_video = location
        except (ValueError, IndexError):
            return event.ignore()
        if not self.input_video.exists():
            logger.error(f"File does not exist {self.input_video}")
            return event.ignore()

        self.source_video_path_widget.setText(str(self.input_video))
        self.video_path_widget.setText(str(self.input_video))
        try:
            self.update_video_info()
        except Exception:
            logger.exception(f"Could not load video {self.input_video}")
            self.video_path_widget.setText("")
            self.output_video_path_widget.setText("")
            self.output_video_path_widget.setDisabled(True)
            self.widgets.output_directory.setText("")
            self.output_path_button.setDisabled(True)
        self.page_update()

    def dragEnterEvent(self, event):
        event.accept() if event.mimeData().hasUrls else event.ignore()

    def dragMoveEvent(self, event):
        event.accept() if event.mimeData().hasUrls else event.ignore()

    def status_update(self, status_response):
        response = Response(*status_response)
        logger.debug(f"Updating queue from command worker: {response}")

        video_to_send: Optional[Video] = None
        errored = False
        same_video = False

        for video in self.app.fastflix.conversion_list:
            if response.video_uuid == video.uuid:
                video.status.running = False

                if response.status == "cancelled":
                    video.status.cancelled = True
                    self.end_encoding()
                    self.conversion_cancelled(video)
                    self.video_options.update_queue()
                    return

                if response.status == "complete":
                    video.status.current_command += 1
                    if len(video.video_settings.conversion_commands) > video.status.current_command:
                        same_video = True
                        video_to_send = video
                        break
                    else:
                        video.status.complete = True

                if response.status == "error":
                    video.status.error = True
                    errored = True
                break

        if errored and not self.video_options.queue.ignore_errors.isChecked():
            self.end_encoding()
            self.conversion_complete(success=False)
            return

        if not video_to_send:
            for video in self.app.fastflix.conversion_list:
                if video.status.ready:
                    video_to_send = video
                    # TODO ensure command int is in command list?
                    break

        if not video_to_send:
            self.end_encoding()
            self.conversion_complete(success=True)
            return

        self.app.fastflix.currently_encoding = True
        if not same_video and self.app.fastflix.conversion_paused:
            return self.end_encoding()

        self.send_video_request_to_worker_queue(video_to_send)

    def end_encoding(self):
        self.app.fastflix.currently_encoding = False
        allow_sleep_mode()
        self.video_options.queue.run_after_done()
        self.video_options.update_queue()
        self.set_convert_button()

    def send_next_video(self) -> bool:
        if not self.app.fastflix.currently_encoding:
            for video in self.app.fastflix.conversion_list:
                if video.status.ready:
                    video.status.running = True
                    self.send_video_request_to_worker_queue(video)
                    self.app.fastflix.currently_encoding = True
                    prevent_sleep_mode()
                    self.set_convert_button()
                    return True
        self.app.fastflix.currently_encoding = False
        allow_sleep_mode()
        self.set_convert_button()
        return False

    def send_video_request_to_worker_queue(self, video: Video):
        command = video.video_settings.conversion_commands[video.status.current_command]
        self.app.fastflix.currently_encoding = True
        prevent_sleep_mode()

        # logger.info(f"Sending video {video.uuid} command {command.uuid} called from {inspect.stack()}")

        self.app.fastflix.worker_queue.put(
            Request(
                request="execute",
                video_uuid=video.uuid,
                command_uuid=command.uuid,
                command=command.command,
                work_dir=str(video.work_path),
                log_name=video.video_settings.video_title or video.video_settings.output_path.stem,
                shell=command.shell,
            )
        )
        video.status.running = True
        self.video_options.update_queue()

    def find_video(self, uuid) -> Video:
        for video in self.app.fastflix.conversion_list:
            if uuid == video.uuid:
                return video
        raise FlixError(f"{t('No video found for')} {uuid}")

    def find_command(self, video: Video, uuid) -> int:
        for i, command in enumerate(video.video_settings.conversion_commands, start=1):
            if uuid == command.uuid:
                return i
        raise FlixError(f"{t('No command found for')} {uuid}")


class Notifier(QtCore.QThread):
    def __init__(self, parent, app, status_queue):
        super().__init__(parent)
        self.app = app
        self.main: Main = parent
        self.status_queue = status_queue
        self._shutdown = False

    def request_shutdown(self):
        """Request graceful shutdown of the thread."""
        self._shutdown = True

    def run(self):
        while not self._shutdown:
            # Message looks like (command, video_uuid, command_uuid)
            try:
                status = self.status_queue.get(timeout=0.5)
            except Empty:
                continue
            self.app.processEvents()
            if status[0] == "exit":
                logger.debug("GUI received ask to exit")
                self.main.close_event.emit()
                return
            self.main.status_update_signal.emit(status)
            self.app.processEvents()
