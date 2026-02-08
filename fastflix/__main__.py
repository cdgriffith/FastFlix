# -*- coding: utf-8 -*-
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


def start_fastflix():
    exit_code = 2
    portable_mode = True
    try:
        from fastflix import portable  # noqa: F401
    except ImportError:
        portable_mode = False

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
