# -*- coding: utf-8 -*-
import logging
import os
import shutil
import sys
import traceback
from datetime import datetime
from distutils.version import StrictVersion
from json import JSONDecodeError
from multiprocessing import Process, Queue, freeze_support
from pathlib import Path
from queue import Empty

try:
    import pkg_resources.py2_warn  # Needed for pyinstaller on 3.8
except ImportError:
    pass

try:
    import coloredlogs
    import requests
    import reusables
    from appdirs import user_data_dir
    from box import Box
    from qtpy import API, QT_VERSION, QtWidgets

    from fastflix.flix import FlixError, ff_version
    from fastflix.shared import base_path, error_message, message
    from fastflix.version import __version__
    from fastflix.widgets.command_runner import BackgroundRunner
    from fastflix.widgets.container import Container
except ImportError as err:
    traceback.print_exc()
    print("Could not load FastFlix properly!", file=sys.stderr)
    input("Please report this issue on https://github.com/cdgriffith/FastFlix/issues (press any key to exit)")
    sys.exit(1)


def file_date():
    return datetime.now().isoformat().replace(":", ".").rsplit(".")[0]


def main():
    logging.basicConfig(level=logging.DEBUG)
    data_path = Path(user_data_dir("FastFlix", appauthor=False, roaming=True))
    data_path.mkdir(parents=True, exist_ok=True)
    log_dir = data_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    queue = Queue()
    status_queue = Queue()
    log_queue = Queue()

    def log(msg, level=logging.INFO):
        log_queue.put(msg)
        logger.log(level, msg)

    runner = BackgroundRunner(log_queue=log_queue)
    gui_proc = Process(target=start_app, args=(queue, status_queue, log_queue, data_path, log_dir))
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
                log("The GUI might have died, but I'm going to keep converting!", logging.WARNING)
            else:
                break
        try:
            request = queue.get(block=True, timeout=0.01)
        except Empty:
            if not runner.is_alive() and not sent_response and not queued_requests:
                excess = runner.process.stdout.read().strip()
                if excess:
                    log(excess)
                ret = runner.process.poll()
                if ret > 0:
                    log(f"Error during conversion", logging.WARNING)
                else:
                    log("conversion complete")
                reusables.remove_file_handlers(logger)
                status_queue.put("complete")
                sent_response = True

                if not gui_proc.is_alive():
                    return
        else:
            if request[0] == "command":
                if runner.is_alive():
                    queued_requests.append(request)
                else:
                    log_queue.put("CLEAR_WINDOW")
                    reusables.remove_file_handlers(logger)
                    reusables.add_file_handler(
                        logger,
                        log_dir / f"flix_conversion_{file_date()}.log",
                        level=logging.DEBUG,
                        log_format="%(asctime)s - %(message)s",
                    )
                    runner.start_exec(*request[1:])
                    finished_message = False
                    sent_response = False
            if request[0] == "cancel":
                runner.kill()
                status_queue.put("cancelled")
                sent_response = True
        if not runner.is_alive():
            if not finished_message:
                log(runner.read() or "")
                finished_message = True
            if queued_requests:
                runner.start_exec(*queued_requests.pop()[1:])
                finished_message = False
                sent_response = False


def parse_changes(last_version=None):
    changes = (Path(__file__).parent / "CHANGES").read_text().splitlines()
    if last_version:
        version_hit = False
        last_line = None
        for i, line in enumerate(changes):
            if line.startswith(f"Version {last_version}"):
                version_hit = True
            if version_hit and not line.strip():
                last_line = i
                break
        if last_line:
            print("found last version")
            return "\n".join(changes[3:last_line])

    return "\n".join(changes[3:50])


def required_info(logger, data_path, log_dir):
    if reusables.win_based:
        # This fixes the taskbar icon not always appearing
        try:
            import ctypes

            app_id = f"cdgriffith.fastflix.{__version__}".encode("utf-8")
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            logger.exception("Could not set application ID for Windows, please raise issue in github with above error")

    ffmpeg_folder = Path(user_data_dir("FFmpeg", appauthor=False, roaming=True))
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

    logger.addHandler(logging.FileHandler(log_dir / f"flix_gui_{file_date()}.log"))

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
            message(
                f"<h2 style='text-align: center;'>Welcome to FastFlix {__version__}!</h2><br>"
                f"<p style='text-align: center; font-size: 15px;'>Please check out the changes made since your last update ({config.version})<br>View the change log in the Help menu (Alt+H then C)<br></p>"
            )
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

    if not ffmpeg or not ffprobe:
        qm = QtWidgets.QMessageBox
        if reusables.win_based:
            ret = qm.question(
                None,
                "FFmpeg not found!",
                f"<h2>FFmpeg not found!</h2>" f"<br> Automatically download FFmpeg?",
                qm.Yes | qm.No,
            )
            if ret == qm.Yes:
                try:
                    windows_download_ffmpeg(ffmpeg_folder)
                except Exception as err:
                    logger.exception("Could not download FFmpeg")
                    sys.exit(2)
                else:
                    ffmpeg = ffmpeg_folder / "bin" / "ffmpeg.exe"
                    ffprobe = ffmpeg_folder / "bin" / "ffprobe.exe"
            else:
                sys.exit(1)
        else:
            qm.question(
                None, "<h2>FFmpeg not found!</h2>", "Please download FFmpeg via your platform package manager", qm.Close
            )
            sys.exit(1)
    else:
        logger.info(f"Using ffmpeg {ffmpeg}")
        logger.info(f"Using ffprobe {ffprobe}")

    try:
        ffmpeg_version = ff_version(ffmpeg, throw=True)
        ffprobe_version = ff_version(ffprobe, throw=True)
    except FlixError:
        error_message("ffmpeg or ffmpeg could not be executed properly!<br>")
        sys.exit(1)

    return ffmpeg, ffprobe, ffmpeg_version, ffprobe_version, work_dir, config_file


def start_app(queue, status_queue, log_queue, data_path, log_dir):
    logger = logging.getLogger("fastflix")
    coloredlogs.install(level="DEBUG", logger=logger)
    logger.info(f"Starting FastFlix {__version__}")

    logger.debug(f"Using qt engine {API} version {QT_VERSION}")

    try:
        main_app = QtWidgets.QApplication(sys.argv)
        main_app.setStyle("fusion")
        main_app.setApplicationDisplayName("FastFlix")
        (ffmpeg, ffprobe, ffmpeg_version, ffprobe_version, work_dir, config_file) = required_info(
            logger, data_path, log_dir
        )
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
            log_queue=log_queue,
        )
        main_app.setWindowIcon(window.icon)
        window.show()
        main_app.exec_()
    except (Exception, BaseException, SystemError, SystemExit) as err:
        logger.exception(f"HARD FAIL: Unexpected error: {err}")
        print(f"Unexpected error: {err}")
    else:
        logger.info("Fastflix shutting down")
        for item in Path(work_dir).iterdir():
            if item.is_dir() and item.stem.startswith("temp_"):
                shutil.rmtree(item, ignore_errors=True)
        thumb = Path(work_dir) / "thumbnail_preview.png"
        if thumb.exists():
            thumb.unlink(missing_ok=True)


def windows_download_ffmpeg(ffmpeg_folder):
    ffmpeg_folder.mkdir(exist_ok=True)
    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.zip"
    req = requests.get(url, headers={"referer": "https://www.gyan.dev"}, stream=True)
    with open(ffmpeg_folder / "ffmpeg-git-full.zip", "wb") as f:
        for i, block in enumerate(req.iter_content(chunk_size=1024)):
            if i % 1000 == 0.0:
                print(f"Downloaded {i // 1000}MB")
            f.write(block)

    reusables.extract(ffmpeg_folder / "ffmpeg-git-full.zip", path=ffmpeg_folder)
    try:
        Path(ffmpeg_folder / "ffmpeg-git-full.zip").unlink()
    except OSError:
        pass

    sub_dir = next(Path(ffmpeg_folder).glob("ffmpeg-*"))

    for item in os.listdir(sub_dir):
        shutil.move(str(sub_dir / item), str(ffmpeg_folder))

    shutil.rmtree(sub_dir, ignore_errors=True)


if __name__ == "__main__":
    freeze_support()
    try:
        main()
    except Exception:
        traceback.print_exc()
        input(
            "Error while running FastFlix!\n"
            "Plese report this issue on https://github.com/cdgriffith/FastFlix/issues (press any key to exit)"
        )
