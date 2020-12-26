# -*- coding: utf-8 -*-
import logging
import sys
import traceback
from multiprocessing import Process, Queue

try:
    import coloredlogs
    import requests
    import reusables
    from appdirs import user_data_dir
    from box import Box

    import fastflix.language  # Have to set language first thing
    from fastflix.conversion_worker import queue_worker
    from fastflix.models.config import Config
    from fastflix.models.fastflix import FastFlix
    from fastflix.program_downloads import ask_for_ffmpeg, latest_ffmpeg
    from fastflix.shared import base_path, error_message, file_date, latest_fastflix, message
    from fastflix.version import __version__

except ImportError as err:
    traceback.print_exc()
    print("Could not load FastFlix properly!", file=sys.stderr)
    input("Please report this issue on https://github.com/cdgriffith/FastFlix/issues (press any key to exit)")
    sys.exit(1)


def separate_app_process(worker_queue, status_queue, log_queue):
    """ This prevents any QT components being imported in the main process"""
    from fastflix.application import start_app

    start_app(worker_queue, status_queue, log_queue)


def startup_options():
    options = sys.argv[1:]

    if "--test" in options:
        try:
            import appdirs
            import box
            import colorama
            import coloredlogs
            import iso639
            import mistune
            import qtpy
            import requests
            import reusables
            import ruamel.yaml

            import fastflix.encoders.av1_aom.main
            import fastflix.encoders.avc_x264.main
            import fastflix.encoders.common.attachments
            import fastflix.encoders.common.audio
            import fastflix.encoders.common.helpers
            import fastflix.encoders.common.setting_panel
            import fastflix.encoders.common.subtitles
            import fastflix.encoders.copy.main
            import fastflix.encoders.gif.main
            import fastflix.encoders.hevc_x265.main
            import fastflix.encoders.rav1e.main
            import fastflix.encoders.svt_av1.main
            import fastflix.encoders.vp9.main
            import fastflix.encoders.webp.main
            import fastflix.flix
            import fastflix.language
            import fastflix.models.base
            import fastflix.models.config
            import fastflix.models.encode
            import fastflix.models.fastflix
            import fastflix.models.fastflix_app
            import fastflix.models.video
            import fastflix.program_downloads
            import fastflix.resources
            import fastflix.shared
            import fastflix.version
            import fastflix.widgets.about
            import fastflix.widgets.changes
            import fastflix.widgets.container
            import fastflix.widgets.logs
            import fastflix.widgets.main
            import fastflix.widgets.panels.abstract_list
            import fastflix.widgets.panels.audio_panel
            import fastflix.widgets.panels.command_panel
            import fastflix.widgets.panels.cover_panel
            import fastflix.widgets.panels.queue_panel
            import fastflix.widgets.panels.status_panel
            import fastflix.widgets.panels.subtitle_panel
            import fastflix.widgets.profile_window
            import fastflix.widgets.progress_bar
            import fastflix.widgets.settings
            import fastflix.widgets.background_tasks
            import fastflix.widgets.video_options
        except Exception as err:
            print(f"Error: {err}")
            sys.exit(1)
        print("Success")
        sys.exit(0)
    if "--version" in options:
        print(__version__)
        sys.exit(0)


def main():
    startup_options()
    logger = logging.getLogger("fastflix-core")
    logger.addHandler(reusables.get_stream_handler(level=logging.DEBUG))
    logger.setLevel(logging.DEBUG)
    coloredlogs.install(level="DEBUG", logger=logger)
    logger.info(f"Starting FastFlix {__version__}")

    worker_queue = Queue()
    status_queue = Queue()
    log_queue = Queue()

    gui_proc = Process(
        target=separate_app_process,
        args=(
            worker_queue,
            status_queue,
            log_queue,
        ),
    )
    gui_proc.start()
    try:
        queue_worker(gui_proc, worker_queue, status_queue, log_queue)
    finally:
        gui_proc.join()
