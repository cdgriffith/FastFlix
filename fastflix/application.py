# -*- coding: utf-8 -*-
import logging
import sys

import coloredlogs
import reusables
from PySide6 import QtGui, QtWidgets, QtCore

from fastflix.flix import ffmpeg_audio_encoders, ffmpeg_configuration, ffprobe_configuration, ffmpeg_opencl_support
from fastflix.language import t
from fastflix.models.config import Config, MissingFF
from fastflix.models.fastflix import FastFlix
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.program_downloads import ask_for_ffmpeg, grab_stable_ffmpeg
from fastflix.resources import main_icon, breeze_styles_path
from fastflix.shared import file_date, message, latest_fastflix, DEVMODE
from fastflix.widgets.container import Container
from fastflix.widgets.progress_bar import ProgressBar, Task

logger = logging.getLogger("fastflix")


def create_app(enable_scaling):
    if enable_scaling:
        if hasattr(QtCore.Qt, "AA_EnableHighDpiScaling"):
            QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
        if hasattr(QtCore.Qt, "AA_UseHighDpiPixmaps"):
            QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    else:
        QtWidgets.QApplication.setHighDpiScaleFactorRoundingPolicy(QtCore.Qt.HighDpiScaleFactorRoundingPolicy.Floor)

    if reusables.win_based:
        sys.argv += ["-platform", "windows:darkmode=2"]
    main_app = FastFlixApp(sys.argv)
    main_app.allWindows()
    main_app.setApplicationDisplayName("FastFlix")
    my_font = QtGui.QFont("Arial" if "Arial" in QtGui.QFontDatabase().families() else "Sans Serif", 9)
    main_app.setFont(my_font)
    main_app.setWindowIcon(QtGui.QIcon(main_icon))
    return main_app


def init_logging(app: FastFlixApp):
    stream_handler = reusables.get_stream_handler(level=logging.DEBUG)
    file_handler = reusables.get_file_handler(
        app.fastflix.log_path / f"flix_gui_{file_date()}.log",
        level=logging.DEBUG,
        encoding="utf-8",
    )
    logger.setLevel(logging.DEBUG)
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    coloredlogs.install(level="DEBUG", logger=logger)


def init_encoders(app: FastFlixApp, **_):
    from fastflix.encoders.av1_aom import main as av1_plugin
    from fastflix.encoders.avc_x264 import main as avc_plugin
    from fastflix.encoders.copy import main as copy_plugin
    from fastflix.encoders.gif import main as gif_plugin
    from fastflix.encoders.ffmpeg_hevc_nvenc import main as nvenc_plugin
    from fastflix.encoders.hevc_x265 import main as hevc_plugin
    from fastflix.encoders.rav1e import main as rav1e_plugin
    from fastflix.encoders.svt_av1 import main as svt_av1_plugin
    from fastflix.encoders.vp9 import main as vp9_plugin
    from fastflix.encoders.webp import main as webp_plugin
    from fastflix.encoders.qsvencc_hevc import main as qsvencc_plugin
    from fastflix.encoders.qsvencc_avc import main as qsvencc_avc_plugin
    from fastflix.encoders.nvencc_hevc import main as nvencc_plugin
    from fastflix.encoders.nvencc_avc import main as nvencc_avc_plugin
    from fastflix.encoders.vceencc_hevc import main as vceencc_hevc_plugin
    from fastflix.encoders.vceencc_avc import main as vceencc_avc_plugin
    from fastflix.encoders.hevc_videotoolbox import main as hevc_videotoolbox_plugin
    from fastflix.encoders.h264_videotoolbox import main as h264_videotoolbox_plugin
    from fastflix.encoders.svt_av1_avif import main as svt_av1_avif_plugin
    from fastflix.encoders.nvencc_av1 import main as nvencc_av1_plugin
    from fastflix.encoders.qsvencc_av1 import main as qsvencc_av1_plugin
    from fastflix.encoders.vceencc_av1 import main as vceencc_av1_plugin
    from fastflix.encoders.vvc import main as vvc_plugin
    from fastflix.encoders.vaapi_h264 import main as vaapi_h264_plugin
    from fastflix.encoders.vaapi_hevc import main as vaapi_hevc_plugin
    from fastflix.encoders.vaapi_vp9 import main as vaapi_vp9_plugin
    from fastflix.encoders.vaapi_mpeg2 import main as vaapi_mpeg2_plugin

    encoders = [
        hevc_plugin,
        nvenc_plugin,
        hevc_videotoolbox_plugin,
        h264_videotoolbox_plugin,
        av1_plugin,
        rav1e_plugin,
        svt_av1_plugin,
        svt_av1_avif_plugin,
        avc_plugin,
        vp9_plugin,
        gif_plugin,
        webp_plugin,
        vvc_plugin,
        vaapi_hevc_plugin,
        vaapi_h264_plugin,
        vaapi_vp9_plugin,
        vaapi_mpeg2_plugin,
        copy_plugin,
    ]

    if DEVMODE:
        encoders.insert(1, qsvencc_plugin)
        encoders.insert(encoders.index(av1_plugin), qsvencc_av1_plugin)
        encoders.insert(encoders.index(avc_plugin), qsvencc_avc_plugin)
        encoders.insert(1, nvencc_plugin)
        encoders.insert(encoders.index(av1_plugin), nvencc_av1_plugin)
        encoders.insert(encoders.index(avc_plugin), nvencc_avc_plugin)
        encoders.insert(1, vceencc_hevc_plugin)
        encoders.insert(encoders.index(av1_plugin), vceencc_av1_plugin)
        encoders.insert(encoders.index(avc_plugin), vceencc_avc_plugin)
    else:
        if app.fastflix.config.qsvencc:
            # if "H.265/HEVC" in app.fastflix.config.qsvencc_encoders:
            encoders.insert(1, qsvencc_plugin)
            # if "AV1" in app.fastflix.config.qsvencc_encoders:
            encoders.insert(encoders.index(av1_plugin), qsvencc_av1_plugin)
            # if "H.264/AVC" in app.fastflix.config.qsvencc_encoders:
            encoders.insert(encoders.index(avc_plugin), qsvencc_avc_plugin)

        if app.fastflix.config.nvencc:
            # if "H.265/HEVC" in app.fastflix.config.nvencc_encoders:
            encoders.insert(1, nvencc_plugin)
            # if "AV1" in app.fastflix.config.nvencc_encoders:
            encoders.insert(encoders.index(av1_plugin), nvencc_av1_plugin)
            # if "H.264/AVC" in app.fastflix.config.nvencc_encoders:
            encoders.insert(encoders.index(avc_plugin), nvencc_avc_plugin)

        if app.fastflix.config.vceencc:
            # if reusables.win_based: # and "H.265/HEVC" in app.fastflix.config.vceencc_encoders:
            # HEVC AMF support only works on windows currently
            encoders.insert(1, vceencc_hevc_plugin)
            # if "AV1" in app.fastflix.config.vceencc_encoders:
            encoders.insert(encoders.index(av1_plugin), vceencc_av1_plugin)
            # if "H.264/AVC" in app.fastflix.config.vceencc_encoders:
            encoders.insert(encoders.index(avc_plugin), vceencc_avc_plugin)

    app.fastflix.encoders = {
        encoder.name: encoder
        for encoder in encoders
        if (not getattr(encoder, "requires", None)) or encoder.requires in app.fastflix.ffmpeg_config or DEVMODE
    }


def init_fastflix_directories(app: FastFlixApp):
    app.fastflix.data_path.mkdir(parents=True, exist_ok=True)
    app.fastflix.log_path.mkdir(parents=True, exist_ok=True)


def app_setup(
    enable_scaling: bool = True,
    portable_mode: bool = False,
    queue_list: list = None,
    queue_lock=None,
    status_queue=None,
    log_queue=None,
    worker_queue=None,
):
    app = create_app(enable_scaling=enable_scaling)
    app.fastflix = FastFlix(queue=queue_list, queue_lock=queue_lock)
    app.fastflix.log_queue = log_queue
    app.fastflix.status_queue = status_queue
    app.fastflix.worker_queue = worker_queue

    app.fastflix.config = Config()
    init_fastflix_directories(app)
    init_logging(app)
    upgraded = app.fastflix.config.upgrade_check()
    if upgraded:
        # No translation will be possible in this case
        message(
            f"Your config file has been upgraded to FastFlix's new YAML config format\n"
            f"{app.fastflix.config.config_path}",
            title="Upgraded",
        )
    try:
        app.fastflix.config.load(portable_mode=portable_mode)
    except MissingFF as err:
        if reusables.win_based and ask_for_ffmpeg():
            try:
                ProgressBar(app, [Task(t("Downloading FFmpeg"), grab_stable_ffmpeg)], signal_task=True)
                app.fastflix.config.load()
            except Exception as err:
                logger.exception(str(err))
                sys.exit(1)
        else:
            logger.error(f"Could not find {err} location, please manually set in {app.fastflix.config.config_path}")
            sys.exit(1)
    except Exception:
        # TODO give edit / delete options
        logger.exception(t("Could not load config file!"))
        sys.exit(1)

    if app.fastflix.config.theme != "system":
        QtCore.QDir.addSearchPath(app.fastflix.config.theme, str(breeze_styles_path / app.fastflix.config.theme))
        file = QtCore.QFile(f"{app.fastflix.config.theme}:stylesheet.qss")
        file.open(QtCore.QFile.OpenModeFlag.ReadOnly | QtCore.QFile.OpenModeFlag.Text)
        stream = QtCore.QTextStream(file)
        data = stream.readAll()
        dark = str(breeze_styles_path / "dark")
        light = str(breeze_styles_path / "light")
        onyx = str(breeze_styles_path / "onyx")
        if reusables.win_based:
            dark = dark.replace("\\", "/")
            light = light.replace("\\", "/")
            onyx = onyx.replace("\\", "/")
        data = data.replace("url(dark:", f"url({dark}/")
        data = data.replace("url(light:", f"url({light}/")
        data = data.replace("url(onyx:", f"url({onyx}/")

        app.setStyleSheet(data)

    logger.setLevel(app.fastflix.config.logging_level)

    startup_tasks = [
        Task(t("Gather FFmpeg version"), ffmpeg_configuration),
        Task(t("Gather FFprobe version"), ffprobe_configuration),
        Task(t("Gather FFmpeg audio encoders"), ffmpeg_audio_encoders),
        Task(t("Determine OpenCL Support"), ffmpeg_opencl_support),
        Task(t("Initialize Encoders"), init_encoders),
    ]

    try:
        ProgressBar(app, startup_tasks)
    except Exception:
        logger.exception(f'{t("Could not start FastFlix")}!')
        sys.exit(1)

    container = Container(app)
    container.show()

    container.move(QtGui.QGuiApplication.primaryScreen().availableGeometry().center() - container.rect().center())

    if not app.fastflix.config.disable_version_check:
        latest_fastflix(app=app, show_new_dialog=False)

    return app


def start_app(worker_queue, status_queue, log_queue, queue_list, queue_lock, portable_mode=False, enable_scaling=True):
    # import tracemalloc
    #
    # tracemalloc.start()

    app = app_setup(
        enable_scaling=enable_scaling,
        portable_mode=portable_mode,
        queue_list=queue_list,
        queue_lock=queue_lock,
        status_queue=status_queue,
        log_queue=log_queue,
        worker_queue=worker_queue,
    )

    try:
        app.exec_()
    except Exception:
        logger.exception("Error while running FastFlix")
        raise
