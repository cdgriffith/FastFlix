# -*- coding: utf-8 -*-
import sys
import logging
from pathlib import Path
from distutils.version import StrictVersion
from datetime import datetime
import os
import shutil
import traceback
from json import JSONDecodeError
from multiprocessing import Process, Queue
from queue import Empty
from subprocess import Popen, PIPE, STDOUT
import time

try:
    import pkg_resources.py2_warn  # Needed for pyinstaller on 3.8
except ImportError:
    pass

try:
    from appdirs import user_data_dir
    from box import Box
    import reusables
    import requests
    import coloredlogs

    from fastflix.version import __version__
    from fastflix.flix import ff_version, FlixError
    from fastflix.shared import error_message, base_path, message
    from fastflix.widgets.container import Container
    from fastflix.widgets.command_runner import BackgroundRunner
except ImportError as err:
    traceback.print_exc()
    print("Could not load FastFlix properly!", file=sys.stderr)
    input("Please report this issue on https://github.com/cdgriffith/FastFlix/issues (press any key to exit)")
    sys.exit(1)


def main():
    logging.basicConfig(level=logging.DEBUG)

    queue = Queue()
    status_queue = Queue()
    runner = BackgroundRunner()
    gui_proc = Process(target=start_app, args=(queue, status_queue))
    gui_proc.start()

    logger = logging.getLogger("fastflix-core")
    coloredlogs.install(level="DEBUG", logger=logger)
    logger.info(f"Starting FastFlix {__version__}")

    finished_message = True
    sent_response = True
    gui_close_message = False
    queued_requests = []
    while True:
        if not gui_close_message and not gui_proc.is_alive():
            gui_proc.join()
            gui_close_message = True
            if runner.is_alive() or queued_requests:
                print("The GUI might have died, but I'm going to keep converting!")
            else:
                break
        try:
            request = queue.get(block=True, timeout=0.01)
        except Empty:
            if not runner.is_alive() and not sent_response and not queued_requests:
                excess = runner.process.stdout.read().strip()
                if excess:
                    logger.info(excess)
                ret = runner.process.poll()
                if ret > 0:
                    logger.warning(f"Error during conversion")
                else:
                    logger.info("conversion complete")
                status_queue.put("complete")
                sent_response = True

                if not gui_proc.is_alive():
                    return
        else:
            if request[0] == "command":
                if runner.is_alive():
                    queued_requests.append(request)
                else:
                    runner.start_exec(*request[1:])
                    finished_message = False
                    sent_response = False
            if request[0] == "cancel":
                runner.kill()
                status_queue.put("cancelled")
                sent_response = True
        if not runner.is_alive():
            if not finished_message:
                logger.info(runner.read() or "")
                finished_message = True
            if queued_requests:
                runner.start_exec(*queued_requests.pop()[1:])
                finished_message = False
                sent_response = False


def required_info(logger):
    if reusables.win_based:
        # This fixes the taskbar icon not always appearing
        try:
            import ctypes

            app_id = f"cdgriffith.fastflix.{__version__}".encode("utf-8")
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            logger.exception("Could not set application ID for Windows, please raise issue in github with above error")

    data_path = Path(user_data_dir("FastFlix", appauthor=False, roaming=True))
    ffmpeg_folder = Path(user_data_dir("FFmpeg", appauthor=False, roaming=True))
    data_path.mkdir(parents=True, exist_ok=True)
    log_dir = data_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        ffmpeg = Path(ffmpeg)
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        ffprobe = Path(ffprobe)

    if ffmpeg_folder.exists():
        for file in ffmpeg_folder.iterdir():
            if file.is_file() and file.name.lower() in ("ffmpeg", "ffmpeg.exe"):
                ffmpeg = file
            if file.is_file() and file.name.lower() in ("ffprobe", "ffprobe.exe"):
                ffprobe = file
        if (not ffmpeg or not ffprobe) and (ffmpeg_folder / "bin").exists():
            for file in (ffmpeg_folder / "bin").iterdir():
                if file.is_file() and file.name.lower() in ("ffmpeg", "ffmpeg.exe"):
                    ffmpeg = file
                if file.is_file() and file.name.lower() in ("ffprobe", "ffprobe.exe"):
                    ffprobe = file

    logger.addHandler(logging.FileHandler(log_dir / f"flix_{datetime.now().isoformat().replace(':', '.')}"))

    config_file = Path(data_path, "fastflix.json")
    if not config_file.exists():
        config = Box({"version": __version__, "work_dir": str(data_path)})
        config.to_json(filename=config_file, indent=2)
    else:
        try:
            config = Box.from_json(filename=config_file)
        except JSONDecodeError as err:
            logger.exception(f'Error with config file: "{config_file}"')
            error_message(
                msg=f"Bad config file: {config_file}"
                "<br> If you are unsure what to do, just delete the file"
                f"<br><br>Error: {err}",
                traceback=True,
            )
            sys.exit(1)
        if "version" not in config or "work_dir" not in config:
            message("Config file does not have all required fields, adding defaults")
            config.version = __version__
            config.work_dir = str(data_path)
            config.to_json(filename=config_file, indent=2)
        if StrictVersion(config.version) < StrictVersion(__version__):
            # do upgrade of config
            config.version = __version__
            config.to_json(filename=config_file, indent=2)
        if "ffmpeg" in config:
            ffmpeg = Path(config.ffmpeg)
        if "ffprobe" in config:
            ffprobe = Path(config.ffprobe)
    work_dir = Path(config.get("work_dir", data_path))
    if not work_dir.exists():
        try:
            work_dir.mkdir(parents=True, exist_ok=True)
        except OSError as err:
            logger.error(
                f"Cannot use specified working directory {work_dir}"
                f" - Falling back to {data_path} due to error: {err}"
            )
            work_dir = data_path
            work_dir.mkdir(parents=True, exist_ok=True)

    try:
        ffmpeg_version = ff_version(ffmpeg, throw=True)
        ffprobe_version = ff_version(ffprobe, throw=True)
    except FlixError:
        error_message("ffmpeg or ffmpeg could not be executed properly!")
        sys.exit(1)

    return ffmpeg, ffprobe, ffmpeg_version, ffprobe_version, data_path, work_dir, config_file


def start_app(queue, status_queue):

    logger = logging.getLogger("fastflix")
    coloredlogs.install(level="DEBUG", logger=logger)
    logger.info(f"Starting FastFlix {__version__}")

    (ffmpeg, ffprobe, ffmpeg_version, ffprobe_version, data_path, work_dir, config_file) = required_info(logger)

    from qtpy import QtWidgets
    from qtpy import QT_VERSION, API

    logger.debug(f"Using qt engine {API} version {QT_VERSION}")
    main_app = QtWidgets.QApplication(sys.argv)
    main_app.setStyle("fusion")
    main_app.setApplicationDisplayName("FastFlix")
    try:
        window = Container(
            ffmpeg=ffmpeg,
            ffprobe=ffprobe,
            ffmpeg_version=ffmpeg_version,
            ffprobe_version=ffprobe_version,
            source=sys.argv[1] if len(sys.argv) > 1 else "",
            data_path=data_path,
            work_path=work_dir,
            config_file=config_file,
            worker_queue=queue,
            status_queue=status_queue,
        )
        main_app.setWindowIcon(window.icon)
        window.show()
        main_app.exec_()
    except (Exception, BaseException, SystemError, SystemExit) as err:
        logger.exception(f"HARD FAIL: Unexpected error: {err}")
    else:
        logger.info("Fastflix shutting down")


def windows_download_ffmpeg(ffmpeg_folder):
    ffmpeg_folder.mkdir(exist_ok=True)
    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.zip"
    # logger.info(f"Downloading {url} to {ffmpeg_folder}")
    req = requests.get(url, headers={"referer": "https://www.gyan.dev"}, stream=True)
    with open(ffmpeg_folder / "ffmpeg-git-full.zip", "wb") as f:
        for block in req.iter_content(chunk_size=4096):
            f.write(block)

    reusables.extract(ffmpeg_folder / "ffmpeg-git-full.zip", path=ffmpeg_folder)
    sub_dir = ffmpeg_folder / "ffmpeg-latest-win64-static"

    for item in os.listdir(sub_dir):
        shutil.move(str(sub_dir / item), str(ffmpeg_folder))

    try:
        sub_dir.unlink()
        Path("ffmpeg-git-full.zip").unlink()
    except OSError:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        input(
            "Error while running FastFlix!\n"
            "Plese report this issue on https://github.com/cdgriffith/FastFlix/issues (press any key to exit)"
        )
