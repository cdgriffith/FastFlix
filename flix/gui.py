import sys
import os
import logging

from flix.flix import ff_version
from flix.shared import QtWidgets
from flix.widgets.main import Main

logging.getLogger('flix')


def main():
    main_app = QtWidgets.QApplication(sys.argv)
    main_app.setStyle("fusion")
    main_app.setApplicationDisplayName("FastFlix")

    ffmpeg = os.getenv("FFMPEG", 'ffmpeg')
    ffmpeg_version = ff_version(ffmpeg, throw=False)

    ffprobe = os.getenv("FFPROBE", 'ffprobe')
    ffprobe_version = ff_version(ffprobe, throw=False)

    window = Main(ffmpeg=ffmpeg, ffprobe=ffprobe, ffmpeg_version=ffmpeg_version, ffprobe_version=ffprobe_version,
                  source=sys.argv[1] if len(sys.argv) > 1 else "")
    window.setFixedWidth(622)
    window.setFixedHeight(710)
    window.show()
    sys.exit(main_app.exec_())


if __name__ == '__main__':
    main()
