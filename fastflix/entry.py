# -*- coding: utf-8 -*-
import logging
import sys
import traceback
from multiprocessing import Process, Queue, freeze_support, Manager, Lock

try:
    import coloredlogs
    import reusables

    import fastflix.language  # Have to set language first thing  # noqa: F401
    from fastflix.conversion_worker import queue_worker  # noqa: F401
    from fastflix.models.config import Config  # noqa: F401
    from fastflix.models.fastflix import FastFlix  # noqa: F401
    from fastflix.version import __version__  # noqa: F401

except ImportError:
    traceback.print_exc()
    print("Could not load FastFlix properly!", file=sys.stderr)
    input("Please report this issue on https://github.com/cdgriffith/FastFlix/issues (press any key to exit)")
    sys.exit(1)


def separate_app_process(worker_queue, status_queue, log_queue, queue_list, queue_lock, portable_mode=False):
    """This prevents any QT components being imported in the main process"""
    from fastflix.models.config import Config

    settings = Config().pre_load(portable_mode=portable_mode)

    from fastflix.application import start_app

    freeze_support()
    try:
        start_app(
            worker_queue,
            status_queue,
            log_queue,
            queue_list,
            queue_lock,
            portable_mode,
            enable_scaling=settings.get("enable_scaling", True),
        )
    except Exception as err:
        print(f"Could not start GUI process - Error: {err}", file=sys.stderr)
        raise err


def startup_options():
    options = sys.argv[1:]

    if "--test" in options:
        try:
            pass
        except Exception as err:
            print(f"Error: {err}")
            return 1
        print("Success")
        return 0
    if "--version" in options:
        print(__version__)
        return 0


def main(portable_mode=False):
    if reusables.win_based:
        import platform

        try:
            windows_version_string = platform.platform().lower().split("-")[1]
            if "server" in windows_version_string:
                # Windows-2022Server-10.0.20348-SP0
                server_version = int(windows_version_string[:4])
                win_ver = 0 if server_version < 2016 else 10
            else:
                win_ver = int(windows_version_string)
        except Exception as error:
            print(f"COULD NOT DETERMINE WINDOWS VERSION FROM: {platform.platform()} - {error}")
            win_ver = 0
        if win_ver < 10:
            input(
                "You are an unsupported Windows version, and may not be able to run FastFlix properly.\n"
                "Download FastFlix 4.x versions for Windows 7/8 support [press enter to continue]"
            )

    exit_code = startup_options()
    if exit_code is not None:
        return exit_code
    logger = logging.getLogger("fastflix-core")
    logger.addHandler(reusables.get_stream_handler(level=logging.DEBUG))
    logger.setLevel(logging.DEBUG)
    level_styles = {
        "debug": {"color": "blue"},
        "info": {"color": "green"},
        "warning": {"color": "yellow", "bold": True},
        "error": {"color": "red", "bold": True},
    }
    coloredlogs.install(level="DEBUG", logger=logger, level_styles=level_styles)
    logger.info(f"Starting FastFlix {__version__}")

    worker_queue = Queue()
    status_queue = Queue()
    log_queue = Queue()

    queue_lock = Lock()
    with Manager() as manager:
        queue_list = manager.list()
        exit_status = 1

        try:
            logger.info("Preparing separate process for GUI - this may take a moment")
            gui_proc = Process(
                target=separate_app_process,
                args=(worker_queue, status_queue, log_queue, queue_list, queue_lock, portable_mode),
            )
            gui_proc.start()
        except Exception:
            logger.exception("Could not create GUI Process, please report this error!")
            return exit_status

        try:
            queue_worker(gui_proc, worker_queue, status_queue, log_queue)
            exit_status = 0
        except Exception:
            logger.exception("Exception occurred while running FastFlix core")
        finally:
            gui_proc.kill()
            return exit_status
