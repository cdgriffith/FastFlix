#!/usr/bin/env python
import os
from pathlib import Path
import time
from datetime import timedelta
import logging
import tempfile

import reusables

from flix.flix import Flix
from flix.shared import QtGui, QtCore, QtWidgets, error_message, main_width
from flix.widgets.worker import Worker
from flix.av1 import convert

logger = logging.getLogger('flix')

__all__ = ['AV1']


class AV1(QtWidgets.QWidget):
    completed = QtCore.Signal(int)
    thumbnail_complete = QtCore.Signal()
    cancelled = QtCore.Signal()

    def __init__(self, parent=None, source=""):
        super(AV1, self).__init__(parent)
        self.main = parent
        self.thumb_file = Path(tempfile.gettempdir(), "flix_av1_preview.png")
        layout = QtWidgets.QGridLayout()
        self.setFixedHeight(650)
        self.setFixedWidth(main_width)
        self.setAcceptDrops(True)

        self.video_width = None
        self.video_height = None
        self.video_duration = 0

        # Signals
        self.completed.connect(self.conversion_complete)
        self.cancelled.connect(self.conversion_cancelled)
        self.thumbnail_complete.connect(self.thumbnail_generated)

        self.working_dir = os.path.dirname(source) if source else str(Path.home())

        # Source input file
        input_file_layout = QtWidgets.QHBoxLayout()
        self.input_file_path = QtWidgets.QLineEdit(source)
        self.input_file_path.setReadOnly(True)
        self.open_input_file = QtWidgets.QPushButton("...")
        if not source:
            self.open_input_file.setDefault(True)
        input_file_layout.addWidget(QtWidgets.QLabel("Source File:"))
        input_file_layout.addWidget(self.input_file_path)
        input_file_layout.addWidget(self.open_input_file)
        input_file_layout.setSpacing(20)
        self.open_input_file.clicked.connect(lambda: self.open_file(self.input_file_path))

        # Scale
        self.source_label_width = QtWidgets.QLabel("")
        self.source_label_height = QtWidgets.QLabel("")
        self.source_label_duration = QtWidgets.QLabel("")
        self.source_label_colorspace = QtWidgets.QLabel("")
        self.scale_area = QtWidgets.QGroupBox("Scale")
        self.scale_area.setCheckable(True)
        self.scale_area.setChecked(False)
        scale_layout = QtWidgets.QVBoxLayout()

        dimensions_layout = QtWidgets.QHBoxLayout()
        dimensions_layout.addWidget(QtWidgets.QLabel("Dimensions:"))
        self.source_label_width = QtWidgets.QLabel("0")
        dimensions_layout.addWidget(self.source_label_width)
        dimensions_layout.addWidget(QtWidgets.QLabel("x"))
        self.source_label_height = QtWidgets.QLabel("0")
        dimensions_layout.addWidget(self.source_label_height)

        new_scale_layout = QtWidgets.QHBoxLayout()
        new_scale_layout.addWidget(QtWidgets.QLabel("Scale:"))
        self.scale_width = QtWidgets.QLineEdit("0")
        self.scale_width.editingFinished.connect(self.scale_update)
        new_scale_layout.addWidget(self.scale_width)
        new_scale_layout.addWidget(QtWidgets.QLabel("x"))
        self.scale_height = QtWidgets.QLineEdit("0")
        self.scale_height.editingFinished.connect(self.scale_update)
        self.scale_height.setDisabled(True)
        new_scale_layout.addWidget(self.scale_height)

        self.keep_aspect_button = QtWidgets.QCheckBox("Keep (near) aspect ratio")
        self.keep_aspect_button.setChecked(True)
        self.keep_aspect_button.toggled.connect(self.scale_update)

        self.scale_warning_message = QtWidgets.QLabel("")

        scale_layout.addLayout(dimensions_layout)
        scale_layout.addLayout(new_scale_layout)
        scale_layout.addWidget(self.keep_aspect_button)
        scale_layout.addWidget(self.scale_warning_message)
        self.scale_area.setLayout(scale_layout)

        # # Convert HDR
        # self.convert_hdr_check = QtWidgets.QCheckBox("Convert HDR to SD")
        # self.convert_hdr_check.setChecked(False)
        # self.convert_hdr_check.hide()
        # self.convert_hdr_check.toggled.connect(lambda x: self.generate_thumbnail())
        # source_info_layout.addWidget(self.convert_hdr_check)
        #
        # # Keep subs
        # self.keep_subtitles = QtWidgets.QCheckBox("Keep Subtitles")
        # self.keep_subtitles.setChecked(False)
        # self.keep_subtitles.hide()
        # source_info_layout.addWidget(self.keep_subtitles)
        # source_info_layout.addStretch()

        # Duration Settings
        self.timing = QtWidgets.QGroupBox("Start Time / Duration")
        self.timing.setCheckable(True)
        self.timing.setChecked(False)
        self.timing.setFixedWidth(150)
        self.timing.toggled.connect(lambda x: self.generate_thumbnail())
        timing_layout = QtWidgets.QVBoxLayout()

        start_time_layout = QtWidgets.QHBoxLayout()
        self.start_time = QtWidgets.QLineEdit("0")
        start_time_layout.addWidget(QtWidgets.QLabel("Start Time: "))
        start_time_layout.addWidget(self.start_time)

        duration_layout = QtWidgets.QHBoxLayout()
        self.duration = QtWidgets.QLineEdit()
        duration_layout.addWidget(QtWidgets.QLabel("Length: "))
        duration_layout.addWidget(self.duration)

        source_duration_layout = QtWidgets.QHBoxLayout()
        source_duration_layout.addWidget(QtWidgets.QLabel("Duration: "))
        source_duration_layout.addWidget(self.source_label_duration)

        timing_layout.addLayout(start_time_layout)
        timing_layout.addLayout(duration_layout)
        timing_layout.addLayout(source_duration_layout)

        self.timing.setLayout(timing_layout)
        self.start_time.editingFinished.connect(lambda: self.generate_thumbnail())

        self.streams = {}
        self.format_info = {}
        self.output_video = None
        self.encoding_worker = None

        # Quality
        quality_layout = QtWidgets.QHBoxLayout()
        quality_layout.addWidget(QtWidgets.QLabel("Quality"), stretch=0)
        self.crfs = QtWidgets.QComboBox()
        self.crfs.addItems([str(x) for x in range(63)])
        self.crfs.setCurrentIndex(30)
        quality_layout.addWidget(self.crfs, stretch=1)

        self.mode = QtWidgets.QComboBox()
        self.mode.addItems(list(map(str, range(8))))  # Currently supports 0-8 encoding
        self.mode.setCurrentIndex(4)
        quality_layout.addWidget(QtWidgets.QLabel("Encoding Mode"), stretch=0)
        quality_layout.addWidget(self.mode, stretch=1)

        # Select Tracks
        audio_box_layout = QtWidgets.QHBoxLayout()
        self.audio_box = QtWidgets.QComboBox()
        self.audio_box.addItems([])
        audio_box_layout.addWidget(QtWidgets.QLabel("Audio: "), stretch=0)
        audio_box_layout.addWidget(self.audio_box, stretch=1)
        audio_box_layout.setSpacing(20)

        video_box_layout = QtWidgets.QHBoxLayout()
        self.video_box = QtWidgets.QComboBox()
        self.video_box.addItems([])
        video_box_layout.addWidget(QtWidgets.QLabel("Video: "), stretch=0)
        video_box_layout.addWidget(self.video_box, stretch=1)
        video_box_layout.setSpacing(20)
        self.video_box.currentIndexChanged.connect(self.video_track_change)

        self.kill_button = QtWidgets.QPushButton('Stop Encoding')
        self.kill_button.clicked.connect(lambda x: self.encoding_worker.kill())
        self.kill_button.hide()

        self.create_button = QtWidgets.QPushButton('Create')
        self.create_button.clicked.connect(self.create_video)
        if source:
            self.create_button.setDefault(True)

        # Preview Image
        self.preview = QtWidgets.QLabel()
        self.preview.setBackgroundRole(QtGui.QPalette.Base)
        self.preview.setFixedSize(main_width, 400)
        self.preview.setStyleSheet('border-top: 2px solid #dddddd;')  # background-color:#f0f0f0

        # Cropping
        self.crop = QtWidgets.QGroupBox("Crop")
        self.crop.setCheckable(True)
        self.crop.setChecked(False)
        # self.crop.setFixedHeight(110)
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

        # Add root layouts
        layout.addLayout(input_file_layout, 1, 0, 1, 10)
        layout.addWidget(self.scale_area, 2, 0, 3, 1)
        layout.addWidget(self.timing, 2, 1, 3, 5)
        layout.addWidget(self.crop, 2, 6, 3, 4)
        layout.addLayout(quality_layout, 5, 0, 1, 10)
        layout.addLayout(audio_box_layout, 6, 0, 1, 10)
        layout.addLayout(video_box_layout, 7, 0, 1, 10)
        layout.addWidget(self.kill_button, 8, 0, 1, 2)
        layout.addWidget(self.create_button, 8, 8, 1, 2)
        layout.addWidget(self.preview, 10, 0, 1, 10)

        self.setLayout(layout)

        self.converting = False

        self.update_source_labels(0, 0)
        if source:
            self.update_video_info()

    @reusables.log_exception('flix', show_traceback=False)
    def scale_update(self, *args):
        keep_aspect = self.keep_aspect_button.isChecked()
        self.scale_height.setDisabled(keep_aspect)
        height = self.video_height
        width = self.video_width
        if self.crop.isChecked():
            width, height, *_ = (int(x) for x in self.build_crop().split(":"))

        if keep_aspect and (not height or not width):
            return self.scale_warning_message.setText("Invalid source dimensions")

        try:
            scale_width = int(self.scale_width.text())
            assert scale_width > 0
        except (ValueError, AssertionError):
            return self.scale_warning_message.setText("Invalid main_width")

        if scale_width % 8:
            return self.scale_warning_message.setText("Width must be divisible by 8")

        if keep_aspect:
            ratio = scale_width / width
            scale_height = ratio * height
            self.scale_height.setText(str(int(scale_height)))
            mod = int(scale_height % 8)
            if mod:
                scale_height -= mod
                logger.info(f"Have to adjust scale height by {mod} pixels")
                self.scale_warning_message.setText(f"height has -{mod}px off aspect")
            self.scale_height.setText(str(int(scale_height)))
            return

        try:
            scale_height = int(self.scale_height.text())
            assert scale_height > 0
        except (ValueError, AssertionError):
            return self.scale_warning_message.setText("Invalid height")

        if scale_height % 8:
            return self.scale_warning_message.setText("Height must be divisible by 8")
        self.scale_warning_message.setText("")

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

    @staticmethod
    def _calc_time(amount):
        try:
            t = sum(float(x) * 60 ** i for i, x in enumerate(reversed(amount.split(":"))))
        except ValueError:
            return 0
        else:
            if t < 0:
                return 0
            return t

    @reusables.log_exception('flix', show_traceback=False)
    def _get_start_time(self):
        return self._calc_time(self.start_time.text())

    @reusables.log_exception('flix', show_traceback=False)
    def update_source_labels(self, width, height, **kwargs):
        self.source_label_width.setText(f"{width}px" if width else "0")
        self.source_label_height.setText(f"{height}px" if height else "0")
        self.video_height = int(height)
        self.video_width = int(width)
        self.source_label_duration.setText(str(timedelta(seconds=float(self.video_duration)))[:10])
        self.source_label_colorspace.setText(f"{kwargs.get('color_space', 'unkown')}")
        if kwargs.get('color_space', '').startswith('bt2020'):
            self.convert_hdr_check.setChecked(True)
            self.convert_hdr_check.show()

    @property
    def flix(self):
        return Flix(ffmpeg=self.main.ffmpeg, ffprobe=self.main.ffprobe, svt_av1=self.main.svt_av1)

    @reusables.log_exception('flix', show_traceback=False)
    def update_video_info(self):
        self.streams, self.format_info = self.flix.parse(self.input_file_path.text())
        text_audio_tracks = [(f'{i}: language {x.get("tags", {"language": "unknown"}).get("language", "unknown")}'
                              f' - channels {x.channels}'
                              f' - codec {x.codec_name}') for i, x in enumerate(self.streams['audio'])] + ["Disabled"]
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

    @reusables.log_exception('flix', show_traceback=False)
    def generate_thumbnail(self):
        if not self.input_file_path.text():
            return
        start_time = 0
        try:
            crop = self.build_crop()
        except (ValueError, AssertionError):
            logger.warning("Invalid crop, thumbnail will not reflect it")
            crop = None
        if self.timing.isChecked():
            start_time = self._get_start_time()
        elif self.video_duration > 5:
            start_time = 5
        thumb_command = self.flix.generate_thumbnail_command(
            source=self.input_file_path.text(),
            output=self.thumb_file,
            video_track=self.streams['video'][self.video_box.currentIndex()]['index'],
            start_time=start_time,
            # disable_hdr=self.convert_hdr_check.isChecked(),
            crop=crop
        )
        logger.info("Generating thumbnail")
        worker = Worker(self, thumb_command, cmd_type="thumb")
        worker.start()

    @reusables.log_exception('flix', show_traceback=False)
    def thumbnail_generated(self):
        pixmap = QtGui.QPixmap(str(self.thumb_file))
        pixmap = pixmap.scaled(600, 400, QtCore.Qt.KeepAspectRatio)
        self.preview.setPixmap(pixmap)

    @reusables.log_exception('flix', show_traceback=False)
    def video_track_change(self, index):
        self.update_source_labels(**self.streams['video'][index])

    def build_scale(self):
        width = int(self.scale_width.text())
        height = int(self.scale_height.text())
        assert 0 < width <= 2160
        assert 0 < height <= 4096
        return f"{width}:{height}"

    def build_crop(self):
        if not self.crop.isChecked():
            return None
        top = int(self.crop_top.text())
        left = int(self.crop_left.text())
        right = int(self.crop_right.text())
        bottom = int(self.crop_bottom.text())
        width = self.video_width - right - left
        height = self.video_height - bottom - top
        assert top >= 0
        assert left >= 0
        assert width > 0
        assert height > 0
        assert width <= self.video_width
        assert height <= self.video_height
        assert width % 8 == 0
        assert height % 8 == 0
        self.source_label_width.setText(str(width))
        self.source_label_height.setText(str(height))
        return f"{width}:{height}:{left}:{top}"

    @reusables.log_exception('flix', show_traceback=False)
    def create_video(self):
        if self.encoding_worker and self.encoding_worker.is_alive():
            return error_message("Still encoding something else")

        source_video = self.input_file_path.text()
        self.output_video = self.save_file()
        if not source_video:
            return error_message("Please provide a source video")
        if not self.output_video:
            logger.warning("No output video specified, canceling encoding")
            return
        if not self.output_video.lower().endswith(("mkv", "mp4")):
            return error_message("Output file must end with .mp4 or .mkv")
        video_track = self.streams['video'][self.video_box.currentIndex()]['index']
        audio_track = None
        if self.audio_box.currentText() != 'Disabled':
            audio_track = self.streams['audio'][self.audio_box.currentIndex()]['index']
        start_time = 0
        duration = None
        if self.timing.isChecked():
            start_time = self._get_start_time()
            duration = self.duration.text()
            if not start_time:
                start_time = 0
            if not duration:
                error_message("Please select a duration amount or disable the Start Time / Duration field")
        if Path(self.output_video).exists():
            em = QtWidgets.QMessageBox()
            em.setText("Output video already exists, overwrite?")
            em.addButton("Overwrite", QtWidgets.QMessageBox.YesRole)
            em.setStandardButtons(QtWidgets.QMessageBox.Close)
            em.exec_()
            if em.clickedButton().text() == "Overwrite":
                os.remove(self.output_video)
            else:
                return

        crop = None
        if self.crop.isChecked():
            try:
                crop = self.build_crop()
            except ValueError:
                return error_message("Crop values are not numeric")
            except AssertionError:
                return error_message("Crop values must be divisible by eight, "
                                     "positive integers, and less than video dimensions")

        scale = None
        if self.scale_area.isChecked():
            try:
                scale = self.build_scale()
            except ValueError:
                return error_message("Scale values are not numeric")
            except AssertionError:
                return error_message("Scale values must be positive integers less than 4096x2160")

        if not scale and (self.video_height > 2160 or self.video_width > 4096):
            return error_message("Currently only videos at resolutions less than 4096x2160 are supported")

        av1_settings = self.main.get_settings()['svt_av1']

        params = {
            "flix": self.flix,
            "source": source_video,
            "output": self.output_video,
            "video_track": video_track,
            "audio_track": audio_track,
            "build_dir": tempfile.gettempdir(),
            "start_time": start_time,
            "duration": duration,
            "save_segments": av1_settings.get('save_segments', False),
            "auto_crop": True,
            "save_yuv": av1_settings.get('save_raw', False),
            "overwrite": False,
            "scale": scale,
            "crop": crop,
            "segment_size": av1_settings.get('segment_size', 60),
            "crf": self.crfs.currentText(),
            "mode": self.mode.currentText(),
        }

        logger.debug(f'Encoding with params: {params}')

        self.create_button.setDisabled(True)
        self.kill_button.hide()
        self.main.status.showMessage("Encoding...")
        logger.info("Converting video")
        self.encoding_worker = Worker(self, target=convert, params=params, cmd_type="convert")
        self.encoding_worker.start()

    @reusables.log_exception('flix', show_traceback=False)
    def conversion_cancelled(self):
        self.create_button.setDisabled(False)
        self.main.default_status()
        self.kill_button.hide()
        os.remove(self.output_video)

    @reusables.log_exception('flix', show_traceback=False)
    def conversion_complete(self, return_code):
        self.create_button.setDisabled(False)
        self.main.default_status()
        self.kill_button.hide()

        if return_code:
            error_message("Could not encode video due to an error, please view the logs for more details")
        else:
            sm = QtWidgets.QMessageBox()
            sm.setText("Encoded successfully, view now?")
            sm.addButton("View", QtWidgets.QMessageBox.YesRole)
            sm.setStandardButtons(QtWidgets.QMessageBox.Close)
            sm.exec_()
            if sm.clickedButton().text() == "View":
                QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(self.output_video))

    def dragEnterEvent(self, event):
        event.accept() if event.mimeData().hasUrls else event.ignore()

    def dragMoveEvent(self, event):
        event.accept() if event.mimeData().hasUrls else event.ignore()

    @reusables.log_exception('flix', show_traceback=False)
    def dropEvent(self, event):
        if not event.mimeData().hasUrls:
            return event.ignore()
        event.setDropAction(QtCore.Qt.CopyAction)
        event.accept()
        self.input_file_path.setText(str(event.mimeData().urls()[0].toLocalFile()))
        self.update_video_info()
        self.open_input_file.setDefault(False)
        self.create_button.setDefault(True)
