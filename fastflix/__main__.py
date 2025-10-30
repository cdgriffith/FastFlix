# -*- coding: utf-8 -*-
import os
import sys
import traceback
from multiprocessing import freeze_support
from pathlib import Path

from fastflix.entry import main


def patch_pgsrip_for_pyinstaller():
    """Monkey-patch pgsrip to fix temp folder creation in PyInstaller.

    pgsrip's MediaPath.create_temp_folder() doesn't work correctly in frozen
    PyInstaller executables, so we patch MkvPgs.read_data to handle it.
    """
    try:
        import tempfile
        from subprocess import check_output

        # Import pgsrip.mkv module to patch it
        from pgsrip import mkv as pgsrip_mkv

        @classmethod
        def patched_read_data(cls, media_path, track_id, temp_folder):
            """Patched version that ensures temp_folder exists as a directory"""
            # Check if temp_folder exists as a directory
            temp_folder_path = Path(temp_folder)
            if not temp_folder_path.exists() or not temp_folder_path.is_dir():
                # Create our own temp folder if pgsrip's creation failed
                temp_folder = tempfile.mkdtemp(prefix=f"{Path(str(media_path)).stem}_", suffix=".pgsrip")

            lang_ext = f".{str(media_path.language)}" if media_path.language else ""
            sup_file = os.path.join(temp_folder, f"{track_id}{lang_ext}.sup")
            cmd = ["mkvextract", str(media_path), "tracks", f"{track_id}:{sup_file}"]
            check_output(cmd)
            with open(sup_file, mode="rb") as f:
                return f.read()

        # Apply the monkey-patch
        pgsrip_mkv.MkvPgs.read_data = patched_read_data
    except ImportError:
        # pgsrip not installed, skip patching
        pass


def setup_ocr_environment():
    """Set up environment variables for OCR tools early in app startup.

    This is necessary for PyInstaller frozen executables where os.environ
    modifications later in the code don't properly propagate to subprocesses.
    """
    import tempfile
    from fastflix.models.config import find_ocr_tool

    # Ensure TEMP/TMP point to standard locations for PyInstaller compatibility
    # pgsrip creates temp folders and needs writable temp directory
    temp_dir = tempfile.gettempdir()
    os.environ["TEMP"] = temp_dir
    os.environ["TMP"] = temp_dir

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

    # Patch pgsrip AFTER environment is set up
    patch_pgsrip_for_pyinstaller()


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
