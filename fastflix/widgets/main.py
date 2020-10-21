#!/usr/bin/env python
# -*- coding: utf-8 -*-
import importlib.machinery  # Needed for pyinstaller
import logging
import os
import secrets
import tempfile
import time
from datetime import timedelta
from pathlib import Path

import pkg_resources
import reusables
from box import Box
from qtpy import QtCore, QtGui, QtWidgets

from fastflix.encoders.common import helpers
from fastflix.flix import FlixError
from fastflix.shared import error_message, file_date, FastFlixInternalException
from fastflix.widgets.thumbnail_generator import ThumbnailCreator
from fastflix.widgets.video_options import VideoOptions

logger = logging.getLogger("fastflix")

root = os.path.abspath(os.path.dirname(__file__))


def load_plugins(configuration):
    from fastflix.encoders.av1_aom import main as av1_plugin
    from fastflix.encoders.avc_x264 import main as avc_plugin
    from fastflix.encoders.gif import main as gif_plugin
    from fastflix.encoders.hevc_x265 import main as hevc_plugin
    from fastflix.encoders.rav1e import main as rav1e_plugin
    from fastflix.encoders.svt_av1 import main as svt_av1_plugin
    from fastflix.encoders.vp9 import main as vp9_plugin

    plugins = [hevc_plugin, avc_plugin, gif_plugin, vp9_plugin, av1_plugin, rav1e_plugin, svt_av1_plugin]

    return {
        plugin.name: plugin
        for plugin in plugins
        if (not getattr(plugin, "requires", None)) or plugin.requires in configuration
    }


class Main(QtWidgets.QWidget):
    completed = QtCore.Signal(int)
    thumbnail_complete = QtCore.Signal(int)
    cancelled = QtCore.Signal()
    close_event = QtCore.Signal()

    def __init__(self, parent, data_path, work_path, worker_queue, status_queue, log_queue, flix, **kwargs):
        super().__init__(parent)
        self.container = parent
        self.initialized = False
        self.loading_video = True
        self.scale_updating = False
        self.path = Box(
            data=data_path,
            work=work_path,
        )

        self.config = self.container.config

        self.worker_queue = worker_queue
        self.status_queue = status_queue
        self.log_queue = log_queue
        self.only_int = QtGui.QIntValidator()

        self.notifier = Notifier(self, self.status_queue)
        self.notifier.start()

        self.input_defaults = Box(scale=None, crop=None)
        self.initial_duration = 0

        for path in self.path.values():
            path.mkdir(parents=True, exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(prefix="temp_", dir=work_path)
        self.path.temp_dir = self.temp_dir.name

        self.setAcceptDrops(True)

        self.input_video = None
        self.video_path_widget = QtWidgets.QLineEdit("No Source Selected")
        self.output_video_path_widget = QtWidgets.QLineEdit("")
        self.output_video_path_widget.setDisabled(True)
        self.output_video_path_widget.textChanged.connect(lambda x: self.page_update(build_thumbnail=False))
        self.video_path_widget.setEnabled(False)
        self.video_path_widget.setStyleSheet("QLineEdit{color:#222}")
        self.output_video_path_widget.setStyleSheet("QLineEdit{color:#222}")
        self.streams, self.format_info = None, None

        self.widgets = Box(
            input_file=None,
            preview=None,
            start_time=None,
            end_time=None,
            video_track=None,
            convert_to=None,
            rotate=None,
            convert_button=None,
            v_flip=None,
            h_flip=None,
            crop=Box(top=None, bottom=None, left=None, right=None),
            scale=Box(width=None, height=None, keep_aspect_ratio=None),
            remove_metadata=None,
            chapters=None,
            fast_time=None,
            pause_resume=QtWidgets.QPushButton("Pause"),
        )

        self.thumb_file = Path(self.path.work, "thumbnail_preview.png")
        self.flix = flix
        self.plugins = load_plugins(self.flix.config)

        self.video_options = VideoOptions(
            self, available_audio_encoders=self.flix.get_audio_encoders(), log_queue=log_queue
        )

        self.completed.connect(self.conversion_complete)
        self.cancelled.connect(self.conversion_cancelled)
        self.close_event.connect(self.close)
        self.thumbnail_complete.connect(self.thumbnail_generated)
        self.encoding_worker = None
        self.command_runner = None
        self.converting = False
        self.side_data = Box()

        self.video_width = 0
        self.video_height = 0
        self.initial_video_width = 0
        self.initial_video_height = 0

        self.default_options = Box()

        self.grid = QtWidgets.QGridLayout()

        self.init_video_area()
        self.init_scale_and_crop()
        self.init_preview_image()

        self.grid.addWidget(self.video_options, 5, 0, 10, 14)
        self.grid.setSpacing(5)
        self.paused = False

        self.setLayout(self.grid)
        self.show()
        self.initialized = True
        self.last_page_update = time.time()

    def pause_resume(self):
        if not self.paused:
            self.paused = True
            self.worker_queue.put(["pause"])
            self.widgets.pause_resume.setText("Resume")
            self.widgets.pause_resume.setStyleSheet("background-color: green;")
            logger.info("Pausing FFmpeg conversion via pustils")
        else:
            self.paused = False
            self.worker_queue.put(["resume"])
            self.widgets.pause_resume.setText("Pause")
            self.widgets.pause_resume.setStyleSheet("background-color: orange;")
            logger.info("Resuming FFmpeg conversion")

    def config_update(self, ffmpeg, ffprobe):
        self.flix.update(ffmpeg, ffprobe)
        self.plugins = load_plugins(self.flix.config)
        self.thumb_file = Path(self.path.work, "thumbnail_preview.png")
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
        self.widgets.video_track.currentIndexChanged.connect(lambda: self.page_update())

        track_label = QtWidgets.QLabel("Video Track")
        track_label.setFixedWidth(65)
        layout.addWidget(track_label)
        layout.addWidget(self.widgets.video_track, stretch=1)
        layout.setSpacing(10)
        return layout

    def init_flip(self):
        self.flip_combo_box = QtWidgets.QComboBox()
        rotation_folder = "../data/rotations/FastFlix"

        no_rot_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder}.png")).resolve())
        vert_flip_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder} VF.png")).resolve())
        hoz_flip_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder} HF.png")).resolve())
        rot_180_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder} 180.png")).resolve())

        self.flip_combo_box.addItems(["No Flip", "Vertical Flip", "Horizontal Flip", "Vert + Hoz Flip"])
        self.flip_combo_box.setItemIcon(0, QtGui.QIcon(no_rot_file))
        self.flip_combo_box.setItemIcon(1, QtGui.QIcon(vert_flip_file))
        self.flip_combo_box.setItemIcon(2, QtGui.QIcon(hoz_flip_file))
        self.flip_combo_box.setItemIcon(3, QtGui.QIcon(rot_180_file))
        self.flip_combo_box.setIconSize(QtCore.QSize(35, 35))
        self.flip_combo_box.currentIndexChanged.connect(lambda: self.page_update())
        return self.flip_combo_box

    def get_flips(self):
        mapping = {0: (False, False), 1: (True, False), 2: (False, True), 3: (True, True)}
        return mapping[self.flip_combo_box.currentIndex()]

    def init_rotate(self):
        self.rotate_combo_box = QtWidgets.QComboBox()
        rotation_folder = "../data/rotations/FastFlix"

        no_rot_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder}.png")).resolve())
        rot_90_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder} C90.png")).resolve())
        rot_270_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder} CC90.png")).resolve())
        rot_180_file = str(Path(pkg_resources.resource_filename(__name__, f"{rotation_folder} 180.png")).resolve())

        self.rotate_combo_box.addItems(["No Rotation", "90°", "180°", "270°"])
        self.rotate_combo_box.setItemIcon(0, QtGui.QIcon(no_rot_file))
        self.rotate_combo_box.setItemIcon(1, QtGui.QIcon(rot_90_file))
        self.rotate_combo_box.setItemIcon(2, QtGui.QIcon(rot_180_file))
        self.rotate_combo_box.setItemIcon(3, QtGui.QIcon(rot_270_file))
        self.rotate_combo_box.setIconSize(QtCore.QSize(35, 35))
        self.rotate_combo_box.currentIndexChanged.connect(lambda: self.page_update())
        return self.rotate_combo_box

    def rotation_to_transpose(self):
        mapping = {0: None, 1: 1, 2: 4, 3: 2}
        return mapping[self.rotate_combo_box.currentIndex()]

    def change_output_types(self):
        self.widgets.convert_to.clear()
        self.widgets.convert_to.addItems([f"   {x}" for x in self.plugins.keys()])
        for i, plugin in enumerate(self.plugins.values()):
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
        if not self.convert_to:
            return
        if not self.output_video_path_widget.text().endswith(self.plugins[self.convert_to].video_extension):
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
        scale_area.setFont(self.container.font())
        scale_area.setStyleSheet("QGroupBox{padding-top:15px; margin-top:-18px}")
        scale_layout = QtWidgets.QVBoxLayout()

        self.widgets.scale.width, new_scale_layout = self.build_hoz_int_field("Width  ", right_stretch=False)
        self.widgets.scale.height, new_scale_layout, lb, rb = self.build_hoz_int_field(
            "  Height  ", left_stretch=False, layout=new_scale_layout, return_buttons=True
        )
        self.widgets.scale.height.setDisabled(True)
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
            widget.setValidator(self.only_int)
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
            value = self.time_to_number(widget.text())
            if value is None:
                return
        else:
            modifier = getattr(self.plugins[self.convert_to], "video_dimension_divisor", 1)
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
            self, caption="Open Video", filter="Video Files (*.mkv *.mp4 *.m4v *.mov *.avi *.divx)"
        )
        if not filename or not filename[0]:
            return
        self.input_video = filename[0]
        self.video_path_widget.setText(self.input_video)
        self.output_video_path_widget.setText(self.generate_output_filename)
        self.output_video_path_widget.setDisabled(False)
        self.output_path_button.setDisabled(False)
        self.update_video_info()
        self.page_update()

    @property
    def generate_output_filename(self):
        if self.input_video:
            return f"{Path(self.input_video).parent / Path(self.input_video).stem}-fastflix-{secrets.token_hex(2)}.{self.plugins[self.convert_to].video_extension}"
        return f"{Path('~').expanduser()}{os.sep}fastflix-{secrets.token_hex(2)}.{self.plugins[self.convert_to].video_extension}"

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
        start_pos = self.start_time or self.initial_duration // 10
        r, b, l, t = self.flix.get_auto_crop(self.input_video, self.video_width, self.video_height, start_pos)
        # Hack to stop thumb gen
        self.loading_video = True
        self.widgets.crop.top.setText(str(t))
        self.widgets.crop.left.setText(str(l))
        self.widgets.crop.right.setText(str(r))
        self.loading_video = False
        self.widgets.crop.bottom.setText(str(b))

    def build_crop(self):
        top = int(self.widgets.crop.top.text())
        left = int(self.widgets.crop.left.text())
        right = int(self.widgets.crop.right.text())
        bottom = int(self.widgets.crop.bottom.text())
        width = self.video_width - right - left
        height = self.video_height - bottom - top
        if (top + left + right + bottom) == 0:
            return None
        try:
            assert top >= 0, "Top must be positive number"
            assert left >= 0, "Left must be positive number"
            assert width > 0, "Total video width must be greater than 0"
            assert height > 0, "Total video height must be greater than 0"
            assert width <= self.video_width, "Width must be smaller than video width"
            assert height <= self.video_height, "Height must be smaller than video height"
        except AssertionError as err:
            error_message(f"Invalid Crop: {err}")
            return
        return f"{width}:{height}:{left}:{top}"

    def keep_aspect_update(self):
        keep_aspect = self.widgets.scale.keep_aspect.isChecked()
        if keep_aspect:
            self.widgets.scale.height.setText("-1")
        else:
            try:
                scale_width = int(self.widgets.scale.width.text())
                assert scale_width > 0
            except (ValueError, AssertionError):
                self.scale_updating = False
                return logger.warning("Invalid width")

            ratio = self.initial_video_height / self.initial_video_width
            scale_height = ratio * scale_width
            mod = int(scale_height % 2)
            if mod:
                scale_height -= mod
                logger.info(f"Have to adjust scale height by {mod} pixels")
            self.widgets.scale.height.setText(str(int(scale_height)))
        self.scale_update()

    @reusables.log_exception("fastflix", show_traceback=False)
    def scale_update(self):
        if self.scale_updating:
            return False

        self.scale_updating = True

        keep_aspect = self.widgets.scale.keep_aspect.isChecked()

        self.widgets.scale.height.setDisabled(keep_aspect)
        height = self.video_height
        width = self.video_width
        if self.build_crop():
            width, height, *_ = (int(x) for x in self.build_crop().split(":"))

        if keep_aspect and (not height or not width):
            self.scale_updating = False
            return logger.warning("Invalid source dimensions")
            # return self.scale_warning_message.setText("Invalid source dimensions")

        try:
            scale_width = int(self.widgets.scale.width.text())
            assert scale_width > 0
        except (ValueError, AssertionError):
            self.scale_updating = False
            return logger.warning("Invalid width")
            # return self.scale_warning_message.setText("Invalid main_width")

        if scale_width % 2:
            self.scale_updating = False
            self.widgets.scale.width.setStyleSheet("background-color: red;")
            self.widgets.scale.width.setToolTip(
                f"Width must be divisible by 2 - Source width: {self.initial_video_width}"
            )
            return logger.warning("Width must be divisible by 2")
            # return self.scale_warning_message.setText("Width must be divisible by 8")
        else:
            self.widgets.scale.width.setToolTip(f"Source width: {self.initial_video_width}")

        if keep_aspect:
            self.widgets.scale.height.setText("-1")
            self.widgets.scale.width.setStyleSheet("background-color: white;")
            self.widgets.scale.height.setStyleSheet("background-color: white;")
            self.page_update()
            self.scale_updating = False
            return
            # ratio = self.initial_video_height / self.initial_video_width
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

        try:
            scale_height = int(self.widgets.scale.height.text())
            assert scale_height == -1 or scale_height > 0
        except (ValueError, AssertionError):
            self.scale_updating = False
            return logger.warning("Invalid height")
            # return self.scale_warning_message.setText("Invalid height")

        if scale_height != -1 and scale_height % 2:
            self.widgets.scale.height.setStyleSheet("background-color: red;")
            self.widgets.scale.height.setToolTip(
                f"Height must be divisible by 2 - Source height: {self.initial_video_height}"
            )
            self.scale_updating = False
            return logger.warning(f"Height must be divisible by 2 - Source height: {self.initial_video_height}")
        else:
            self.widgets.scale.height.setToolTip(f"Source height: {self.initial_video_height}")
            # return self.scale_warning_message.setText("Height must be divisible by 8")
        # self.scale_warning_message.setText("")
        self.widgets.scale.width.setStyleSheet("background-color: white;")
        self.widgets.scale.height.setStyleSheet("background-color: white;")
        self.page_update()
        self.scale_updating = False

    @reusables.log_exception("fastflix", show_traceback=False)
    def update_video_info(self):
        self.loading_video = True
        try:
            self.streams, self.format_info = self.flix.parse(
                self.input_video, work_dir=self.path.work, extract_covers=True
            )
        except FlixError:
            error_message(f"Not a video file<br>{self.input_video}")
            self.input_video = None
            self.video_path_widget.setText("No Source Selected")
            self.output_video_path_widget.setText("")
            self.output_path_button.setDisabled(True)
            self.output_video_path_widget.setDisabled(True)
            self.streams = None
            self.format_info = None
            for i in range(self.widgets.video_track.count()):
                self.widgets.video_track.removeItem(0)
            self.widgets.convert_button.setDisabled(True)
            self.widgets.convert_button.setStyleSheet("background-color:gray;")
            self.widgets.preview.setText("No Video File")
            self.page_update()
            return

        self.side_data = self.flix.parse_hdr_details(self.input_video)
        logger.debug(self.streams)
        logger.debug(self.format_info)

        text_video_tracks = [
            f"{x.index}: codec {x.codec_name} " f'- pix_fmt {x.get("pix_fmt")} ' f'- profile {x.get("profile")}'
            for x in self.streams.video
        ]

        for i in range(self.widgets.video_track.count()):
            self.widgets.video_track.removeItem(0)

        if len(self.streams.video) == 0:
            error_message(f"No video tracks detected in file<br>{self.input_video}")
            self.input_video = None
            self.video_path_widget.setText("No Source Selected")
            self.output_video_path_widget.setText("")
            self.output_path_button.setDisabled(True)
            self.output_video_path_widget.setDisabled(True)
            self.streams = None
            self.format_info = None
            self.widgets.convert_button.setDisabled(True)
            self.widgets.convert_button.setStyleSheet("background-color:gray;")
            self.widgets.preview.setText("No Video File")
            self.page_update()
            return

        self.widgets.crop.top.setText("0")
        self.widgets.crop.left.setText("0")
        self.widgets.crop.right.setText("0")
        self.widgets.crop.bottom.setText("0")
        self.widgets.start_time.setText("0:00:00")

        # TODO set width and height by video track
        rotation = 0
        if "rotate" in self.streams.video[0].get("tags", {}):
            rotation = abs(int(self.streams.video[0].tags.rotate))
        # elif 'side_data_list' in self.streams.video[0]:
        #     rots = [abs(int(x.rotation)) for x in self.streams.video[0].side_data_list if 'rotation' in x]
        #     rotation = rots[0] if rots else 0

        if rotation in (90, 270):
            self.video_width = self.streams.video[0].height
            self.video_height = self.streams.video[0].width
        else:
            self.video_width = self.streams.video[0].width
            self.video_height = self.streams.video[0].height

        self.initial_video_width = self.video_width
        self.initial_video_height = self.video_height

        self.widgets.scale.width.setText(
            str(self.video_width + (self.video_width % self.plugins[self.convert_to].video_dimension_divisor))
        )
        self.widgets.scale.width.setToolTip(f"Source width: {self.initial_video_width}")
        self.widgets.scale.height.setText(
            str(self.video_height + (self.video_height % self.plugins[self.convert_to].video_dimension_divisor))
        )
        self.widgets.scale.height.setToolTip(f"Source height: {self.initial_video_height}")
        self.widgets.video_track.addItems(text_video_tracks)

        self.widgets.video_track.setDisabled(bool(len(self.streams.video) == 1))

        video_duration = float(self.format_info.get("duration", 0))
        self.initial_duration = video_duration

        logger.debug(f"{len(self.streams['video'])} video tracks found")
        logger.debug(f"{len(self.streams['audio'])} audio tracks found")
        if self.streams["subtitle"]:
            logger.debug(f"{len(self.streams['subtitle'])} subtitle tracks found")
        if self.streams["attachment"]:
            logger.debug(f"{len(self.streams['attachment'])} attachment tracks found")
        if self.streams["data"]:
            logger.debug(f"{len(self.streams['data'])} data tracks found")

        self.widgets.end_time.setText(self.number_to_time(video_duration))
        title_name = [v for k, v in self.format_info.get("tags", {}).items() if k.lower() == "title"]
        if title_name:
            self.widgets.video_title.setText(title_name[0])
        else:
            self.widgets.video_title.setText("")

        self.video_options.new_source()
        self.widgets.convert_button.setDisabled(False)
        self.widgets.convert_button.setStyleSheet("background-color:green;")
        self.loading_video = False

    @property
    def video_track(self):
        return int(self.widgets.video_track.currentIndex())

    @property
    def original_video_track(self):
        return int(self.widgets.video_track.currentText().split(":", 1)[0])

    @property
    def pix_fmt(self):
        return self.streams.video[self.video_track].pix_fmt

    @staticmethod
    def number_to_time(number):
        return str(timedelta(seconds=float(number)))[:10]

    @property
    def start_time(self):
        return self.time_to_number(self.widgets.start_time.text())

    @property
    def end_time(self):
        return self.time_to_number(self.widgets.end_time.text())

    @property
    def fast_time(self):
        return self.widgets.fast_time.currentText() == "fast"

    @property
    def remove_metadata(self):
        return self.widgets.remove_metadata.isChecked()

    @property
    def copy_chapters(self):
        return self.widgets.chapters.isChecked()

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
                logger.info("bad micro value")
                return
        total = float(f".{micro}")
        for i, v in enumerate(reversed(base.split(":"))):
            try:
                v = int(v)
            except ValueError:
                logger.info(f"Not a valid int: {v}")
            else:
                total += v * (60 ** i)
        return total

    @reusables.log_exception("fastflix", show_traceback=False)
    def generate_thumbnail(self, settings):
        if not self.input_video or self.loading_video:
            return

        if settings.pix_fmt == "yuv420p10le" and self.pix_fmt in ("yuv420p10le", "yuv420p12le"):
            settings.disable_hdr = True
        filters = helpers.generate_filters(custom_filters="scale='min(320\\,iw):-1'", **settings)

        preview_place = self.initial_duration // 10 if settings.start_time == 0 else settings.start_time

        thumb_command = self.flix.generate_thumbnail_command(
            source=self.input_video,
            output=self.thumb_file,
            filters=filters,
            start_time=preview_place,
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
            self.widgets.preview.setText("Error Updating Thumbnail")
            return

        pixmap = QtGui.QPixmap(str(self.thumb_file))
        pixmap = pixmap.scaled(320, 213, QtCore.Qt.KeepAspectRatio)
        self.widgets.preview.setPixmap(pixmap)

    def build_scale(self):
        width = self.widgets.scale.width.text()
        height = self.widgets.scale.height.text()
        return f"{width}:{height}"

    def get_all_settings(self):
        if not self.initialized:
            return
        stream_info = self.streams.video[self.video_track]

        end_time = self.end_time
        if self.end_time == float(self.format_info.get("duration", 0)):
            end_time = None
        if self.end_time and self.end_time - 0.1 <= self.initial_duration <= self.end_time + 0.1:
            end_time = None

        scale = self.build_scale()
        if scale in (
            f"{stream_info.width}:-1",
            f"-1:{stream_info.height}",
            f"{stream_info.width}:{stream_info.height}",
        ):
            scale = None

        v_flip, h_flip = self.get_flips()
        settings = Box(
            crop=self.build_crop(),
            scale=scale,
            source=self.input_video,
            start_time=self.start_time,
            end_time=end_time,
            video_track=self.original_video_track,
            stream_track=self.video_track,
            pix_fmt=self.pix_fmt,
            rotate=self.rotation_to_transpose(),
            v_flip=v_flip,
            h_flip=h_flip,
            streams=self.streams,
            format_info=self.format_info,
            work_dir=self.path.work,
            side_data=self.side_data,
            ffmpeg=self.flix.ffmpeg,
            ffprobe=self.flix.ffprobe,
            temp_dir=self.path.temp_dir,
            output_video=self.output_video,
            remove_metadata=self.remove_metadata,
            copy_chapters=self.copy_chapters,
            fast_time=self.fast_time,
            video_title=self.title,
        )
        settings.update(**self.video_options.get_settings())
        logger.debug(f"Settings gathered: {settings.to_dict()}")
        return settings

    def build_commands(self):
        if not self.initialized or not self.streams or self.loading_video:
            return None, None
        try:
            settings = self.get_all_settings()
        except FastFlixInternalException as err:
            error_message(str(err))
            return None, None
        commands = self.plugins[self.convert_to].build(**settings)
        after_done = self.video_options.commands.after_done(builder=True)
        if after_done is not None:
            commands.append(after_done)
        self.video_options.commands.update_commands(commands)
        return settings, commands

    def page_update(self, build_thumbnail=True):
        if not self.initialized or self.loading_video:
            return
        self.last_page_update = time.time()
        self.video_options.refresh()
        settings, _ = self.build_commands()
        if build_thumbnail:
            self.generate_thumbnail(settings)

    def close(self, no_cleanup=False):
        try:
            self.status_queue.put("exit")
        except KeyboardInterrupt:
            if not no_cleanup:
                self.temp_dir.cleanup()
            self.notifier.terminate()
            super().close()
            self.container.close()
            raise

    @property
    def convert_to(self):
        if self.widgets.convert_to:
            return self.widgets.convert_to.currentText().strip()

    @property
    def current_plugin(self):
        return self.plugins[self.convert_to]

    @reusables.log_exception("fastflix", show_traceback=False)
    def create_video(self):
        if self.converting:
            self.worker_queue.put(["cancel"])
            return

        if not self.input_video:
            return error_message("Have to select a video first")
        if self.encoding_worker and self.encoding_worker.is_alive():
            return error_message("Still encoding something else")
        if not self.input_video:
            return error_message("Please provide a source video")
        if not self.output_video:
            return error_message("Please specify output video")
        if Path(self.input_video).resolve().absolute() == Path(self.output_video).resolve().absolute():
            return error_message("Output video path is same as source!")

        if not self.output_video.lower().endswith(self.current_plugin.video_extension):
            sm = QtWidgets.QMessageBox()
            sm.setText(
                f"Output video file does not have expected extension ({self.current_plugin.video_extension}), which can case issues."
            )
            sm.addButton("Continue anyways", QtWidgets.QMessageBox.DestructiveRole)
            sm.addButton(f"Append ({self.current_plugin.video_extension}) for me", QtWidgets.QMessageBox.YesRole)
            sm.setStandardButtons(QtWidgets.QMessageBox.Close)
            for button in sm.buttons():
                if button.text().startswith("Append"):
                    button.setStyleSheet("background-color:green;")
                elif button.text().startswith("Continue"):
                    button.setStyleSheet("background-color:red;")
            sm.exec_()
            if sm.clickedButton().text().startswith("Append"):
                self.output_video_path_widget.setText(f"{self.output_video}.{self.current_plugin.video_extension}")
                self.output_video_path_widget.setDisabled(False)
                self.output_path_button.setDisabled(False)
            elif not sm.clickedButton().text().startswith("Continue"):
                return

        out_file_path = Path(self.output_video)
        if out_file_path.exists() and out_file_path.stat().st_size > 0:
            sm = QtWidgets.QMessageBox()
            sm.setText("That output file already exists and is not empty!")
            sm.addButton("Cancel", QtWidgets.QMessageBox.DestructiveRole)
            sm.addButton("Overwrite", QtWidgets.QMessageBox.RejectRole)
            sm.exec_()
            if sm.clickedButton().text() == "Cancel":
                return

        _, commands = self.build_commands()

        self.widgets.convert_button.setText("⛔ Cancel")
        self.widgets.convert_button.setStyleSheet("background-color:red;")
        self.widgets.pause_resume.setDisabled(False)
        self.widgets.pause_resume.setStyleSheet("background-color:orange;")
        self.converting = True
        for command in commands:
            self.worker_queue.put(("command", command.command, self.path.temp_dir, command.shell))
        self.video_options.setCurrentWidget(self.video_options.status)

    @reusables.log_exception("fastflix", show_traceback=False)
    def conversion_complete(self, return_code):
        self.widgets.convert_button.setStyleSheet("background-color:green;")
        self.converting = False
        self.paused = False
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
        self.widgets.convert_button.setText("Convert 🎥")
        self.widgets.pause_resume.setDisabled(True)
        self.widgets.pause_resume.setText("Pause")
        self.widgets.pause_resume.setStyleSheet("background-color:gray;")
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
        self.input_video = str(event.mimeData().urls()[0].toLocalFile())
        self.video_path_widget.setText(self.input_video)
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
        self.app = parent
        self.status_queue = status_queue

    def __del__(self):
        self.wait()

    def run(self):
        while True:
            status = self.status_queue.get()
            if status == "complete":
                self.app.completed.emit(0)
            elif status == "cancelled":
                self.app.cancelled.emit()
            elif status == "exit":
                self.app.close_event.emit()
                return
