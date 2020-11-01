# -*- coding: utf-8 -*-
import sys
import logging

from qtpy import QtGui
import coloredlogs
import reusables

from fastflix.flix import ffmpeg_configuration, ffmpeg_audio_encoders
from fastflix.models.config import MissingFF
from fastflix.widgets.progress_bar import Task, ProgressBar
from fastflix.shared import file_date
from fastflix.resources import main_icon
from fastflix.version import __version__
from fastflix.language import t, change_language
from fastflix.widgets.container import Container
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.program_downloads import latest_ffmpeg, ask_for_ffmpeg

logger = logging.getLogger("fastflix")


def create_app():
    main_app = FastFlixApp(sys.argv)
    main_app.setStyle("fusion")
    main_app.setApplicationDisplayName("FastFlix")
    my_font = QtGui.QFont("helvetica", 9, weight=57)
    main_app.setFont(my_font)
    main_app.setWindowIcon(QtGui.QIcon(main_icon))
    return main_app


def init_logging(app: FastFlixApp):
    gui_logger = logging.getLogger("fastflix")
    stream_handler = reusables.get_stream_handler(level=logging.DEBUG)
    file_handler = reusables.get_file_handler(
        app.fastflix.log_path / f"flix_gui_{file_date()}.log",
        level=logging.DEBUG,
        encoding="utf-8",
    )
    gui_logger.setLevel(logging.DEBUG)
    gui_logger.addHandler(stream_handler)
    gui_logger.addHandler(file_handler)
    coloredlogs.install(level="DEBUG", logger=gui_logger)


def init_encoders(app: FastFlixApp, **_):
    from fastflix.encoders.av1_aom import main as av1_plugin
    from fastflix.encoders.avc_x264 import main as avc_plugin
    from fastflix.encoders.gif import main as gif_plugin
    from fastflix.encoders.hevc_x265 import main as hevc_plugin
    from fastflix.encoders.rav1e import main as rav1e_plugin
    from fastflix.encoders.svt_av1 import main as svt_av1_plugin
    from fastflix.encoders.vp9 import main as vp9_plugin
    from fastflix.encoders.webp import main as webp_plugin

    encoders = [hevc_plugin, avc_plugin, gif_plugin, vp9_plugin, webp_plugin, av1_plugin, rav1e_plugin, svt_av1_plugin]

    app.fastflix.encoders = {
        encoder.name: encoder
        for encoder in encoders
        if (not getattr(encoder, "requires", None)) or encoder.requires in app.fastflix.ffmpeg_config
    }


def init_fastflix_directories(app: FastFlixApp):
    app.fastflix.data_path.mkdir(parents=True, exist_ok=True)
    app.fastflix.log_path.mkdir(parents=True, exist_ok=True)


def register_app():
    """
    On Windows you have to set the AppUser Model ID or else the
    taskbar icon will not appear as expected.
    """
    if reusables.win_based:
        try:
            import ctypes

            app_id = f"cdgriffith.fastflix.{__version__}".encode("utf-8")
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            logger.exception("Could not set application ID for Windows, please raise issue in github with above error")


def start_app(fastflix):
    app = create_app()
    app.fastflix = fastflix
    init_fastflix_directories(app)
    init_logging(app)
    register_app()
    try:
        app.fastflix.config.load()
    except MissingFF:
        change_language(app.fastflix.config.language)
        if reusables.win_based and ask_for_ffmpeg():
            ProgressBar(app, [Task(t("Downloading FFmpeg"), latest_ffmpeg)], signal_task=True)
    except Exception as err:
        # TODO give edit / delete options
        logger.exception("Could not load config file!")
        sys.exit(1)
    else:
        change_language(app.fastflix.config.language)

    startup_tasks = [
        Task(t("Gather FFmpeg version"), ffmpeg_configuration),
        Task(t("Gather FFmpeg audio encoders"), ffmpeg_audio_encoders),
        Task(t("Initialize Encoders"), init_encoders),
    ]

    ProgressBar(app, startup_tasks)

    container = Container(app)
    container.show()

    app.exec_()
