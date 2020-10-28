# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import pkg_resources
import time

from qtpy import QtWidgets, QtGui, QtCore


def create_app():
    main_app = QtWidgets.QApplication(sys.argv)
    main_app.setStyle("fusion")
    main_app.setApplicationDisplayName("FastFlix")
    my_font = QtGui.QFont("helvetica", 9, weight=57)
    main_app.setFont(my_font)
    main_icon = str(Path(pkg_resources.resource_filename(__name__, "data/icon.ico")).resolve())
    main_app.setWindowIcon(QtGui.QIcon(main_icon))
    return main_app


class Worker(QtCore.QObject):
    finished = QtCore.Signal(int)
    status_signal = QtCore.Signal(str)

    def __init__(self, parent, app, tasks, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.tasks = tasks

    @QtCore.Slot()
    def run_tasks(self):
        ratio = 100 // len(self.tasks)
        for i, task in enumerate(self.tasks, start=1):
            time.sleep(0.5)
            self.status_signal.emit(str(i * ratio) + "|||" + str(task))

        self.finished.emit()


class ProgressBar(QtWidgets.QWidget):
    def __init__(self, app, tasks):
        super().__init__()
        self.status = QtWidgets.QLabel()
        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setGeometry(30, 40, 500, 75)
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.status, alignment=QtCore.Qt.AlignCenter)
        self.layout.addWidget(self.progress_bar)
        self.setLayout(self.layout)
        self.setWindowFlags(QtCore.Qt.SplashScreen | QtCore.Qt.FramelessWindowHint)
        # self.setGeometry(300, 300, 550, 100)

        self.obj = Worker(self, app, tasks)
        self.thread = QtCore.QThread()
        self.thread.started.connect(self.obj.run_tasks)
        self.obj.status_signal.connect(self.status_update)
        self.obj.moveToThread(self.thread)
        self.obj.finished.connect(self.thread.quit)
        self.obj.finished.connect(self.close)  # To hide the progress bar after the progress is completed

    def start_progress(self):  # To restart the progress every time
        self.show()
        self.thread.start()

    def status_update(self, status):
        percentage, label = status.split("|||")  # May raise value error
        self.status.setText(label)
        self.progress_bar.setValue(int(percentage))


if __name__ == "__main__":
    app = create_app()
    popup = ProgressBar(app, [1, 2, 3, 4, 5])
    popup.start_progress()
    # a = QtWidgets.QSplashScreen(QtGui.QPixmap(str(Path(pkg_resources.resource_filename(__name__, "data/splash_screens/loading.png")).resolve())))
    # a.show()
    # app.processEvents()
    #
    # import time
    # time.sleep(5)

    sys.exit(app.exec_())


# def start_app(queue, status_queue, log_queue, data_path, log_dir):
#     logger = logging.getLogger("fastflix")
#     coloredlogs.install(level="DEBUG", logger=logger)
#
#     logger.debug(f"Using qt engine {API} version {QT_VERSION}")
#
#     try:
#
#
#         flix, work_dir, config_file = required_info(logger, data_path, log_dir)
#         window = Container(
#             flix=flix,
#             source=sys.argv[1] if len(sys.argv) > 1 else "",
#             data_path=data_path,
#             work_path=work_dir,
#             config_file=config_file,
#             worker_queue=queue,
#             status_queue=status_queue,
#             log_queue=log_queue,
#             main_app=main_app,
#         )
#         main_app.setWindowIcon(window.icon)
#         window.show()
#         main_app.exec_()
#     except (Exception, BaseException, SystemError, SystemExit) as err:
#         logger.exception(f"HARD FAIL: Unexpected error: {err}")
#         print(f"Unexpected error: {err}")
#     else:
#         logger.info("Fastflix shutting down")
