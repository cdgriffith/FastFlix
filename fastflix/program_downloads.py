#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import os
import shutil
import sys
from pathlib import Path
import re

import requests
import reusables
from appdirs import user_data_dir
from PySide6 import QtWidgets

from fastflix.language import t
from fastflix.shared import message
from fastflix.exceptions import FastFlixError

logger = logging.getLogger("fastflix")


def ask_for_ffmpeg():
    qm = QtWidgets.QMessageBox
    if reusables.win_based:
        ret = qm.question(
            None,
            t("FFmpeg not found!"),
            f"<h2>{t('FFmpeg not found!')}</h2> <br> {t('Automatically download FFmpeg?')}",
            qm.Yes | qm.No,
        )
        if ret == qm.Yes:
            return True
        else:
            sys.exit(1)
    else:
        qm.question(
            None,
            t("FFmpeg not found!"),
            f"<h2>{t('FFmpeg not found!')}</h2> "
            f"{t('Please')} <a href='https://ffmpeg.org/download.html'>{t('download a static FFmpeg')}</a> "
            f"{t('and add it to PATH')}",
            qm.Close,
        )
        sys.exit(1)


ffmpeg_version_re = re.compile(r"ffmpeg-n(\d+\.\d+)-latest-win64-gpl-")


def grab_stable_ffmpeg(signal, stop_signal, **_):
    return latest_ffmpeg(signal, stop_signal, ffmpeg_version="stable")


def latest_ffmpeg(signal, stop_signal, ffmpeg_version="latest", **_):
    stop = False
    logger.debug(f"Downloading {ffmpeg_version} FFmpeg")

    def stop_me():
        nonlocal stop
        stop = True

    stop_signal.connect(stop_me)
    ffmpeg_folder = Path(user_data_dir("FFmpeg", appauthor=False, roaming=True))
    ffmpeg_folder.mkdir(exist_ok=True)

    extract_folder = ffmpeg_folder / "temp_download"
    if extract_folder.exists():
        shutil.rmtree(extract_folder, ignore_errors=True)
    if extract_folder.exists():
        message(t("Could not delete previous temp extract directory: ") + str(extract_folder))
        raise FastFlixError("Could not delete previous temp extract directory")

    url = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest"

    try:
        data = requests.get(url, timeout=15).json()
    except Exception:
        shutil.rmtree(extract_folder, ignore_errors=True)
        message(t("Could not connect to github to check for newer versions."))
        raise

    if stop:
        shutil.rmtree(extract_folder, ignore_errors=True)
        message(t("Download Cancelled"))
        return

    gpl_ffmpeg = None

    if ffmpeg_version == "latest":
        for asset in data["assets"]:
            if "master-latest-win64-gpl.zip" in asset["name"]:
                gpl_ffmpeg = asset
                break
    else:
        versions = []
        for asset in data["assets"]:
            if ver_match := ffmpeg_version_re.search(asset["name"]):
                versions.append((float(ver_match.group(1)), asset))
        gpl_ffmpeg = sorted(versions, key=lambda x: x[0], reverse=True)[0][1]

    if not gpl_ffmpeg:
        shutil.rmtree(extract_folder, ignore_errors=True)
        message(
            t("Could not find any matching FFmpeg expected patterns, please check")
            + f" {t('latest release from')} <a href='https://github.com/BtbN/FFmpeg-Builds/releases/'>"
            "https://github.com/BtbN/FFmpeg-Builds/releases/</a> and reach out to FastFlix team about this issue if they exist."
        )
        raise Exception()

    logger.debug(f"Downloading version {gpl_ffmpeg['name']}")

    req = requests.get(gpl_ffmpeg["browser_download_url"], stream=True)

    filename = ffmpeg_folder / "ffmpeg-full.zip"
    with open(filename, "wb") as f:
        for i, block in enumerate(req.iter_content(chunk_size=1024)):
            if i % 1000 == 0.0:
                # logger.debug(f"Downloaded {i // 1000}MB")
                signal.emit(int(((i * 1024) / gpl_ffmpeg["size"]) * 90))
            f.write(block)
            if stop:
                f.close()
                Path(filename).unlink()
                shutil.rmtree(extract_folder, ignore_errors=True)
                message(t("Download Cancelled"))
                return

    if filename.stat().st_size < 1000:
        message(t("FFmpeg was not properly downloaded as the file size is too small"))
        try:
            Path(filename).unlink()
        except OSError:
            pass
        raise

    try:
        reusables.extract(filename, path=extract_folder)
    except Exception:
        message(f"{t('Could not extract FFmpeg files from')} {filename}!")
        raise

    if stop:
        Path(filename).unlink()
        shutil.rmtree(extract_folder, ignore_errors=True)
        message(t("Download Cancelled"))
        return

    signal.emit(95)

    try:
        shutil.rmtree(str(ffmpeg_folder / "bin"), ignore_errors=True)
        shutil.rmtree(str(ffmpeg_folder / "doc"), ignore_errors=True)
        (ffmpeg_folder / "LICENSE.txt").unlink(missing_ok=True)
        Path(filename).unlink()
    except OSError:
        pass

    signal.emit(96)
    sub_dir = next(Path(extract_folder).glob("ffmpeg-*"))

    for item in os.listdir(sub_dir):
        try:
            shutil.move(str(sub_dir / item), str(ffmpeg_folder))
        except Exception as err:
            message(f"{t('Error while moving files in')} {ffmpeg_folder}: {err}")
            raise
    signal.emit(98)
    shutil.rmtree(sub_dir, ignore_errors=True)
    signal.emit(100)
    # if done_alert:
    #     message(f"FFmpeg has been downloaded to {ffmpeg_folder}")
