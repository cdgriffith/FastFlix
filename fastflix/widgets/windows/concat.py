# -*- coding: utf-8 -*-
from pathlib import Path
import os
import logging
import secrets

from PySide6 import QtWidgets, QtGui
from PySide6.QtWidgets import QAbstractItemView

from fastflix.language import t
from fastflix.flix import probe
from fastflix.shared import yes_no_message, error_message
from fastflix.widgets.progress_bar import ProgressBar, Task

logger = logging.getLogger("fastflix")


BAD_FILES = ("Thumbs.db",)


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
        self.header_labels = ["Filename", "Resolution", "Codec", "Remove"]
        self.min_column_widths = []

        header = self.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        header.sectionResized.connect(self._on_section_resized)

        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setShowGrid(False)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDragDropOverwriteMode(False)

        # Set our custom model - this prevents row "shifting"
        self.model = MyModel()
        self.model.setHorizontalHeaderLabels(self.header_labels)

        self.setModel(self.model)
        self.buttons = []
        self._resizing = False

    def _calculate_min_widths(self):
        """Calculate minimum column widths based on header text."""
        font_metrics = self.horizontalHeader().fontMetrics()
        padding = 20  # Extra padding for header margins
        self.min_column_widths = [font_metrics.horizontalAdvance(label) + padding for label in self.header_labels]

    def _on_section_resized(self, logical_index, old_size, new_size):
        """Enforce column width constraints when a section is resized."""
        if self._resizing:
            return

        self._resizing = True
        try:
            if not self.min_column_widths:
                self._calculate_min_widths()

            header = self.horizontalHeader()
            num_cols = len(self.header_labels)
            viewport_width = self.viewport().width()

            # Enforce minimum width for the resized column
            if new_size < self.min_column_widths[logical_index]:
                header.resizeSection(logical_index, self.min_column_widths[logical_index])
                return

            # Calculate total width of all columns and ensure they fit in viewport
            total_width = sum(header.sectionSize(i) for i in range(num_cols))

            if total_width > viewport_width:
                # Column was made too wide, reduce it to fit
                excess = total_width - viewport_width
                max_allowed = new_size - excess
                if max_allowed >= self.min_column_widths[logical_index]:
                    header.resizeSection(logical_index, max_allowed)
                else:
                    # Can't shrink this column enough, revert to old size
                    header.resizeSection(logical_index, old_size)
        finally:
            self._resizing = False

    def set_column_widths(self, total_width):
        """Set column widths with Filename taking 50% of total width."""
        self._calculate_min_widths()

        filename_width = int(total_width * 0.5)
        resolution_width = int(total_width * 0.17)
        codec_width = int(total_width * 0.17)
        remove_width = int(total_width * 0.16)

        # Ensure widths are at least the minimum
        filename_width = max(filename_width, self.min_column_widths[0])
        resolution_width = max(resolution_width, self.min_column_widths[1])
        codec_width = max(codec_width, self.min_column_widths[2])
        remove_width = max(remove_width, self.min_column_widths[3])

        self.setColumnWidth(0, filename_width)
        self.setColumnWidth(1, resolution_width)
        self.setColumnWidth(2, codec_width)
        self.setColumnWidth(3, remove_width)

    def resizeEvent(self, event):
        """Adjust columns to fit when the table is resized."""
        super().resizeEvent(event)
        if self._resizing or not self.min_column_widths:
            return

        self._resizing = True
        try:
            header = self.horizontalHeader()
            num_cols = len(self.header_labels)
            viewport_width = self.viewport().width()
            total_width = sum(header.sectionSize(i) for i in range(num_cols))

            if total_width > viewport_width:
                # Columns are too wide, shrink the filename column (index 0) first
                excess = total_width - viewport_width
                current_filename_width = header.sectionSize(0)
                new_filename_width = current_filename_width - excess

                if new_filename_width >= self.min_column_widths[0]:
                    header.resizeSection(0, new_filename_width)
                else:
                    # Filename at minimum, distribute reduction across other resizable columns
                    header.resizeSection(0, self.min_column_widths[0])
                    remaining_excess = excess - (current_filename_width - self.min_column_widths[0])

                    # Shrink other columns proportionally
                    for i in range(1, num_cols):
                        current = header.sectionSize(i)
                        reduction = remaining_excess // (num_cols - 1)
                        new_width = max(current - reduction, self.min_column_widths[i])
                        header.resizeSection(i, new_width)
        finally:
            self._resizing = False

    def update_items(self, items):
        self.model.clear()
        self.model.setHorizontalHeaderLabels(self.header_labels)
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
        self.setMinimumWidth(750)
        self.setMinimumHeight(500)
        self.table = ConcatTable(None)
        self.setWidget(self.table)

    def showEvent(self, event):
        """Set initial column widths when the scroll area is first shown."""
        super().showEvent(event)
        # Only set initial widths the first time the widget is shown
        if not hasattr(self, "_initial_widths_set"):
            self._initial_widths_set = True
            self.table.set_column_widths(self.width())


class ConcatWindow(QtWidgets.QWidget):
    def __init__(self, app, main, items=None):
        super().__init__(None)
        self.app = app
        self.main = main
        self.setStyleSheet("font-size: 14px")
        self.folder_name = str(self.app.fastflix.config.source_directory) or str(Path.home())
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
        self.base_folder_label.setText(f"{t('Base Folder')}: {name}")

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

        def check_to_add(file, list_of_items, bad_items, **_):
            try:
                data = None
                details = probe(self.app, file)
                for stream in details.streams:
                    if stream.codec_type == "video":
                        data = (file.name, f"{stream.width}x{stream.height}", stream.codec_name)
                if not data:
                    raise Exception()
            except Exception:
                logger.warning(f"Skipping {file.name} as it is not a video/image file")
                bad_items.append(file.name)
            else:
                list_of_items.append(data)

        items = []
        skipped = []
        tasks = []
        file_list = sorted(Path(folder_name).glob("*"), key=lambda x: x.name)
        for file in file_list:
            if file.is_file():
                if file.name in BAD_FILES:
                    continue
                tasks.append(
                    Task(
                        f"Evaluating {file.name}",
                        command=check_to_add,
                        kwargs={"file": file, "list_of_items": items, "bad_items": skipped},
                    )
                )
            if len(tasks) > 100:
                error_message(t("There are more than 100 files, skipping pre-processing."))
                return self.save((x.name for x in file_list if x.name not in BAD_FILES))

        ProgressBar(self.app, tasks, can_cancel=True, auto_run=True)

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

    def save(self, file_list=None):
        concat_file = self.app.fastflix.config.work_path / f"concat_{secrets.token_hex(4)}.txt"
        with open(concat_file, "w") as f:
            f.write(
                "\n".join(
                    [
                        f"file '{self.folder_name}{os.sep}{item}'"
                        for item in (self.concat_area.table.get_items() if not file_list else file_list)
                    ]
                )
            )
        self.main.input_video = concat_file
        self.main.source_video_path_widget.setText(str(self.main.input_video))
        self.main.update_video_info()
        self.concat_area.table.model.clear()
        self.concat_area.table.buttons = []
        self.main.widgets.end_time.setText("0")
        self.main.widgets.start_time.setText("0")
        self.hide()
        self.main.page_update(build_thumbnail=True)
        self.main.app.fastflix.current_video.interlaced = False
        self.main.widgets.deinterlace.setChecked(False)
        # TODO present if images
        # error_message(
        #     "Make sure to manually supply the frame rate in the Advanced tab "
        #     "(usually want to set both input and output to the same thing.)",
        #     title="Set FPS in Advanced Tab",
        # )
