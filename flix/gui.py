# -*- coding: utf-8 -*-
import sys
import logging
from logging.handlers import SocketHandler
from pathlib import Path
from distutils.version import StrictVersion
from datetime import datetime
import shutil

try:
    import pkg_resources.py2_warn  # Needed for pyinstaller on 3.8
except ImportError:
    pass

from appdirs import user_data_dir
from box import Box
import reusables

from flix.version import __version__
from flix.flix import ff_version, FlixError
from flix.shared import QtWidgets, error_message, base_path, Qt
from flix.widgets.container import Container

logger = logging.getLogger("flix")


def main():
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)-6s  %(levelname)-8s %(message)s")
    socket_handler = SocketHandler("127.0.0.1", 19996)
    logger.addHandler(socket_handler)

    main_app = QtWidgets.QApplication(sys.argv)
    main_app.setStyle("fusion")
    main_app.setApplicationDisplayName("FastFlix")

    data_path = Path(user_data_dir("FastFlix", appauthor=False, roaming=True))
    ffmpeg_folder = Path(user_data_dir("FFmpeg", appauthor=False, roaming=True))
    data_path.mkdir(parents=True, exist_ok=True)
    log_dir = data_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg = Path(shutil.which("ffmpeg"))
    ffprobe = Path(shutil.which("ffprobe"))
    svt_av1 = shutil.which("SvtAv1EncApp")

    if ffmpeg_folder.exists():
        for file in ffmpeg_folder.iterdir():
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
        config = Box.from_json(filename=config_file)
        if StrictVersion(config.version) < StrictVersion(__version__):
            # do upgrade of config
            config.version = __version__
            config.to_json(filename=config_file, indent=2)
        if "ffmpeg" in config:
            ffmpeg = Path(config.ffmpeg)
        if "ffprobe" in config:
            ffprobe = Path(config.ffprobe)
        if "svt_av1" in config:
            svt_av1 = Path(config.svt_av1)
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
            qm.question(
                None,
                "FFmpeg not found!",
                f"<h2>FFmpeg not found!</h2>"
                f"<br> Please <a href='https://ffmpeg.zeranoe.com/builds/'> download FFmpeg </a> "
                f"<br> <br>You must add ffmpeg.exe and ffprobe.exe to the folder:"
                f"<br> {ffmpeg_folder} "
                f"<br> or to the system path",
                qm.Close,
            )
        else:
            qm.question(
                None, "<h2>FFmpeg not found!</h2>", "Please download FFmpeg via your platform package manager", qm.Close
            )
        sys.exit(1)
    else:
        logger.info(f"Using ffmpeg {ffmpeg}")
        logger.info(f"Using ffprobe {ffprobe}")

    svt_av1_folder = Path(user_data_dir("SVT-AV1", appauthor=False, roaming=True))
    if not svt_av1 and svt_av1_folder.exists():
        svt_av1 = Path(svt_av1_folder, "SvtAv1EncApp.exe")

    if (not svt_av1 or not svt_av1.exists()) and reusables.win_based:
        qm = QtWidgets.QMessageBox
        ret = qm.question(
            None,
            "Download SVT-AV1",
            f"<h2>Would you like to download SVT-AV1?<h2>" f"<br> Will be placed in:" f"<br> {svt_av1_folder}",
            qm.Yes | qm.No,
        )
        if ret == qm.Yes:
            svt_av1_folder.mkdir(parents=True, exist_ok=True)
            try:
                download_svt_av1(svt_av1_folder)
            except Exception:
                logging.exception("Could not download newest SVT-AV1!")
                qm.question(None, "", f"Could not download SVT-AV1!", qm.Close)
                sys.exit(1)
            else:
                svt_av1 = Path(svt_av1_folder, "SvtAv1EncApp.exe")
    try:
        ffmpeg_version = ff_version(ffmpeg, throw=True)
        ffprobe_version = ff_version(ffprobe, throw=True)
    except FlixError:
        error_message("ffmpeg or ffmpeg could not be executed properly!")
        sys.exit(1)

    try:
        window = Container(
            ffmpeg=ffmpeg,
            ffprobe=ffprobe,
            ffmpeg_version=ffmpeg_version,
            ffprobe_version=ffprobe_version,
            svt_av1=svt_av1,
            source=sys.argv[1] if len(sys.argv) > 1 else "",
            data_path=data_path,
            work_path=work_dir,
        )
        window.show()
    except (Exception, BaseException, SystemError, SystemExit):
        logger.exception("HARD FAIL: Unexpected error")
        sys.exit(1)
    sys.exit(main_app.exec_())


def download_svt_av1(svt_av1_folder):
    import requests

    logger.info(f"Downloading SVT-AV1 to {svt_av1_folder}")

    if reusables.win_based:
        svt_av1_releases = requests.get(f"https://api.github.com/repos/OpenVisualCloud/SVT-AV1/releases").json()
        svt_av1_assets = requests.get(svt_av1_releases[0]["assets_url"]).json()
        for asset in svt_av1_assets:
            reusables.download(asset["browser_download_url"], save_dir=svt_av1_folder)


if __name__ == "__main__":
    main()
