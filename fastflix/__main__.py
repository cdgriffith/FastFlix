# -*- coding: utf-8 -*-
import multiprocessing
import os
import sys
import traceback
from multiprocessing import freeze_support
from pathlib import Path

if sys.platform == "win32":
    import ctypes

    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("cdgriffith.FastFlix")

from fastflix.entry import main


def setup_ocr_environment():
    """Set up environment variables for OCR tools early in app startup.

    This is necessary for PyInstaller frozen executables where os.environ
    modifications later in the code don't properly propagate to subprocesses.
    """
    from fastflix.models.config import find_ocr_tool

    # Find tesseract and add to PATH
    tesseract_path = find_ocr_tool("tesseract")
    if tesseract_path:
        tesseract_dir = str(Path(tesseract_path).parent)
        os.environ["PATH"] = f"{tesseract_dir}{os.pathsep}{os.environ.get('PATH', '')}"
        os.environ["TESSERACT_CMD"] = str(tesseract_path)

    # Find mkvmerge and add MKVToolNix to PATH
    mkvmerge_path = find_ocr_tool("mkvmerge")
    if mkvmerge_path:
        mkvtoolnix_dir = str(Path(mkvmerge_path).parent)
        os.environ["PATH"] = f"{mkvtoolnix_dir}{os.pathsep}{os.environ.get('PATH', '')}"


def configure_multiprocessing():
    """Use the "fork" start method on Linux, which was the default before Python 3.14.

    Python 3.14 switched the Linux default to "forkserver". In frozen (PyInstaller) builds the forkserver is started
    by re-running the executable, which starts FastFlix again instead, so every GUI process launch spawned another
    FastFlix until the system ran out of memory (#750). The main process never imports Qt, so forking it is safe.
    """
    if not sys.platform.startswith("linux") or multiprocessing.get_start_method(allow_none=True) is not None:
        return
    try:
        multiprocessing.set_start_method("fork")
    except (RuntimeError, ValueError):
        pass


def start_fastflix():
    exit_code = 2
    configure_multiprocessing()

    # Portable mode: Go launcher sets FASTFLIX_PORTABLE=1, PyInstaller uses portable.py import
    portable_mode = os.environ.get("FASTFLIX_PORTABLE") == "1"
    if not portable_mode:
        try:
            from fastflix import portable  # noqa: F401

            portable_mode = True
        except ImportError:
            pass

    if portable_mode:
        print("PORTABLE MODE DETECTED: now using local config file and workspace in same directory as the executable")

    # Set up OCR environment variables early for PyInstaller compatibility
    setup_ocr_environment()

    try:
        exit_code = main(portable_mode)
    except Exception:
        traceback.print_exc()
        input(
            "Error while running FastFlix!\n"
            "Please report this issue on https://github.com/cdgriffith/FastFlix/issues (press any key to exit)"
        )
    except KeyboardInterrupt:
        pass
    finally:
        sys.exit(exit_code)


if __name__ == "__main__":
    freeze_support()
    start_fastflix()
