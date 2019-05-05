import sys
import logging
from logging.handlers import SocketHandler
from pathlib import Path

from appdirs import user_data_dir

from flix.version import __version__
from flix.flix import ff_version, FlixError
from flix.shared import QtWidgets, error_message, base_path
from flix.widgets.container import Container

logger = logging.getLogger('flix')


def main():
    logging.basicConfig(level=logging.DEBUG)
    socket_handler = SocketHandler('127.0.0.1', 19996)
    logger.addHandler(socket_handler)

    main_app = QtWidgets.QApplication(sys.argv)
    main_app.setStyle("fusion")
    main_app.setApplicationDisplayName("FastFlix")

    data_path = Path(user_data_dir("FastFlix", appauthor=False, version=__version__, roaming=True))
    first_time = not data_path.exists()
    data_path.mkdir(parents=True, exist_ok=True)

    ffmpeg_folder = Path(data_path, 'ffmpeg')
    ffmpeg_folder.mkdir(parents=True, exist_ok=True)
    ffmpeg = Path(ffmpeg_folder, 'ffmpeg.exe')
    ffprobe = Path(ffmpeg_folder, 'ffprobe.exe')

    svt_av1_folder = Path(data_path, 'svt_av1')
    svt_av1_folder.mkdir(parents=True, exist_ok=True)
    svt_av1 = Path(svt_av1_folder, 'SvtAv1EncApp.exe')

    if first_time:
        first_time_setup(ffmpeg_folder, svt_av1_folder, data_path)

    if not all([x.exists() for x in (ffmpeg, ffprobe, svt_av1, Path(data_path, "plugins"))]):
        qm = QtWidgets.QMessageBox
        ret = qm.question(None, '', 'Not all required libraries found! <br> Re-extra them?', qm.Yes | qm.No)
        if ret == qm.Yes:
            first_time_setup(ffmpeg_folder, svt_av1_folder, data_path)
        else:
            sys.exit(1)

    try:
        ffmpeg_version = ff_version(ffmpeg, throw=True)
        ffprobe_version = ff_version(ffprobe, throw=True)
    except FlixError:
        error_message("ffmpeg or ffmpeg could not be executed properly!")
        sys.exit(1)

    try:
        window = Container(ffmpeg=ffmpeg, ffprobe=ffprobe,
                           ffmpeg_version=ffmpeg_version, ffprobe_version=ffprobe_version,
                           svt_av1=svt_av1,
                           source=sys.argv[1] if len(sys.argv) > 1 else "",
                           data_path=data_path)

        window.show()
    except (Exception, BaseException, SystemError, SystemExit) as err:
        print(err)
        sys.exit(1)
    sys.exit(main_app.exec_())


def first_time_setup(ffmpeg_folder, svt_av1_folder, data_path):
    import subprocess
    import re
    logger.info("Performing first time setup")
    svt_re = re.compile(r'svt-.*\.7z')

    commands = [
        subprocess.run(f'{Path(base_path, "extra", "7za.exe")} e {Path(base_path, "extra", "ffmpeg_lgpl.7z")} -o"{ffmpeg_folder}" -y',
                       stdout=subprocess.PIPE, shell=True),
        subprocess.run(f'{Path(base_path, "extra", "7za.exe")} x {Path(base_path, "extra", "plugins.7z")} -o"{data_path}" -y',
                       stdout=subprocess.PIPE, shell=True),
        subprocess.run(f'{Path(base_path, "extra", "7za.exe")} e {[x for x in Path(base_path, "extra").iterdir() if svt_re.match(str(x.name))][0]} -o"{svt_av1_folder}" -y',
                       stdout=subprocess.PIPE, shell=True)
    ]
    err = False
    for command in commands:
        if command.returncode != 0:
            print(f'"{command.args}" returned {command.returncode}: {command.stderr} - {command.stdout}')
            err = True
    if err:
        sys.exit(1)


if __name__ == '__main__':
    main()
