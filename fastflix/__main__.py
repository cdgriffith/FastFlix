# -*- coding: utf-8 -*-
import sys
import traceback
from multiprocessing import freeze_support

from fastflix.entry import main


def start_fastflix():
    exit_code = 2
    portable_mode = True
    try:
        from fastflix import portable
    except ImportError:
        portable_mode = False

    if portable_mode:
        print("PORTABLE MODE DETECTED: now using local config file and workspace in same directory as the executable")

    try:
        exit_code = main(portable_mode)
    except Exception:
        traceback.print_exc()
        input(
            "Error while running FastFlix!\n"
            "Plese report this issue on https://github.com/cdgriffith/FastFlix/issues (press any key to exit)"
        )
    except KeyboardInterrupt:
        pass
    finally:
        sys.exit(exit_code)


if __name__ == "__main__":
    freeze_support()
    start_fastflix()
