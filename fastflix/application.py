# -*- coding: utf-8 -*-
import logging
import platform
import sys

import coloredlogs
import reusables
from PySide6 import QtGui, QtWidgets, QtCore

from fastflix.flix import (
    ffmpeg_audio_encoders,
    ffmpeg_video_encoders,
    ffmpeg_configuration,
    ffprobe_configuration,
    ffmpeg_opencl_support,
)
from fastflix.language import t
from fastflix.models.config import Config, MissingFF
from fastflix.models.fastflix import FastFlix
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.program_downloads import ask_for_ffmpeg, grab_stable_ffmpeg, download_hdr10plus_tool
from fastflix.resources import main_icon, breeze_styles_path
from fastflix.shared import file_date, message, latest_fastflix, DEVMODE, yes_no_message
from fastflix.ui_constants import FONTS
from fastflix.widgets.container import Container
from fastflix.widgets.status_bar import Task, STATE_IDLE, STATE_ERROR
from fastflix.gpu_detect import automatic_rigaya_download

logger = logging.getLogger("fastflix")


def create_app(enable_scaling):
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("cdgriffith.FastFlix")

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

    # On Linux, ensure an icon theme is set so QFileDialog toolbar icons appear
    if sys.platform == "linux" and not QtGui.QIcon.themeName():
        QtGui.QIcon.setThemeName("breeze")
    available_fonts = QtGui.QFontDatabase().families()
    font_preference = ["Roboto", "Segoe UI", "Ubuntu", "Open Sans", "Sans Serif"]
    selected_font = next((f for f in font_preference if f in available_fonts), "Sans Serif")
    my_font = QtGui.QFont(selected_font, FONTS.SMALL)
    main_app.setFont(my_font)
    icon = QtGui.QIcon()
    icon.addFile(main_icon, QtCore.QSize(16, 16))
    icon.addFile(main_icon, QtCore.QSize(32, 32))
    icon.addFile(main_icon, QtCore.QSize(48, 48))
    icon.addFile(main_icon, QtCore.QSize(256, 256))
    main_app.setWindowIcon(icon)
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
    level_styles = {
        "debug": {"color": "blue"},
        "info": {"color": "green"},
        "warning": {"color": "yellow", "bold": True},
        "error": {"color": "red", "bold": True},
    }
    coloredlogs.install(level="DEBUG", logger=logger, level_styles=level_styles)


def init_encoders(app: FastFlixApp, **_):
    from fastflix.encoders.av1_aom import main as av1_plugin
    from fastflix.encoders.avc_x264 import main as avc_plugin
    from fastflix.encoders.copy import main as copy_plugin
    from fastflix.encoders.gif import main as gif_plugin
    from fastflix.encoders.gifski import main as gifski_plugin
    from fastflix.encoders.ffmpeg_hevc_nvenc import main as nvenc_plugin
    from fastflix.encoders.ffmpeg_av1_nvenc import main as ffmpeg_av1_nvenc_plugin
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
    from fastflix.encoders.modify import main as modify_plugin

    encoders = [
        hevc_plugin,
        nvenc_plugin,
        hevc_videotoolbox_plugin,
        h264_videotoolbox_plugin,
        ffmpeg_av1_nvenc_plugin,
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
        modify_plugin,
    ]

    if DEVMODE or app.fastflix.config.gifski:
        encoders.insert(encoders.index(gif_plugin) + 1, gifski_plugin)

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

    # Mapping from requires values to search terms for ffmpeg -encoders output.
    # Most requires values (e.g. "vaapi", "libx264") appear directly in encoder names,
    # but some compilation flags don't match encoder names and need explicit mapping.
    requires_to_encoder = {
        "cuda-llvm": "nvenc",
    }

    def _encoder_available(requires: str) -> bool:
        if requires in app.fastflix.ffmpeg_config:
            return True
        search_term = requires_to_encoder.get(requires, requires)
        return any(search_term in enc for enc in (app.fastflix.video_encoders or []))

    app.fastflix.encoders = {
        encoder.name: encoder
        for encoder in encoders
        if (not getattr(encoder, "requires", None)) or _encoder_available(encoder.requires) or DEVMODE
    }


def init_fastflix_directories(app: FastFlixApp):
    app.fastflix.data_path.mkdir(parents=True, exist_ok=True)
    app.fastflix.log_path.mkdir(parents=True, exist_ok=True)


def _handle_ffmpeg_version_warning_windows(app: FastFlixApp, container: Container):
    msg = QtWidgets.QMessageBox(container)
    msg.setIcon(QtWidgets.QMessageBox.Warning)
    msg.setWindowTitle(t("FFmpeg Version Warning"))
    msg.setText(
        t(
            "Your FFmpeg (libavcodec {version}) is older than the required FFmpeg 8.0+ (libavcodec 62+)."
            " Some features may not work correctly."
        ).format(version=app.fastflix.libavcodec_version)
    )
    cb = QtWidgets.QCheckBox(t("Don't show this warning again"))
    msg.setCheckBox(cb)
    download_btn = msg.addButton(t("Download Latest"), QtWidgets.QMessageBox.AcceptRole)
    msg.addButton(t("Ignore"), QtWidgets.QMessageBox.RejectRole)
    msg.exec()

    if msg.clickedButton() == download_btn:
        try:
            container.status_bar.run_tasks(
                [Task(t("Downloading FFmpeg"), grab_stable_ffmpeg)],
                signal_task=True,
                can_cancel=True,
            )
            ffmpeg_configuration(app)
        except Exception:
            logger.exception("Failed to download FFmpeg")

    if cb.isChecked():
        app.fastflix.config.suppress_ffmpeg_version_warning = True
        app.fastflix.config.save()


def _handle_ffmpeg_version_warning_other(app: FastFlixApp):
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Warning)
    msg.setWindowTitle(t("FFmpeg Version Warning"))
    msg.setText(
        t(
            "Your FFmpeg (libavcodec {version}) is older than the required FFmpeg 8.0+ (libavcodec 62+)."
            " Please update FFmpeg. Visit https://ffmpeg.org/download.html"
        ).format(version=app.fastflix.libavcodec_version)
    )
    cb = QtWidgets.QCheckBox(t("Don't show this warning again"))
    msg.setCheckBox(cb)
    msg.addButton(t("OK"), QtWidgets.QMessageBox.AcceptRole)
    msg.exec()

    if cb.isChecked():
        app.fastflix.config.suppress_ffmpeg_version_warning = True
        app.fastflix.config.save()


def app_setup(
    enable_scaling: bool = True,
    portable_mode: bool = False,
    status_queue=None,
    log_queue=None,
    worker_queue=None,
):
    app = create_app(enable_scaling=enable_scaling)
    app.fastflix = FastFlix()
    app.fastflix.log_queue = log_queue
    app.fastflix.status_queue = status_queue
    app.fastflix.worker_queue = worker_queue

    app.fastflix.config = Config()
    init_fastflix_directories(app)
    init_logging(app)
    logger.debug(f"GUI logging initialized, saving to {app.fastflix.log_path}")
    upgraded = app.fastflix.config.upgrade_check()
    if upgraded:
        # No translation will be possible in this case
        message(
            f"Your config file has been upgraded to FastFlix's new YAML config format\n"
            f"{app.fastflix.config.config_path}",
            title="Upgraded",
        )
    missing_ff = False
    try:
        app.fastflix.config.load(portable_mode=portable_mode)
    except MissingFF as err:
        if reusables.win_based and ask_for_ffmpeg():
            # User wants to download FFmpeg — will be handled after Container is shown
            missing_ff = "download"
        else:
            missing_ff = str(err)
        logger.warning(f"FFmpeg not found during config load: {err}")
    except Exception:
        logger.exception(t("Could not load config file!"))
        sys.exit(1)

    if not app.fastflix.config.terms_accepted:
        from fastflix.widgets.terms_agreement import TermsAgreementDialog

        dialog = TermsAgreementDialog()
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            app.fastflix.config.terms_accepted = True
            app.fastflix.config.save()
        else:
            sys.exit(0)

    if app.fastflix.config.theme != "system":
        file = QtCore.QFile(str(breeze_styles_path / app.fastflix.config.theme / "stylesheet.qss"))
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

        # On Linux/KDE, applying a custom stylesheet can disrupt the platform
        # icon theme for standard dialog icons (e.g., QFileDialog toolbar).
        # Re-asserting the icon theme after stylesheet application restores them.
        if sys.platform == "linux":
            theme_name = QtGui.QIcon.themeName() or "breeze"
            QtGui.QIcon.setThemeName(theme_name)

    logger.setLevel(app.fastflix.config.logging_level)

    # Initialize empty encoder/audio lists so Container can be created before startup tasks
    if app.fastflix.encoders is None:
        app.fastflix.encoders = {}
    if app.fastflix.audio_encoders is None:
        app.fastflix.audio_encoders = []

    # Create and show Container immediately (UI starts disabled via Main.__init__)
    container = Container(app)
    container.show()

    cursor_pos = QtGui.QCursor.pos()
    screen = QtGui.QGuiApplication.screenAt(cursor_pos) or QtGui.QGuiApplication.primaryScreen()
    screen_geometry = screen.availableGeometry()
    container.move(screen_geometry.center() - container.rect().center())

    # Disable entire window during startup tasks
    container.setEnabled(False)
    app.processEvents()

    # Handle missing FFmpeg
    if missing_ff:
        if missing_ff == "download":
            # Download FFmpeg through status bar
            try:
                container.status_bar.run_tasks(
                    [Task(t("Downloading FFmpeg"), grab_stable_ffmpeg)],
                    signal_task=True,
                    persist_complete=True,
                )
                app.fastflix.config.load()
            except Exception as err:
                logger.exception(str(err))
                container.status_bar.set_state(
                    STATE_ERROR,
                    t("FFmpeg not found") + " — " + t("configure in Settings") + " (Ctrl+S)",
                )
                container.setEnabled(True)
                return app
        else:
            logger.error(
                f"Could not find {missing_ff} location, please manually set in {app.fastflix.config.config_path}"
            )
            container.status_bar.set_state(
                STATE_ERROR,
                t("FFmpeg not found") + " — " + t("configure in Settings") + " (Ctrl+S)",
            )
            container.setEnabled(True)
            return app

    # GPU detect and HDR10+ download (Windows only, with user permission dialogs)
    if platform.system() == "Windows":
        if app.fastflix.config.auto_gpu_check is None:
            app.fastflix.config.auto_gpu_check = yes_no_message(
                t(
                    "Do you want FastFlix to automatically detect your GPUs and download the optional encoders for them?\n\nThis will include downloading 7zip on Windows platform."
                ),
                title="Allow Optional Downloads",
            )
        if app.fastflix.config.auto_gpu_check:
            try:
                container.status_bar.run_tasks(
                    [Task(name=t("Detect GPUs"), command=automatic_rigaya_download)],
                    signal_task=True,
                    can_cancel=True,
                )
            except Exception:
                logger.exception("Failed to detect GPUs")

        if app.fastflix.config.auto_hdr10plus_check is None and not app.fastflix.config.hdr10plus_parser:
            app.fastflix.config.auto_hdr10plus_check = yes_no_message(
                t(
                    "HDR10+ tool not found. Do you want FastFlix to automatically download it?\n\nThis tool is used for extracting and injecting HDR10+ dynamic metadata during encoding."
                ),
                title="Download HDR10+ Tool",
            )
            if app.fastflix.config.auto_hdr10plus_check:
                try:
                    container.status_bar.run_tasks(
                        [Task(t("Downloading HDR10+ Tool"), download_hdr10plus_tool)],
                        signal_task=True,
                        can_cancel=True,
                    )
                    from fastflix.models.config import find_hdr10plus_tool

                    app.fastflix.config.hdr10plus_parser = find_hdr10plus_tool()
                except Exception:
                    logger.exception("Failed to download HDR10+ tool")

    if app.fastflix.config.enable_history is None:
        history_choice = yes_no_message(
            t("Would you like to enable encoding history?")
            + "\n\n"
            + t(
                "This keeps a local record of your completed encodings, letting you review the settings used for any past video and quickly re-apply them to new ones."
            )
            + "\n\n"
            + t("All data is stored locally on your computer. Nothing is sent to the internet."),
            title=t("Enable Encoding History"),
        )
        if history_choice is not None:
            app.fastflix.config.enable_history = history_choice
            if history_choice:
                container.rebuild_menu()

    app.fastflix.config.save()

    # Run startup tasks (FFmpeg config, encoder init) through status bar
    startup_tasks = [
        Task(t("Gather FFmpeg version"), ffmpeg_configuration),
        Task(t("Gather FFprobe version"), ffprobe_configuration),
        Task(t("Gather FFmpeg audio encoders"), ffmpeg_audio_encoders),
        Task(t("Gather FFmpeg video encoders"), ffmpeg_video_encoders),
        Task(t("Determine OpenCL Support"), ffmpeg_opencl_support),
        Task(t("Initialize Encoders"), init_encoders),
    ]

    try:
        container.status_bar.run_tasks(startup_tasks, persist_complete=True)
    except Exception:
        logger.exception(f"{t('Could not start FastFlix')}!")
        container.status_bar.set_state(STATE_ERROR, t("Could not start FastFlix"))
        container.setEnabled(True)
        return app

    # Check FFmpeg version (libavcodec 62 = FFmpeg 8.x)
    if not app.fastflix.config.suppress_ffmpeg_version_warning and 0 < app.fastflix.libavcodec_version < 62:
        if reusables.win_based:
            _handle_ffmpeg_version_warning_windows(app, container)
        else:
            _handle_ffmpeg_version_warning_other(app)

    # Encoders are now populated — initialize the encoder UI
    container.main.init_encoders_ui()

    # Re-enable UI after startup tasks complete
    container.setEnabled(True)
    container.status_bar.set_state(STATE_IDLE)

    if not app.fastflix.config.disable_version_check:
        QtCore.QTimer.singleShot(500, lambda: latest_fastflix(app=app, show_new_dialog=False))

    return app


def start_app(worker_queue, status_queue, log_queue, portable_mode=False, enable_scaling=True):
    # import tracemalloc
    #
    # tracemalloc.start()
    app = app_setup(
        enable_scaling=enable_scaling,
        portable_mode=portable_mode,
        status_queue=status_queue,
        log_queue=log_queue,
        worker_queue=worker_queue,
    )

    try:
        app.exec()
    except Exception:
        logger.exception("Error while running FastFlix")
        raise
