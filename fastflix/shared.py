# -*- coding: utf-8 -*-
import importlib.machinery
import logging
import os
import sys
from datetime import datetime, timedelta
from distutils.version import StrictVersion
from pathlib import Path
from subprocess import run

import pkg_resources
import requests
import reusables

try:
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    # noinspection PyUnresolvedReferences
    base_path = sys._MEIPASS
    pyinstaller = True
except AttributeError:
    base_path = os.path.abspath(".")
    pyinstaller = False

from qtpy import QtCore, QtGui, QtWidgets

from fastflix.language import t

QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

main_width = 800

my_data = str(Path(pkg_resources.resource_filename(__name__, f"../data/icon.ico")).resolve())
icon = QtGui.QIcon(my_data)

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
    sm.setText(msg)
    if title:
        sm.setWindowTitle(title)
    sm.setStandardButtons(QtWidgets.QMessageBox.Ok)
    sm.setWindowIcon(icon)
    sm.exec_()


def error_message(msg, details=None, traceback=False, title=None):
    em = MyMessageBox()
    em.setText(msg)
    em.setWindowIcon(icon)
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
    sm.setWindowTitle(t(title))
    sm.setText(msg)
    sm.addButton(yes_text, QtWidgets.QMessageBox.YesRole)
    sm.addButton(no_text, QtWidgets.QMessageBox.NoRole)
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


def latest_fastflix(no_new_dialog=False):
    from fastflix.version import __version__

    url = "https://api.github.com/repos/cdgriffith/FastFlix/releases/latest"
    try:
        data = requests.get(url, timeout=15 if no_new_dialog else 3).json()
    except Exception:
        logger.warning(t("Could not connect to github to check for newer versions"))
        if no_new_dialog:
            message(t("Could not connect to github to check for newer versions"))
        return

    if data["tag_name"] != __version__ and StrictVersion(data["tag_name"]) > StrictVersion(__version__):
        portable, installer = None, None
        for asset in data["assets"]:
            if asset["name"].endswith("win64.zip"):
                portable = asset["browser_download_url"]
            if asset["name"].endswith("installer.exe"):
                installer = asset["browser_download_url"]

        download_link = ""
        if installer:
            download_link += (
                f"<a href='{installer}'>{t('Download')} FastFlix {t('installer')} {data['tag_name']}</a><br>"
            )
        if portable:
            download_link += f"<a href='{portable}'>{t('Download')} FastFlix {t('portable')} {data['tag_name']}</a><br>"
        if (not portable and not installer) or not reusables.win_based:
            html_link = data["html_url"]
            download_link = f"<a href='{html_link}'>{t('View')} FastFlix {data['tag_name']} now</a>"
        message(
            f"{t('There is a newer version of FastFlix available!')} <br> {download_link}",
            title=t("New Version"),
        )
        return
    if no_new_dialog:
        message(t("You are using the latest version of FastFlix"))


def file_date():
    return datetime.now().isoformat().replace(":", ".").rsplit(".", 1)[0]


def time_to_number(string_time: str) -> float:
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
            return
    total = float(f".{micro}")
    for i, v in enumerate(reversed(base.split(":"))):
        try:
            v = int(v)
        except ValueError:
            logger.info(f"{t('Not a valid int for time conversion')}: {v}")
        else:
            total += v * (60 ** i)
    return total


def link(url, text):
    return f'<a href="{url}" style="color: black" >{text}</a>'


def open_folder(path):
    if reusables.win_based:
        run(["explorer", path])
        # Also possible through ctypes shell extension
        # import ctypes
        #
        # ctypes.windll.ole32.CoInitialize(None)
        # pidl = ctypes.windll.shell32.ILCreateFromPathW(self.path)
        # ctypes.windll.shell32.SHOpenFolderAndSelectItems(pidl, 0, None, 0)
        # ctypes.windll.shell32.ILFree(pidl)
        # ctypes.windll.ole32.CoUninitialize()
    elif sys.platform == "darwin":
        run(["open", path])
    else:
        run(["xdg-open", path])


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
                file.unlink(missing_ok=True)
        if file.name.startswith("flix_conversion") or file.name.startswith("flix_2"):
            try:
                condensed = "\n".join(
                    (
                        line
                        for line in file.read_text(encoding="utf-8").splitlines()
                        if "Skipping NAL unit" not in line and "Last message repeated" not in line
                    )
                )
            except UnicodeDecodeError:
                pass
            else:
                file.write_text(condensed, encoding="utf-8")
            if is_old:
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
