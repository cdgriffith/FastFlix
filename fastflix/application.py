# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import pkg_resources
import time
from collections import namedtuple
from typing import List

from qtpy import QtWidgets, QtGui, QtCore
from box import Box

from fastflix.flix import ffmpeg_configuration, ffmpeg_audio_encoders
from fastflix.models.config import Config, MissingFF
from fastflix.widgets.progress_bar import Task, ProgressBar
from fastflix.shared import latest_ffmpeg


def create_app():
    main_app = QtWidgets.QApplication(sys.argv)
    main_app.setStyle("fusion")
    main_app.setApplicationDisplayName("FastFlix")
    my_font = QtGui.QFont("helvetica", 9, weight=57)
    main_app.setFont(my_font)
    main_icon = str(Path(pkg_resources.resource_filename(__name__, "data/icon.ico")).resolve())
    main_app.setWindowIcon(QtGui.QIcon(main_icon))
    return main_app


if __name__ == "__main__":
    app = create_app()
    app.fastflix = Box(default_box=True)
    config = Config()
    try:
        config.load()
    except MissingFF:
        # TODO ask to download
        ProgressBar(app, config, [Task("Downloading FFmpeg", latest_ffmpeg, {})], signal_task=True)

    ProgressBar(
        app,
        config,
        [
            Task("Gather FFmpeg version", ffmpeg_configuration, {}),
            Task("Gather FFmpeg audio encoders", ffmpeg_audio_encoders, {}),
        ],
    )
    print(app.fastflix)
    # a = QtWidgets.QSplashScreen(QtGui.QPixmap(str(Path(pkg_resources.resource_filename(__name__, "data/splash_screens/loading.png")).resolve())))
    # a.show()
    # app.processEvents()
    #
    app.quit()
    # sys.exit(app.exec_())


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
