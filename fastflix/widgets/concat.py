# -*- coding: utf-8 -*-
from pathlib import Path
import os

from qtpy import QtWidgets, QtGui, QtCore


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
    def __init__(self, parent, items):
        super().__init__(parent)
        self.verticalHeader().hide()
        self.horizontalHeader().hide()
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.setSelectionBehavior(self.SelectRows)
        self.setSelectionMode(self.SingleSelection)
        self.setShowGrid(False)
        self.setDragDropMode(self.InternalMove)
        self.setDragDropOverwriteMode(False)

        # Set our custom model - this prevents row "shifting"
        self.model = MyModel()
        self.setModel(self.model)
        self.buttons = []

        if items:
            self.update_items(items)

    def update_items(self, items):
        self.model.clear()
        self.buttons = []
        for item in items:
            self.add_item(item.name)

    def add_item(self, name):
        item_1 = QtGui.QStandardItem(name)
        item_1.setEditable(False)
        item_1.setDropEnabled(False)

        item_2 = QtGui.QStandardItem("X")
        item_2.setEditable(False)
        item_2.setDropEnabled(False)
        item_2.option_name = name

        self.model.appendRow([item_1, item_2])

        x_button = CloseButton(self, "X", name)
        x_button.clicked.connect(x_button.close_item)
        self.setIndexWidget(item_2.index(), x_button)
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
                    self.setIndexWidget(self.model.index(i, 1), item)


class ConcatScroll(QtWidgets.QScrollArea):
    def __init__(self, parent, items=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(500)
        self.table = ConcatTable(None, items)
        self.setWidget(self.table)


class ConcatWindow(QtWidgets.QWidget):
    def __init__(self, app, main, items=None):
        super().__init__(None)
        self.app = app
        self.main = main
        self.folder_name = str(Path.home())

        self.concat_area = ConcatScroll(self)
        self.base_folder_label = QtWidgets.QLabel(self.folder_name)
        layout = QtWidgets.QVBoxLayout()
        folder_button = QtWidgets.QPushButton("Open Folder")
        folder_button.clicked.connect(self.select_folder)

        manual_layout = QtWidgets.QHBoxLayout()
        manual_text = QtWidgets.QLineEdit()
        manual_button = QtWidgets.QPushButton("+")
        manual_button.clicked.connect(lambda: self.concat_area.table.add_item(manual_text.text()))
        manual_layout.addWidget(manual_text)
        manual_layout.addWidget(manual_button)

        save_buttom = QtWidgets.QPushButton("Save")
        save_buttom.clicked.connect(self.save)

        top_bar = QtWidgets.QHBoxLayout()
        top_bar.addWidget(folder_button)
        top_bar.addStretch(1)
        top_bar.addWidget(self.base_folder_label)
        top_bar.addStretch(1)
        top_bar.addWidget(save_buttom)

        layout.addLayout(top_bar)

        layout.addWidget(self.concat_area)
        layout.addLayout(manual_layout)
        self.setLayout(layout)

    def select_folder(self):
        folder_name = QtWidgets.QFileDialog.getExistingDirectory(self, directory=self.folder_name)
        if not folder_name:
            return
        self.folder_name = folder_name
        self.base_folder_label.setText(folder_name)
        items = []
        for file in Path(folder_name).glob("*"):
            if file.is_file():
                items.append(file)
        self.concat_area.table.update_items(items)

    def save(self):
        concat_file = self.app.fastflix.config.work_path / "concat.txt"
        with open(concat_file, "w") as f:
            f.write(
                "\n".join([f'file "{self.folder_name}{os.sep}{item}"' for item in self.concat_area.table.get_items()])
            )
        self.main.input_video = concat_file
        self.main.update_video_info()
        self.concat_area.table.model.clear()
        self.concat_area.table.buttons = []
        self.hide()
        self.main.page_update(build_thumbnail=True)
