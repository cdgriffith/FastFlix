# -*- coding: utf-8 -*-
import sys
import traceback
from multiprocessing import freeze_support

from fastflix.entry import main


def start_fastflix():
    exit_code = 2
    try:
        exit_code = main()
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
