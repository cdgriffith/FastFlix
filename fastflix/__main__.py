# -*- coding: utf-8 -*-
import traceback
from multiprocessing import freeze_support

from fastflix.entry import main


def start_fastflix():
    freeze_support()
    try:
        main()
    except Exception:
        traceback.print_exc()
        input(
            "Error while running FastFlix!\n"
            "Plese report this issue on https://github.com/cdgriffith/FastFlix/issues (press any key to exit)"
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    start_fastflix()
