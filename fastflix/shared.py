# -*- coding: utf-8 -*-
import importlib.machinery
import logging
import os
import sys
from datetime import datetime, timedelta
from packaging import version as packaging_version
from pathlib import Path
from subprocess import run
import platform

from appdirs import user_data_dir
import importlib.resources
import requests
import reusables
from pathvalidate import sanitize_filepath


try:
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    # noinspection PyUnresolvedReferences
    base_path = sys._MEIPASS
    pyinstaller = True
except AttributeError:
    base_path = os.path.abspath(".")
    pyinstaller = False

from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.language import t
from fastflix.resources import get_bool_env

DEVMODE = get_bool_env("DEVMODE")

ref = importlib.resources.files("fastflix") / f"data/icon.ico"
with importlib.resources.as_file(ref) as icon_file:
    my_data = str(icon_file.resolve())

logger = logging.getLogger("fastflix")
no_border = (
    "QPushButton, QPushButton:hover, QPushButton:pressed {border-width: 0;} "
    "QPushButton:hover {border-bottom: 1px solid #aaa}"
)


class MyMessageBox(QtWidgets.QMessageBox):
    def __init__(self):
        QtWidgets.QMessageBox.__init__(self)
        self.setSizeGripEnabled(True)

    def event(self, e):
        result = QtWidgets.QMessageBox.event(self, e)

        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        self.setMinimumWidth(0)
        self.setMaximumWidth(16777215)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        text_edit = self.findChild(QtWidgets.QTextEdit)
        if text_edit is not None:
            text_edit.setMinimumHeight(0)
            text_edit.setMaximumHeight(16777215)
            text_edit.setMinimumWidth(0)
            text_edit.setMaximumWidth(16777215)
            text_edit.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        return result


def message(msg, title=None):
    sm = QtWidgets.QMessageBox()
    sm.setStyleSheet("font-size: 14px")
    sm.setText(msg)
    sm.setWindowFlags(sm.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
    if title:
        sm.setWindowTitle(title)
    sm.setStandardButtons(QtWidgets.QMessageBox.Ok)
    sm.setWindowIcon(QtGui.QIcon(my_data))
    sm.exec_()


def error_message(msg, details=None, traceback=False, title=None):
    em = MyMessageBox()
    em.setStyleSheet("font-size: 14px")
    em.setText(msg)
    em.setWindowIcon(QtGui.QIcon(my_data))
    em.setWindowFlags(em.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
    if title:
        em.setWindowTitle(title)
    if details:
        em.setInformativeText(details)
    elif traceback:
        import traceback

        em.setDetailedText(traceback.format_exc())
    em.setStandardButtons(QtWidgets.QMessageBox.Close)
    em.exec_()


def yes_no_message(msg, title=None, yes_text=t("Yes"), no_text=t("No"), yes_action=None, no_action=None):
    sm = QtWidgets.QMessageBox()
    sm.setStyleSheet("font-size: 14px")
    sm.setWindowTitle(t(title))
    sm.setText(msg)
    sm.addButton(yes_text, QtWidgets.QMessageBox.YesRole)
    sm.addButton(no_text, QtWidgets.QMessageBox.NoRole)
    sm.setWindowFlags(sm.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
    sm.exec_()
    if sm.clickedButton().text() == yes_text:
        if yes_action:
            return yes_action()
        return True
    elif sm.clickedButton().text() == no_text:
        if no_action:
            return no_action()
        return False
    return None


def latest_fastflix(app, show_new_dialog=False):
    from fastflix.version import __version__

    url = "https://api.github.com/repos/cdgriffith/FastFlix/releases"
    # contrib = link(
    #     url="https://github.com/sponsors/cdgriffith?frequency=one-time&sponsor=cdgriffith",
    #     text=t("Please consider supporting FastFlix with a one time contribution!"),
    #     theme=app.fastflix.config.theme,
    # )

    logger.debug("Checking for newer versions of FastFlix")

    try:
        response = requests.get(url, timeout=15 if not show_new_dialog else 3)
        response.raise_for_status()
        data = response.json()
    except Exception:
        logger.warning(t("Could not connect to github to check for newer versions"))
        if show_new_dialog:
            message(t("Could not connect to github to check for newer versions"))
        return

    versions = sorted(
        (tuple(int(y) for y in x["tag_name"].split(".")) for x in data if not x["prerelease"] and not x["draft"]),
        reverse=True,
    )

    use_version = ".".join(str(x) for x in versions[0])
    if reusables.win_based:
        try:
            win_ver = int(platform.platform().lower().split("-")[1])
        except Exception:
            logger.warning(f"Could not extract Windows version from {platform.platform()}, please report this message")
            win_ver = 0

        if win_ver < 10:
            logger.debug(f"Detected legacy Windows version {win_ver}, looking for 4.x builds only")
            for version in versions:
                if version[0] == 4:
                    use_version = ".".join(str(x) for x in version)
                    break
            else:
                logger.warning("No 4.x Versions found for legacy Windows")
                return

    release = [x for x in data if x["tag_name"] == use_version][0]

    if use_version != __version__ and packaging_version.parse(use_version) > packaging_version.parse(__version__):
        portable, installer = None, None
        for asset in release["assets"]:
            if asset["name"].endswith("win64.zip"):
                portable = asset["browser_download_url"]
            if asset["name"].endswith("installer.exe"):
                installer = asset["browser_download_url"]

        download_link = ""
        if installer:
            download_link += link(
                url=installer,
                text=f"{t('Download')} FastFlix {t('installer')} {use_version}",
                theme=app.fastflix.config.theme,
            )
            download_link += "<br><br>"
        if portable:
            download_link += link(
                url=portable,
                text=f"{t('Download')} FastFlix {t('portable')} {use_version}",
                theme=app.fastflix.config.theme,
            )
            download_link += "<br><br>"
        if (not portable and not installer) or not reusables.win_based:
            html_link = release["html_url"]
            download_link = link(
                url=html_link, text=f"{t('View')} FastFlix {use_version}", theme=app.fastflix.config.theme
            )
        logger.debug(f"Newer version found: {use_version}")
        message(
            f"{t('There is a newer version of FastFlix available!')} <br><br> {download_link} <br>",  # <br> {contrib} 💓<br>
            title=t("New Version"),
        )
        return
    logger.debug("FastFlix is up tp date")
    if show_new_dialog:
        message(t(f"You are using the latest version of FastFlix") + f" <br>")  # <br> {contrib} 💓 <br>


def file_date():
    return datetime.now().isoformat().replace(":", ".").rsplit(".", 1)[0]


def time_to_number(string_time: str) -> float:
    string_time = string_time.rstrip(".")
    try:
        return float(string_time)
    except ValueError:
        pass
    base, *extra = string_time.split(".")
    micro = 0
    if extra and len(extra) == 1:
        try:
            micro = int(extra[0])
        except ValueError:
            logger.info(t("bad micro value"))
            return 0
    total = float(f".{micro}")
    for i, v in enumerate(reversed(base.split(":"))):
        try:
            v = int(v)
        except ValueError:
            logger.info(f"{t('Not a valid int for time conversion')}: {v}")
        else:
            total += v * (60**i)
    return total


def link(url, text, theme):
    color = "#afccd5" if theme.lower() in ("dark", "onyx") else "black"
    return f'<a href="{url}" style="color: {color}" >{text}</a>'


def open_folder(path):
    try:
        if reusables.win_based:
            run(["explorer", path])
        elif sys.platform == "darwin":
            run(["open", path])
        else:
            run(["xdg-open", path])
    except FileNotFoundError:
        logger.error(f"Do not know which command to use to open: {path}")


def clean_logs(signal, app, **_):
    compress = []
    total_files = len(list(app.fastflix.log_path.iterdir()))
    for i, file in enumerate(app.fastflix.log_path.iterdir()):
        signal.emit(int((i / total_files) * 75))
        app.processEvents()
        if not file.name.endswith(".log"):
            continue
        try:
            is_old = (datetime.now() - datetime.fromisoformat(file.stem[-19:].replace(".", ":"))) > timedelta(days=14)
        except ValueError:
            is_old = True
        if file.name.startswith("flix_gui"):
            if is_old:
                logger.debug(f"Deleting {file.name}")
                file.unlink(missing_ok=True)
        if file.name.startswith("flix_conversion") or file.name.startswith("flix_2"):
            original = file.read_text(encoding="utf-8", errors="ignore")
            try:
                condensed = "\n".join(
                    (
                        line
                        for line in original.splitlines()
                        if "Skipping NAL unit" not in line and "Last message repeated" not in line
                    )
                )
            except UnicodeDecodeError:
                pass
            else:
                if (len(condensed) + 100) < len(original):
                    logger.debug(f"Compressed {file.name} from {len(original)} characters to {len(condensed)}")
                    file.write_text(condensed, encoding="utf-8")
            if is_old:
                logger.debug(f"Adding {file.name} to be compress")
                compress.append(file)
    if compress:
        reusables.pushd(app.fastflix.log_path)
        try:
            reusables.archive(
                [str(name.name) for name in compress],
                name=str(app.fastflix.log_path / f"flix_conversion_logs_{file_date()}.zip"),
            )
        finally:
            reusables.popd()
        signal.emit(95)
        for file in compress:
            file.unlink(missing_ok=True)
    signal.emit(100)


def timedelta_to_str(delta):
    if not isinstance(delta, (timedelta,)):
        logger.warning(f"Wanted timedelta found but found {type(delta)}")
        return "N/A"

    output_string = str(delta)
    output_string = output_string.split(".")[0]  # Remove .XXX microseconds

    return output_string


def clean_file_string(source):
    return str(source).strip().strip("'\"")


def quoted_path(source):
    cleaned_string = (
        str(source)
        .strip()
        .replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "'\\\\\\''")
        .replace("\r\n", "")
        .replace("\n", "")
        .replace("\r", "")
    )
    if " " in cleaned_string[0:4]:
        logger.warning(f"Unexpected space at start of quoted path, attempting to fix: {cleaned_string}")
        cleaned_string = cleaned_string[0:4].replace(" ", "") + cleaned_string[4:]
        logger.warning(f"New path set to: {cleaned_string}")
    return cleaned_string


def sanitize(source):
    return str(sanitize_filepath(source, platform="Windows" if reusables.win_based else "Linux"))
    # return str().replace("\\", "/")


def get_config(portable_mode=False):
    config = os.getenv("FF_CONFIG")
    if config:
        return Path(config)
    if Path("fastflix.yaml").exists() or portable_mode:
        return Path("fastflix.yaml")
    return Path(user_data_dir("FastFlix", appauthor=False, roaming=True)) / "fastflix.yaml"


def clear_list(the_list: list, close=False):
    for i in range(len(the_list) - 1, -1, -1):
        if close:
            the_list[i].close()
        del the_list[i]
