import sys
import os
from pathlib import Path
import time
from datetime import timedelta
import logging
from subprocess import Popen, PIPE, run, STDOUT
import tempfile
import importlib.machinery

import reusables
from box import __version__ as box_version

from flix import Flix, ff_version

if os.getenv('SHIBOKEN2') and os.getenv('PYSIDE2'):
    importlib.machinery.SourceFileLoader('shiboken2', os.getenv('SHIBOKEN2')).load_module()
    PySide2 = importlib.machinery.SourceFileLoader('PySide2', os.getenv('PYSIDE2')).load_module()

from PySide2 import QtWidgets, QtCore, QtGui
from PySide2 import __version__ as pyside_version

__version__ = '1.0.0'
__author__ = 'Chris Griffith'

try:
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    # noinspection PyUnresolvedReferences
    base_path = sys._MEIPASS
    pyinstaller = True
except AttributeError:
    base_path = os.path.abspath(".")
    pyinstaller = False

logger = logging.getLogger('flix')
logger.setLevel(logging.DEBUG)


class Worker(QtCore.QThread):
    def __init__(self, app, command, cmd_type="convert"):
        super(Worker, self).__init__(app)
        self.app = app
        self.command = command
        self.cmd_type = cmd_type
        self.process = None
        self.killed = False

    def run(self):
        logger.info(f"Running command: {self.command}")
        self.process = self.start_exec()
        while True:
            next_line = self.process.stdout.readline().decode('utf-8')
            if not next_line:
                if self.process.poll() is not None:
                    break
                else:
                    continue
            logger.debug(f"ffmpeg - {next_line}")

        return_code = self.process.poll()
        if self.killed:
            self.app.cancelled.emit()
        elif self.cmd_type == "convert":
            self.app.completed.emit(return_code)
        elif self.cmd_type == "thumb":
            self.app.thumbnail_complete.emit()

    def start_exec(self):
        return Popen(self.command, stdin=PIPE, stdout=PIPE, stderr=STDOUT, shell=True)

    def is_alive(self):
        return True if self.process.poll() is None else False

    def kill(self):
        if self.is_alive():
            self.killed = True
            if reusables.win_based:
                run(f"TASKKILL /F /PID {self.process.pid} /T", stdin=PIPE, stdout=PIPE, stderr=PIPE)
            else:
                run(f"kill -9 {self.process.pid}", stdin=PIPE, stdout=PIPE, stderr=PIPE)
            return self.process.terminate()

    def __del__(self):
        self.kill()


class Main(QtWidgets.QMainWindow):

    def __init__(self, ffmpeg, ffprobe, ffmpeg_version, ffprobe_version, source="", parent=None):
        super(Main, self).__init__(parent)
        self.converter = X265(parent=self, source=source)
        self.converter.show()

        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe
        self.ffmpeg_version = ffmpeg_version
        self.ffprobe_version = ffprobe_version

        self.status = QtWidgets.QStatusBar()
        self.setStatusBar(self.status)
        self.default_status()

        tab_widget = QtWidgets.QTabWidget()
        tab_widget.addTab(self.converter, "x265")
        tab_widget.addTab(Logs(self), 'Logs')
        tab_widget.addTab(Settings(self), 'Settings')
        tab_widget.addTab(About(self), 'About')

        self.setCentralWidget(tab_widget)

        self.setWindowIcon(QtGui.QIcon(os.path.join(base_path, 'data/icon.ico') if pyinstaller else
                                       os.path.join(os.path.dirname(__file__), '../data/icon.ico')))

        if not ffmpeg_version or not ffprobe_version:
            self.converter.setDisabled(True)
            tab_widget.setCurrentIndex(2)
            message("You need to select ffmpeg and ffprobe or equivalent tools to use before you can encode.",
                    parent=self)

        logger.info(f"Initialized FastFlix v{__version__}")
        logger.debug(f"ffmpeg version: {self.ffmpeg_version}")
        logger.debug(f"ffprobe version: {self.ffprobe_version}")

    def default_status(self):
        if not self.ffprobe_version or not self.ffmpeg_version:
            self.status.showMessage("ENCODING DISABLED - Please setup ffmpeg and ffprobe paths in settings!")
        else:
            self.status.showMessage(f"Using ffmpeg version {self.ffmpeg_version},"
                                    f" ffprobe version {self.ffprobe_version}")

    def closeEvent(self, event):
        if self.converter.encoding_worker and self.converter.encoding_worker.is_alive():
            self.converter.encoding_worker.kill()
        try:
            os.remove(self.converter.thumb_file)
        except OSError:
            pass
        event.accept()


class QPlainTextEditLogger(logging.Handler):
    def __init__(self, parent):
        super(QPlainTextEditLogger, self).__init__()
        self.widget = QtWidgets.QTextBrowser(parent)
        self.widget.setReadOnly(True)

    def emit(self, record):
        msg = self.format(record)
        self.widget.append(msg)

    def write(self, m):
        pass


class Logs(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(Logs, self).__init__(parent)

        layout = QtWidgets.QVBoxLayout()
        log_text_box = QPlainTextEditLogger(self)
        log_text_box.setFormatter(logging.Formatter('<b>%(levelname)s</b> - %(asctime)s - %(message)s'))
        logger.addHandler(log_text_box)

        log_text_box.setLevel(logging.DEBUG)
        layout.addWidget(log_text_box.widget)
        self.setLayout(layout)


class About(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(About, self).__init__(parent)
        layout = QtWidgets.QGridLayout()
        label = QtWidgets.QLabel(f"<b>FastFlix</b> v{__version__}<br>"
                                 f"<br>Author: <a href='https://github.com/cdgriffith'>Chris Griffith</a>"
                                 f"<br>License: MIT")
        label.setFont(QtGui.QFont("Arial", 14))
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setOpenExternalLinks(True)
        label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        supporting_libraries_label = QtWidgets.QLabel(
            "Supporting libraries<br>"
            f"<a href='https://www.python.org/'>Python</a> {reusables.version_string} (PSF LICENSE), "
            f"<a href='https://wiki.qt.io/Qt_for_Python'>PySide2</a> {pyside_version} (LGPLv3)<br>"
            f"<a href='https://github.com/cdgriffith/Box'>python-box</a> {box_version} (MIT), "
            f"<a href='https://github.com/cdgriffith/Reusables'>Reusables</a> {reusables.__version__} (MIT)<br>")
        supporting_libraries_label.setAlignment(QtCore.Qt.AlignCenter)
        supporting_libraries_label.setOpenExternalLinks(True)

        layout.addWidget(label)
        layout.addWidget(supporting_libraries_label)

        if pyinstaller:
            pyinstaller_label = QtWidgets.QLabel("Packaged with: <a href='https://www.pyinstaller.org/index.html'>"
                                                 "PyInstaller</a>")
            pyinstaller_label.setAlignment(QtCore.Qt.AlignCenter)
            pyinstaller_label.setOpenExternalLinks(True)
            layout.addWidget(pyinstaller_label)

        self.setLayout(layout)


class Settings(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(Settings, self).__init__(parent)
        self.main = parent
        layout = QtWidgets.QGridLayout()

        self.warning_message = QtWidgets.QLabel("")
        self.warning_message.setFixedHeight(40)

        # Buttons
        self.button_group = QtWidgets.QButtonGroup()

        self.env_radio = QtWidgets.QRadioButton("Environment Variables (FFMPEG and FFPROBE)")
        self.path_radio = QtWidgets.QRadioButton("System PATH")
        self.binary_radio = QtWidgets.QRadioButton("Direct path to binaries")
        self.env_radio.name = "env"
        self.path_radio.name = "path"
        self.binary_radio.name = "binary"

        self.button_group.addButton(self.env_radio)
        self.button_group.addButton(self.path_radio)
        self.button_group.addButton(self.binary_radio)

        self.button_group.buttonClicked.connect(self.choice)

        # Path Select

        self.binary_select = QtWidgets.QGroupBox("Binaries")
        self.binary_select.setCheckable(False)
        self.binary_select.setDisabled(True)
        self.binary_select.setFixedHeight(120)

        binary_file_box = QtWidgets.QVBoxLayout()
        binary_file_layout = QtWidgets.QHBoxLayout()
        self.binary_file_path = QtWidgets.QLineEdit()
        self.binary_file_path.setReadOnly(True)
        self.binary_file_path.setText(os.getcwd())
        self.open_binary_file = QtWidgets.QPushButton("...")
        self.binary_file_info = QtWidgets.QLabel("")
        binary_file_layout.addWidget(QtWidgets.QLabel("Binary directory:"))
        binary_file_layout.addWidget(self.binary_file_path)
        binary_file_layout.addWidget(self.open_binary_file)
        binary_file_layout.setSpacing(20)
        self.open_binary_file.clicked.connect(self.open_binary_dir)
        binary_file_box.addLayout(binary_file_layout)
        binary_file_box.addWidget(self.binary_file_info)
        self.binary_select.setLayout(binary_file_box)

        layout.addWidget(self.warning_message, 0, 0)
        layout.addWidget(self.env_radio, 1, 0)
        layout.addWidget(self.path_radio, 2, 0)
        layout.addWidget(self.binary_radio, 3, 0)
        layout.addWidget(self.binary_select, 4, 0)
        layout.addWidget(QtWidgets.QLabel(), 5, 0, 4, 2)

        self.setLayout(layout)
        self.check()

    def choice(self, x):
        self.binary_select.setDisabled(x.name != "binary")
        if x.name == 'env':
            self.env()
        if x.name == 'binary':
            self.check_dir(self.binary_file_path.text())
        if x.name == 'path':
            self.path()
        self.check()

    def path(self):
        self.main.ffmpeg = 'ffmpeg'
        self.main.ffmpeg_version = ff_version(self.main.ffmpeg, throw=False)
        self.main.ffprobe = 'ffprobe'
        self.main.ffprobe_version = ff_version(self.main.ffprobe, throw=False)

    def env(self):
        self.main.ffmpeg = os.getenv('FFMPEG')
        self.main.ffmpeg_version = ff_version(self.main.ffmpeg, throw=False)
        self.main.ffprobe = os.getenv('FFPROBE')
        self.main.ffprobe_version = ff_version(self.main.ffprobe, throw=False)

    def check_dir(self, directory):
        updated_ffmpeg, updated_ffprobe = False, False
        for path in Path(directory).iterdir():
            if path.stem == 'ffmpeg':
                ffmpeg_ver = ff_version(path, throw=False)
                if ffmpeg_ver:
                    self.main.ffmpeg = str(path)
                    self.main.ffmpeg_version = ffmpeg_ver
                    updated_ffmpeg = True
            if path.stem == 'ffprobe':
                ffprobe_ver = ff_version(path, throw=False)
                if ffprobe_ver:
                    self.main.ffprobe = str(path)
                    self.main.ffprobe_version =ffprobe_ver
                    updated_ffprobe = True
        warnings = []
        if not updated_ffmpeg:
            warnings.append("Did not find FFMPEG binary in this directory!")
        if not updated_ffprobe:
            warnings.append("Did not find FFPROBE binary in this directory!")
        if warnings:
            warnings.append("Please make sure the files are only named ffmpeg (or ffmpeg.exe) "
                            "and ffprobe (or ffprobe.exe)")
            self.binary_file_info.setText("<br>".join(warnings))
        else:
            self.binary_file_info.setText("Binary files found!")

    def open_binary_dir(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self)
        if not directory:
            self.path_radio.setChecked(True)
            self.binary_select.setDisabled(True)
        self.binary_file_path.setText(str(directory))
        self.check_dir(directory)
        self.check()

    def check(self):
        if self.main.ffmpeg_version and self.main.ffprobe_version:
            self.warning_message.setText("<b>Status:</b> Everything is under control. Situation normal.")
            self.main.converter.setDisabled(False)
        elif self.main.ffmpeg_version:
            self.warning_message.setText("<b>Status:</b> ffprobe not found")
            self.main.converter.setDisabled(True)
        elif self.main.ffprobe_version:
            self.warning_message.setText("<b>Status:</b> ffmpeg not found")
            self.main.converter.setDisabled(True)
        else:
            self.warning_message.setText("<b>Status:</b> ffmpeg and ffprobe not found")
            self.main.converter.setDisabled(True)
        self.main.default_status()
        if self.main.ffmpeg_version:
            logger.debug(f"ffmpeg version: {self.main.ffmpeg_version}")
        if self.main.ffprobe_version:
            logger.debug(f"ffprobe version: {self.main.ffprobe_version}")


class X265(QtWidgets.QWidget):
    completed = QtCore.Signal(int)
    thumbnail_complete = QtCore.Signal()
    cancelled = QtCore.Signal()

    def __init__(self, parent=None, source=""):
        super(X265, self).__init__(parent)
        self.main = parent
        self.thumb_file = Path(tempfile.gettempdir(), "flix_preview.png")
        layout = QtWidgets.QGridLayout()
        self.setFixedHeight(650)

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

        # Media Info
        self.source_label_width = QtWidgets.QLabel("")
        self.source_label_height = QtWidgets.QLabel("")
        self.source_label_duration = QtWidgets.QLabel("")
        self.source_label_colorspace = QtWidgets.QLabel("")
        source_width_layout = QtWidgets.QHBoxLayout()
        source_width_layout.addWidget(QtWidgets.QLabel("Width: "))
        source_width_layout.addWidget(self.source_label_width)
        source_height_layout = QtWidgets.QHBoxLayout()
        source_height_layout.addWidget(QtWidgets.QLabel("Height: "))
        source_height_layout.addWidget(self.source_label_height)
        source_colorspace_layout = QtWidgets.QHBoxLayout()
        self.source_label_for_colorspace = QtWidgets.QLabel("Colorspace: ")
        source_colorspace_layout.addWidget(self.source_label_for_colorspace)
        source_colorspace_layout.addWidget(self.source_label_colorspace)
        source_info_layout = QtWidgets.QVBoxLayout()
        source_info_layout.addWidget(QtWidgets.QLabel("Media Info"))
        source_info_layout.addLayout(source_width_layout)
        source_info_layout.addLayout(source_height_layout)
        source_info_layout.addLayout(source_colorspace_layout)

        # Convert HDR
        self.convert_hdr_check = QtWidgets.QCheckBox("Convert HDR to SD")
        self.convert_hdr_check.setChecked(False)
        self.convert_hdr_check.hide()
        self.convert_hdr_check.toggled.connect(lambda x: self.generate_thumbnail())
        source_info_layout.addWidget(self.convert_hdr_check)

        # Keep subs
        self.keep_subtitles = QtWidgets.QCheckBox("Keep Subtitles")
        self.keep_subtitles.setChecked(False)
        self.keep_subtitles.hide()
        source_info_layout.addWidget(self.keep_subtitles)
        source_info_layout.addStretch()

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
        quality_layout.addWidget(QtWidgets.QLabel("crf"), stretch=0)
        self.crfs = QtWidgets.QComboBox()
        self.crfs.addItems([str(x / 2) for x in range(61)])
        self.crfs.setCurrentIndex(40)
        quality_layout.addWidget(self.crfs, stretch=1)

        self.preset = QtWidgets.QComboBox()
        self.preset.addItems([
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
            "placebo"])
        self.preset.setCurrentIndex(5)
        quality_layout.addWidget(QtWidgets.QLabel("preset"), stretch=0)
        quality_layout.addWidget(self.preset, stretch=1)

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
        self.preview.setFixedSize(600, 400)
        self.preview.setStyleSheet('border-top: 2px solid #dddddd;')  # background-color:#f0f0f0

        # Cropping
        self.crop = QtWidgets.QGroupBox("Crop")
        self.crop.setCheckable(True)
        self.crop.setChecked(False)
        self.crop.setFixedHeight(110)
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
        layout.addLayout(input_file_layout, 1, 0, 1, 4)
        layout.addLayout(source_info_layout, 2, 0, 3, 1)
        layout.addWidget(self.timing, 2, 1, 3, 1)
        layout.addWidget(self.crop, 2, 2, 3, 2)
        layout.addLayout(quality_layout, 5, 0, 1, 4)
        layout.addLayout(audio_box_layout, 6, 0, 1, 4)
        layout.addLayout(video_box_layout, 7, 0, 1, 4)
        layout.addWidget(self.kill_button, 8, 0, 1, 1)
        layout.addWidget(self.create_button, 8, 3, 1, 1)
        layout.addWidget(self.preview, 9, 0, 1, 4)

        self.setLayout(layout)

        self.converting = False

        self.update_source_labels(0, 0)
        if source:
            self.update_video_info()

    @reusables.log_exception('flix', show_traceback=False)
    def open_file(self, update_text):
        filename = QtWidgets.QFileDialog.getOpenFileName(self, caption="Open Video",
                                                         filter="Video Files (*.mp4 *.m4v *.mov *.mkv *.avi *.divx)")
        if not filename or not filename[0]:
            return
        update_text.setText(filename[0])
        self.update_video_info()
        self.open_input_file.setDefault(False)
        self.create_button.setDefault(True)

    @reusables.log_exception('flix', show_traceback=False)
    def save_file(self):
        f = Path(self.input_file_path.text())
        save_file = os.path.join(f.parent, f"{f.stem}-flix-{int(time.time())}.mp4")
        filename = QtWidgets.QFileDialog.getSaveFileName(self, caption="Save Video As", dir=str(save_file),
                                                         filter="Video File(*.mp4 *.mkv)")
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
        self.source_label_width.setText(f"{width}px" if width else "")
        self.source_label_height.setText(f"{height}px" if height else "")
        self.video_height = int(height)
        self.video_width = int(width)
        self.source_label_duration.setText(str(timedelta(seconds=float(self.video_duration)))[:10])
        self.source_label_colorspace.setText(f"{kwargs.get('color_space', 'unkown')}")
        if kwargs.get('color_space', '').startswith('bt2020'):
            self.convert_hdr_check.setChecked(True)
            self.convert_hdr_check.show()

    @property
    def flix(self):
        return Flix(ffmpeg=self.main.ffmpeg, ffprobe=self.main.ffprobe)

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
        self.video_duration = float(self.format_info.duration)

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
            self.keep_subtitles.show()
            self.keep_subtitles.setChecked(True)
        else:
            if self.streams['subtitle']:
                # hdmv_pgs_subtitle, dvd_subtitle
                logger.warning(f"Cannot keep subtitles of type: {self.streams['subtitle'][0].codec_name}")
            self.keep_subtitles.setChecked(False)
            self.keep_subtitles.hide()
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
            disable_hdr=self.convert_hdr_check.isChecked(),
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

        try:
            crop = self.build_crop()
        except ValueError:
            error_message("Crop values are not numeric")
            return
        except AssertionError:
            error_message("Crop values must be positive and less than video dimensions")
            return

        remove_hdr = self.convert_hdr_check.isChecked()

        command = self.flix.generate_x265_command(source_video, self.output_video, video_track, audio_track,
                                                  duration=duration, start_time=start_time,
                                                  crf=self.crfs.currentText(), preset=self.preset.currentText(),
                                                  disable_hdr=remove_hdr,
                                                  keep_subtitles=self.keep_subtitles.isChecked(), crop=crop)

        self.create_button.setDisabled(True)
        self.kill_button.show()
        self.main.status.showMessage("Encoding...")
        logger.info("Converting video")
        self.encoding_worker = Worker(self, command, cmd_type="convert")
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


def message(msg, parent=None):
    sm = QtWidgets.QMessageBox(parent=parent)
    sm.setText(msg)
    sm.setStandardButtons(QtWidgets.QMessageBox.Ok)
    sm.exec_()


def error_message(msg, details=None, traceback=False, parent=None):
    em = QtWidgets.QMessageBox(parent=parent)
    em.setText(msg)
    if details:
        em.setDetailedText(details)
    elif traceback:
        import traceback
        em.setDetailedText(traceback.format_exc())
    em.setStandardButtons(QtWidgets.QMessageBox.Ok)
    em.exec_()


def get_file():
    ff_path = QtWidgets.QFileDialog()
    ff_path.setFileMode(QtWidgets.QFileDialog.ExistingFile)
    if ff_path.exec_():
        return ff_path.selectedFiles()[0]


def select_file(msg=''):
    if msg:
        message(msg)
    file_path = get_file()
    if not file_path:
        sys.exit(1)
    return file_path


def main():
    main_app = QtWidgets.QApplication(sys.argv)
    main_app.setStyle("fusion")
    main_app.setApplicationDisplayName("FastFlix")

    ffmpeg = os.getenv("FFMPEG", 'ffmpeg')
    ffmpeg_version = ff_version(ffmpeg, throw=False)

    ffprobe = os.getenv("FFPROBE", 'ffprobe')
    ffprobe_version = ff_version(ffprobe, throw=False)

    window = Main(ffmpeg=ffmpeg, ffprobe=ffprobe, ffmpeg_version=ffmpeg_version, ffprobe_version=ffprobe_version,
                  source=sys.argv[1] if len(sys.argv) > 1 else "")
    window.setFixedWidth(622)
    window.setFixedHeight(710)
    window.show()
    sys.exit(main_app.exec_())


if __name__ == '__main__':
    main()
