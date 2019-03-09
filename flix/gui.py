import sys
import os
import logging
from pathlib import Path

import reusables

from flix.flix import ff_version
from flix.shared import QtWidgets, pyinstaller, base_path, main_width
from flix.widgets.main import Main

logging.getLogger('flix')


def main():
    main_app = QtWidgets.QApplication(sys.argv)
    main_app.setStyle("fusion")
    main_app.setApplicationDisplayName("FastFlix")

    ffmpeg = 'ffmpeg'
    ffprobe = 'ffprobe'
    if pyinstaller and reusables.win_based and Path(base_path, 'bundled').exists():
        ffmpeg = Path(base_path, 'ffmpeg.exe')
        ffprobe = Path(base_path, 'ffprobe.exe')
    elif reusables.win_based:
        ffmpeg = 'ffmpeg.exe'
        ffprobe = 'ffprobe.exe'

    ffmpeg_version = ff_version(ffmpeg, throw=False)
    ffprobe_version = ff_version(ffprobe, throw=False)

    svt_av1 = os.getenv("SVT_AV1", Path(base_path, 'SvtAv1EncApp.exe') if reusables.win_based else 'SvtAv1EncApp')

    window = Main(ffmpeg=ffmpeg, ffprobe=ffprobe,
                  ffmpeg_version=ffmpeg_version, ffprobe_version=ffprobe_version,
                  svt_av1=svt_av1,
                  source=sys.argv[1] if len(sys.argv) > 1 else "")
    window.setFixedWidth(main_width)
    window.setFixedHeight(710)
    window.show()
    sys.exit(main_app.exec_())


if __name__ == '__main__':
    main()
