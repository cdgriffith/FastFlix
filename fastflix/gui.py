# -*- coding: utf-8 -*-
import sys
import logging
from logging.handlers import SocketHandler
from pathlib import Path
from distutils.version import StrictVersion
from datetime import datetime
import os
import shutil
import traceback

try:
    import pkg_resources.py2_warn  # Needed for pyinstaller on 3.8
except ImportError:
    pass

try:
    from appdirs import user_data_dir
    from box import Box
    import reusables
    import requests

    from fastflix.version import __version__
    from fastflix.flix import ff_version, FlixError
    from fastflix.shared import QtWidgets, error_message, base_path, Qt
    from fastflix.widgets.container import Container
except ImportError as err:
    traceback.print_exc()
    print("Could not load FastFlix properly!", file=sys.stderr)
    input("Plese report this issue on https://github.com/cdgriffith/FastFlix/issues (press any key to exit)")
    sys.exit(1)

logger = logging.getLogger("fastflix")


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

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        ffmpeg = Path(ffmpeg)
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        ffprobe = Path(ffprobe)
    svt_av1 = shutil.which("SvtAv1EncApp")

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

    svt_av1_folder = Path(user_data_dir("SVT-AV1", appauthor=False, roaming=True))
    if not svt_av1 and svt_av1_folder.exists():
        svt_av1 = Path(svt_av1_folder, "SvtAv1EncApp.exe")

    if (not svt_av1 or not svt_av1.exists()) and reusables.win_based:
        qm = QtWidgets.QMessageBox
        ret = qm.question(
            None,
            "Download SVT-AV1",
            f"<h2>Would you like to download SVT-AV1?</h2>" f"<br> Will be placed in:" f"<br> {svt_av1_folder}",
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
    logger.info(f"Downloading SVT-AV1 to {svt_av1_folder}")

    if reusables.win_based:
        svt_av1_releases = requests.get(f"https://api.github.com/repos/OpenVisualCloud/SVT-AV1/releases").json()
        svt_av1_assets = requests.get(svt_av1_releases[0]["assets_url"]).json()
        for asset in svt_av1_assets:
            reusables.download(asset["browser_download_url"], save_dir=svt_av1_folder)


def windows_download_ffmpeg(ffmpeg_folder):
    ffmpeg_folder.mkdir(exist_ok=True)
    url = "https://ffmpeg.zeranoe.com/builds/win64/static/ffmpeg-latest-win64-static.zip"
    logger.info(f"Downloading {url} to {ffmpeg_folder}")
    req = requests.get(url, headers={"referer": "https://ffmpeg.zeranoe.com/"}, stream=True,)
    with open(ffmpeg_folder / "ffmpeg-latest-win64-static.zip", "wb") as f:
        for block in req.iter_content(chunk_size=4096):
            f.write(block)

    reusables.extract(ffmpeg_folder / "ffmpeg-latest-win64-static.zip", path=ffmpeg_folder)
    sub_dir = ffmpeg_folder / "ffmpeg-latest-win64-static"

    for item in os.listdir(sub_dir):
        shutil.move(str(sub_dir / item), str(ffmpeg_folder))

    try:
        sub_dir.unlink()
        Path("ffmpeg-latest-win64-static.zip").unlink()
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
