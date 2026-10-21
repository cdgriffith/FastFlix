#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import os
import shutil
import sys
from pathlib import Path
import hashlib
import re
import subprocess

import requests
import reusables
from platformdirs import user_data_dir
from PySide6 import QtWidgets

from fastflix.language import t
from fastflix.shared import message
from fastflix.exceptions import FastFlixError

logger = logging.getLogger("fastflix")

seven_zip_folder = Path(user_data_dir("7-Zip", appauthor=False, roaming=True))


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


ffmpeg_version_re = re.compile(r"^ffmpeg-n(\d+)\.(\d+)-latest-win64-gpl-\d+(?:\.\d+)*\.zip$")
latest_ffmpeg_name = "ffmpeg-master-latest-win64-gpl.zip"
REQUEST_TIMEOUT = 15
DOWNLOAD_TIMEOUT = 30


def get_release_json(url: str) -> dict:
    resp = requests.get(url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def release_assets(data) -> list:
    """Return the assets of a GitHub release response, with a clear error for API error payloads."""
    if not isinstance(data, dict) or "assets" not in data:
        detail = data.get("message", "") if isinstance(data, dict) else ""
        hint = " (GitHub API rate limit reached, try again later)" if "rate limit" in detail.lower() else ""
        raise FastFlixError(f"Unexpected response from GitHub: {detail or 'no assets listed'}{hint}")
    return data["assets"]


def select_stable_ffmpeg_asset(assets) -> dict | None:
    best = None
    best_version = None
    for asset in assets:
        if match := ffmpeg_version_re.match(asset["name"]):
            version = (int(match.group(1)), int(match.group(2)))
            if best_version is None or version > best_version:
                best, best_version = asset, version
    return best


def select_latest_ffmpeg_asset(assets) -> dict | None:
    for asset in assets:
        if asset["name"] == latest_ffmpeg_name:
            return asset
    return None


def expected_sha256(asset: dict, assets: list) -> str | None:
    """Find a published SHA256 for an asset: GitHub's `digest` field, or a checksums.sha256 file in the release."""
    digest = asset.get("digest")
    if isinstance(digest, str) and digest.lower().startswith("sha256:"):
        return digest.split(":", 1)[1].strip().lower()
    for other in assets:
        if other["name"] == "checksums.sha256":
            try:
                resp = requests.get(other["browser_download_url"], timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
            except Exception:
                logger.warning("Could not download checksums.sha256")
                return None
            for line in resp.text.splitlines():
                parts = line.split(maxsplit=1)
                if len(parts) == 2 and parts[1].strip().lstrip("*") == asset["name"]:
                    return parts[0].strip().lower()
    return None


def verify_sha256(path, expected: str | None):
    if not expected:
        logger.warning(f"No published checksum available for {Path(path).name}, skipping integrity verification")
        return
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(chunk)
    if sha.hexdigest().lower() != expected.lower():
        try:
            Path(path).unlink()
        except OSError:
            pass
        raise FastFlixError(f"SHA256 checksum mismatch for {Path(path).name}, download discarded")
    logger.debug(f"SHA256 verified for {Path(path).name}")


def download_file(url: str, filename, progress, is_stopped) -> bool:
    """Stream url to filename. Returns False (and removes the partial file) if cancelled."""
    req = requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT)
    req.raise_for_status()
    with open(filename, "wb") as f:
        for i, block in enumerate(req.iter_content(chunk_size=1024)):
            progress(i)
            f.write(block)
            if is_stopped():
                f.close()
                Path(filename).unlink(missing_ok=True)
                return False
    return True


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
        data = get_release_json(url)
        assets = release_assets(data)
    except Exception:
        shutil.rmtree(extract_folder, ignore_errors=True)
        message(t("Could not connect to github to check for newer versions."))
        raise

    if stop:
        shutil.rmtree(extract_folder, ignore_errors=True)
        message(t("Download Cancelled"))
        return

    if ffmpeg_version == "latest":
        gpl_ffmpeg = select_latest_ffmpeg_asset(assets)
    else:
        gpl_ffmpeg = select_stable_ffmpeg_asset(assets)

    if not gpl_ffmpeg:
        shutil.rmtree(extract_folder, ignore_errors=True)
        message(
            t("Could not find any matching FFmpeg expected patterns, please check")
            + f" {t('latest release from')} <a href='https://github.com/BtbN/FFmpeg-Builds/releases/'>"
            "https://github.com/BtbN/FFmpeg-Builds/releases/</a> and reach out to FastFlix team about this issue if they exist."
        )
        raise FastFlixError("Could not find a matching FFmpeg build in the latest release")

    logger.debug(f"Downloading version {gpl_ffmpeg['name']}")

    filename = ffmpeg_folder / "ffmpeg-full.zip"

    def progress(i):
        if i % 1000 == 0:
            signal.emit(int(((i * 1024) / gpl_ffmpeg["size"]) * 90))

    if not download_file(gpl_ffmpeg["browser_download_url"], filename, progress, lambda: stop):
        shutil.rmtree(extract_folder, ignore_errors=True)
        message(t("Download Cancelled"))
        return

    if filename.stat().st_size < 1000:
        message(t("FFmpeg was not properly downloaded as the file size is too small"))
        try:
            Path(filename).unlink()
        except OSError:
            pass
        raise FastFlixError("FFmpeg was not properly downloaded as the file size is too small")

    verify_sha256(filename, expected_sha256(gpl_ffmpeg, assets))

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
    sub_dir = next(Path(extract_folder).glob("ffmpeg-*"), None)
    if sub_dir is None:
        raise FastFlixError("Could not find the FFmpeg folder in the extracted files")

    for item in os.listdir(sub_dir):
        dest = ffmpeg_folder / item
        try:
            if dest.is_dir():
                shutil.rmtree(str(dest))
            elif dest.exists():
                dest.unlink()
            shutil.move(str(sub_dir / item), str(ffmpeg_folder))
        except Exception as err:
            message(f"{t('Error while moving files in')} {ffmpeg_folder}: {err}")
            raise
    signal.emit(98)
    shutil.rmtree(sub_dir, ignore_errors=True)
    signal.emit(100)
    # if done_alert:
    #     message(f"FFmpeg has been downloaded to {ffmpeg_folder}")


def download_rigaya(stop_signal, seven_zip_path, app_name="NVEnc", **_):
    """"""
    stop = False
    logger.debug(f"Downloading Rigaya {app_name}")

    def stop_me():
        nonlocal stop
        stop = True

    stop_signal.connect(stop_me)
    asset_folder = Path(user_data_dir(app_name, appauthor=False, roaming=True))
    asset_folder.mkdir(exist_ok=True)

    url = f"https://api.github.com/repos/rigaya/{app_name}/releases/latest"

    try:
        data = get_release_json(url)
        assets = release_assets(data)
    except Exception:
        logger.exception(t("Could not connect to GitHub to check for newer versions."))
        raise

    if stop:
        logger.error(t("Download Cancelled"))
        return

    asset = None
    for possible_asset in assets:
        if "x64.7z" in possible_asset["name"]:
            asset = possible_asset
            break

    if not asset:
        logger.error(
            "Could not find any matching expected patterns, please check"
            f" {t('latest release from')} <a href='https://github.com/rigaya/NVEnc/releases/'>"
            f"https://github.com/rigaya/{app_name}/releases/</a> "
            f"and reach out to FastFlix team about this issue if they exist."
        )
        raise FastFlixError(f"Could not find a matching {app_name} release asset")

    logger.debug(f"Downloading version {asset['name']}")

    filename = asset_folder / "download-full.7z"
    if not download_file(asset["browser_download_url"], filename, lambda i: None, lambda: stop):
        message(t("Download Cancelled"))
        return

    if filename.stat().st_size < 1000:
        logger.error(t("NVEnc was not properly downloaded as the file size is too small"))
        try:
            Path(filename).unlink()
        except OSError:
            pass
        raise FastFlixError(f"{app_name} was not properly downloaded as the file size is too small")

    verify_sha256(filename, expected_sha256(asset, assets))

    try:
        subprocess.run([seven_zip_path, "e", str(filename), "-o" + str(asset_folder), "-y"], check=True)
    except Exception:
        logger.exception("Could not extract nvenc files")
        raise

    if stop:
        Path(filename).unlink()
        return
    file = next(asset_folder.glob(f"{app_name}*64.exe"), None)
    if not file or not file.exists():
        logger.error(t("Could not find the executable in the extracted files"))
        raise FastFlixError(t("Could not find the executable in the extracted files"))
    return file


def download_7zip(stop_signal, **_):
    stop = False
    logger.debug("Downloading 7-Zip")

    def stop_me():
        nonlocal stop
        stop = True

    stop_signal.connect(stop_me)
    filename = seven_zip_folder / "7zr.exe"
    seven_zip_folder.mkdir(exist_ok=True)

    url = "https://www.7-zip.org/a/7zr.exe"

    try:
        if not download_file(url, filename, lambda i: None, lambda: stop):
            message(t("Download Cancelled"))
            return
    except Exception as e:
        raise FastFlixError(f"Could not download 7-Zip: {e}")

    if filename.stat().st_size < 1000:
        try:
            Path(filename).unlink()
        except OSError:
            pass
        raise FastFlixError("Could not download 7-Zip - filesize too small")

    logger.warning("No published checksum for 7zr.exe, skipping integrity verification")
    return filename


def download_hdr10plus_tool(signal, stop_signal, **_):
    stop = False
    logger.debug("Downloading hdr10plus_tool")

    def stop_me():
        nonlocal stop
        stop = True

    stop_signal.connect(stop_me)
    ffmpeg_folder = Path(user_data_dir("FFmpeg", appauthor=False, roaming=True))
    ffmpeg_folder.mkdir(exist_ok=True)

    extract_folder = ffmpeg_folder / "temp_hdr10plus_download"
    if extract_folder.exists():
        shutil.rmtree(extract_folder, ignore_errors=True)
    if extract_folder.exists():
        message(t("Could not delete previous temp extract directory: ") + str(extract_folder))
        raise FastFlixError("Could not delete previous temp extract directory")

    url = "https://api.github.com/repos/quietvoid/hdr10plus_tool/releases/latest"

    try:
        data = get_release_json(url)
        assets = release_assets(data)
    except Exception:
        shutil.rmtree(extract_folder, ignore_errors=True)
        message(t("Could not connect to github to check for newer versions."))
        raise

    if stop:
        shutil.rmtree(extract_folder, ignore_errors=True)
        message(t("Download Cancelled"))
        return

    asset = None
    for possible_asset in assets:
        if "x86_64-pc-windows-msvc.zip" in possible_asset["name"]:
            asset = possible_asset
            break

    if not asset:
        shutil.rmtree(extract_folder, ignore_errors=True)
        message(
            t("Could not find any matching expected patterns, please check")
            + f" {t('latest release from')} <a href='https://github.com/quietvoid/hdr10plus_tool/releases/'>"
            "https://github.com/quietvoid/hdr10plus_tool/releases/</a>"
        )
        raise FastFlixError("Could not find a matching hdr10plus_tool release asset")

    logger.debug(f"Downloading version {asset['name']}")

    filename = ffmpeg_folder / "hdr10plus_tool.zip"

    def progress(i):
        if i % 1000 == 0:
            signal.emit(int(((i * 1024) / asset["size"]) * 90))

    if not download_file(asset["browser_download_url"], filename, progress, lambda: stop):
        shutil.rmtree(extract_folder, ignore_errors=True)
        message(t("Download Cancelled"))
        return

    if filename.stat().st_size < 1000:
        message(t("hdr10plus_tool was not properly downloaded as the file size is too small"))
        try:
            Path(filename).unlink()
        except OSError:
            pass
        raise FastFlixError("hdr10plus_tool download too small")

    verify_sha256(filename, expected_sha256(asset, assets))

    try:
        reusables.extract(filename, path=extract_folder)
    except Exception:
        message(f"{t('Could not extract hdr10plus_tool files from')} {filename}!")
        raise

    if stop:
        Path(filename).unlink()
        shutil.rmtree(extract_folder, ignore_errors=True)
        message(t("Download Cancelled"))
        return

    signal.emit(95)

    try:
        Path(filename).unlink()
    except OSError:
        pass

    signal.emit(96)

    exe_file = None
    for item in extract_folder.rglob("hdr10plus_tool.exe"):
        exe_file = item
        break

    if not exe_file:
        shutil.rmtree(extract_folder, ignore_errors=True)
        raise FastFlixError("Could not find hdr10plus_tool.exe in extracted files")

    dest = ffmpeg_folder / "hdr10plus_tool.exe"
    try:
        shutil.move(str(exe_file), str(dest))
    except Exception as err:
        message(f"{t('Error while moving files in')} {ffmpeg_folder}: {err}")
        raise

    signal.emit(98)
    shutil.rmtree(extract_folder, ignore_errors=True)
    signal.emit(100)
    return dest


def find_seven_zip_windows() -> Path | None:
    """Finds the 7-Zip executable"""
    seven_zip_path = seven_zip_folder / "7zr.exe"
    seven_zip_on_path = shutil.which("7zr") or shutil.which("7z")
    if seven_zip_path.exists():
        return seven_zip_path
    if seven_zip_on_path:
        return Path(seven_zip_on_path)
    return None
