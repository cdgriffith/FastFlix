import sys
import logging
from pathlib import Path

from appdirs import user_data_dir

from flix.version import __version__
from flix.flix import ff_version, FlixError
from flix.shared import QtWidgets, error_message
from flix.widgets.container import Container

logger = logging.getLogger('flix')


def main():
    logging.basicConfig(level=logging.DEBUG)

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

    window = Container(ffmpeg=ffmpeg, ffprobe=ffprobe,
                       ffmpeg_version=ffmpeg_version, ffprobe_version=ffprobe_version,
                       svt_av1=svt_av1,
                       source=sys.argv[1] if len(sys.argv) > 1 else "",
                       data_path=data_path)

    window.show()
    sys.exit(main_app.exec_())


def first_time_setup(ffmpeg_folder, svt_av1_folder, data_path):
    import subprocess
    logger.info("Performing first time setup")
    subprocess.run(f'{Path("extra", "7za.exe")} e {Path("extra", "ffmpeg_lgpl.7z")} -o"{ffmpeg_folder}" -y',
                   stdout=subprocess.PIPE, shell=True).check_returncode()
    subprocess.run(f'{Path("extra", "7za.exe")} x {Path("extra", "plugins.7z")} -o"{data_path}" -y',
                   stdout=subprocess.PIPE, shell=True).check_returncode()
    subprocess.run(f'{Path("extra", "7za.exe")} e {Path("extra", "svt-*.7z")} -o"{svt_av1_folder}" -y',
                   stdout=subprocess.PIPE, shell=True).check_returncode()


if __name__ == '__main__':
    main()
