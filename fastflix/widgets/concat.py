# -*- coding: utf-8 -*-
from pathlib import Path
import os
import logging

from PySide6 import QtWidgets, QtGui, QtCore

from fastflix.language import t
from fastflix.flix import probe
from fastflix.shared import yes_no_message, error_message

logger = logging.getLogger("fastflix")


class MyModel(QtGui.QStandardItemModel):
    def dropMimeData(self, data, action, row, col, parent):
        """
        Always move the entire row, and don't allow column "shifting"
        """
        return super().dropMimeData(data, action, row, 0, parent)


class CloseButton(QtWidgets.QPushButton):
    def __init__(self, table, text, name):
        self.text_name = name
        self.table = table
        super(CloseButton, self).__init__(text)

    def close_item(self):
        self.table.remove_item(self.text_name)


class ConcatTable(QtWidgets.QTableView):
    def __init__(self, parent):
        super().__init__(parent)
        self.verticalHeader().hide()
        # self.horizontalHeader().hide()
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.setSelectionBehavior(self.SelectRows)
        self.setSelectionMode(self.SingleSelection)
        self.setShowGrid(False)
        self.setDragDropMode(self.InternalMove)
        self.setDragDropOverwriteMode(False)

        # Set our custom model - this prevents row "shifting"
        self.model = MyModel()
        self.model.setHorizontalHeaderLabels(["Filename", "Resolution", "Codec", "Remove"])

        self.setModel(self.model)
        self.buttons = []

    def update_items(self, items):
        self.model.clear()
        self.model.setHorizontalHeaderLabels(["Filename", "Resolution", "Codec", "Remove"])
        self.buttons = []
        for item in items:
            self.add_item(*item)

    def add_item(self, name, resolution, codec):
        filename = QtGui.QStandardItem(name)
        filename.setEditable(False)
        filename.setDropEnabled(False)

        res = QtGui.QStandardItem(resolution)
        res.setEditable(False)
        res.setDropEnabled(False)

        form = QtGui.QStandardItem(codec)
        form.setEditable(False)
        form.setDropEnabled(False)

        remove = QtGui.QStandardItem("X")
        remove.setEditable(False)
        remove.setDropEnabled(False)
        remove.option_name = name

        self.model.appendRow([filename, res, form, remove])

        x_button = CloseButton(self, "X", name)
        x_button.clicked.connect(x_button.close_item)
        self.setIndexWidget(remove.index(), x_button)
        self.buttons.append(x_button)

    def get_items(self):
        for i in range(self.model.rowCount()):
            yield self.model.index(i, 0).data()

    def remove_item(self, name):
        for i, text in enumerate(self.get_items()):
            if text == name:
                self.model.removeRow(i)
                idx = -1
                for j, item in enumerate(self.buttons):
                    if text == item.text_name:
                        idx = j
                if idx >= 0:
                    self.buttons.pop(idx)

    def dropEvent(self, QDropEvent):
        super(ConcatTable, self).dropEvent(QDropEvent)
        for i, text in enumerate(self.get_items()):
            for item in self.buttons:
                if item.text_name == text:
                    self.setIndexWidget(self.model.index(i, 3), item)


class ConcatScroll(QtWidgets.QScrollArea):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(500)
        self.table = ConcatTable(None)
        self.setWidget(self.table)


class ConcatWindow(QtWidgets.QWidget):
    def __init__(self, app, main, items=None):
        super().__init__(None)
        self.app = app
        self.main = main
        self.folder_name = str(Path.home())
        self.setWindowTitle(t("Concatenation Builder"))

        self.concat_area = ConcatScroll(self)
        self.base_folder_label = QtWidgets.QLabel()
        self.set_folder_name(self.folder_name)
        layout = QtWidgets.QVBoxLayout()
        folder_button = QtWidgets.QPushButton(t("Open Folder"))
        folder_button.clicked.connect(self.select_folder)

        # manual_layout = QtWidgets.QHBoxLayout()
        # manual_text = QtWidgets.QLineEdit()
        # manual_button = QtWidgets.QPushButton("+")
        # manual_button.clicked.connect(lambda: self.concat_area.table.add_item(manual_text.text()))
        # manual_layout.addWidget(manual_text)
        # manual_layout.addWidget(manual_button)

        save_buttom = QtWidgets.QPushButton(t("Load"))
        save_buttom.clicked.connect(self.save)

        top_bar = QtWidgets.QHBoxLayout()
        top_bar.addWidget(folder_button)
        top_bar.addStretch(1)
        top_bar.addWidget(self.base_folder_label)
        top_bar.addStretch(1)
        top_bar.addWidget(save_buttom)

        layout.addLayout(top_bar)

        layout.addWidget(self.concat_area)
        layout.addWidget(QtWidgets.QLabel(t("Drag and Drop to reorder - All items need to be same dimensions")))
        self.setLayout(layout)

    def set_folder_name(self, name):
        self.base_folder_label.setText(f'{t("Base Folder")}: {name}')

    def get_video_details(self, file):
        details = probe(self.app, file)
        for stream in details.streams:
            if stream.codec_type == "video":
                return file.name, f"{stream.width}x{stream.height}", stream.codec_name

    def select_folder(self):
        if self.concat_area.table.model.rowCount() > 0:
            if not yes_no_message(
                f"{t('There are already items in this list')},\n"
                f"{t('if you open a new directory, they will all be removed.')}\n\n"
                f"{t('Continue')}?",
                "Confirm Change Folder",
            ):
                return
        folder_name = QtWidgets.QFileDialog.getExistingDirectory(self, dir=self.folder_name)
        if not folder_name:
            return
        self.folder_name = folder_name
        self.set_folder_name(folder_name)
        items = []
        skipped = []
        for file in Path(folder_name).glob("*"):
            if file.is_file():
                try:
                    details = self.get_video_details(file)
                    if not details:
                        raise Exception()
                except Exception:
                    logger.warning(f"Skipping {file.name} as it is not a video/image file")
                    skipped.append(file.name)
                else:
                    items.append(details)
        self.concat_area.table.update_items(items)
        if skipped:
            error_message(
                "".join(
                    [
                        f"{t('The following items were excluded as they could not be identified as image or video files')}:\n",
                        "\n".join(skipped[:20]),
                        f"\n\n+ {len(skipped[20:])} {t('more')}..." if len(skipped) > 20 else "",
                    ]
                )
            )

    def save(self):
        concat_file = self.app.fastflix.config.work_path / "concat.txt"
        with open(concat_file, "w") as f:
            f.write(
                "\n".join([f"file '{self.folder_name}{os.sep}{item}'" for item in self.concat_area.table.get_items()])
            )
        self.main.input_video = concat_file
        self.main.source_video_path_widget.setText(str(self.main.input_video))
        self.main.update_video_info()
        self.concat_area.table.model.clear()
        self.concat_area.table.buttons = []
        self.hide()
        self.main.page_update(build_thumbnail=True)
