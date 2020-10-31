# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import logging

from qtpy import QtWidgets, QtGui, QtCore
from box import Box
import coloredlogs
from appdirs import user_data_dir

from fastflix.flix import ffmpeg_configuration, ffmpeg_audio_encoders
from fastflix.models.config import Config, MissingFF
from fastflix.widgets.progress_bar import Task, ProgressBar
from fastflix.shared import latest_ffmpeg, file_date
from fastflix.resources import main_icon
from fastflix.version import __version__
from fastflix.language import t, change_language
from fastflix.widgets.container import Container
from fastflix.models.fastflix_app import FastFlixApp


def create_app():
    main_app = FastFlixApp(sys.argv)
    main_app.setStyle("fusion")
    main_app.setApplicationDisplayName("FastFlix")
    my_font = QtGui.QFont("helvetica", 9, weight=57)
    main_app.setFont(my_font)
    main_app.setWindowIcon(QtGui.QIcon(main_icon))
    return main_app


def init_logging(app: FastFlixApp):
    logging.basicConfig(level=logging.DEBUG)
    core_logger = logging.getLogger("fastflix-core")
    gui_logger = logging.getLogger("fastflix")
    coloredlogs.install(level="DEBUG", logger=core_logger)
    coloredlogs.install(level="DEBUG", logger=gui_logger)
    gui_logger.addHandler(logging.FileHandler(app.fastflix.log_path / f"flix_gui_{file_date()}.log", encoding="utf-8"))
    core_logger.info(f"{t('Starting')} FastFlix {__version__}")
    return gui_logger


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


def start_app(fastflix):
    app = create_app()
    app.fastflix = fastflix
    init_fastflix_directories(app)
    init_logging(app)
    try:
        app.fastflix.config.load()
    except MissingFF:
        change_language(app.fastflix.config.language)
        # TODO ask to download
        ProgressBar(app, [Task(t("Downloading FFmpeg"), latest_ffmpeg)], signal_task=True)
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

    # a = QtWidgets.QSplashScreen(QtGui.QPixmap(str(Path(pkg_resources.resource_filename(__name__, "data/splash_screens/loading.png")).resolve())))
    # a.show()
    # app.processEvents()
    #
    app.exec_()


# def start_app(queue, status_queue, log_queue, data_path, log_dir):
#     logger = logging.getLogger("fastflix")
#     coloredlogs.install(level="DEBUG", logger=logger)
#
#     logger.debug(f"Using qt engine {API} version {QT_VERSION}")
#
#     try:
#
#
#         flix, work_dir, config_file = required_info(logger, data_path, log_dir)
#         window = Container(
#             flix=flix,
#             source=sys.argv[1] if len(sys.argv) > 1 else "",
#             data_path=data_path,
#             work_path=work_dir,
#             config_file=config_file,
#             worker_queue=queue,
#             status_queue=status_queue,
#             log_queue=log_queue,
#             main_app=main_app,
#         )
#         main_app.setWindowIcon(window.icon)
#         window.show()
#         main_app.exec_()
#     except (Exception, BaseException, SystemError, SystemExit) as err:
#         logger.exception(f"HARD FAIL: Unexpected error: {err}")
#         print(f"Unexpected error: {err}")
#     else:
#         logger.info("Fastflix shutting down")
