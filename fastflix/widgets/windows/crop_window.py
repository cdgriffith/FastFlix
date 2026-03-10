# -*- coding: utf-8 -*-
import logging
import secrets
from pathlib import Path
from subprocess import run, PIPE
from typing import Optional, TYPE_CHECKING

from PySide6 import QtWidgets, QtCore, QtGui

from fastflix.encoders.common import helpers
from fastflix.flix import generate_thumbnail_command
from fastflix.language import t
from fastflix.shared import time_to_number
from fastflix.ui_scale import scaler

if TYPE_CHECKING:
    from fastflix.widgets.main import Main

__all__ = ["CropPreviewWindow"]

logger = logging.getLogger("fastflix")


class CropImageWidget(QtWidgets.QWidget):
    """Interactive widget that displays a video frame and allows dragging crop edges."""

    EDGE_TOLERANCE = 8  # pixels for edge hit detection
    MIN_CROP_SIZE = 64  # minimum crop area in video pixels

    def __init__(self, parent: "CropPreviewWindow"):
        super().__init__(parent)
        self.crop_window = parent
        self.setMouseTracking(True)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # Display state
        self.display_rect = QtCore.QRect()  # where the image is drawn in widget coords
        self.frame_pixmap: Optional[QtGui.QPixmap] = None
        self.preview_pixmap: Optional[QtGui.QPixmap] = None

        # Drag state - list of active edges (e.g. ["top", "left"] for corner drag)
        self._dragging_edges: list[str] = []

    def set_frame(self, pixmap: QtGui.QPixmap):
        self.frame_pixmap = pixmap
        self.update()

    def set_preview(self, pixmap: QtGui.QPixmap):
        self.preview_pixmap = pixmap
        self.update()

    def _compute_display_rect(self, pixmap: QtGui.QPixmap) -> QtCore.QRect:
        """Compute the rectangle where the pixmap should be drawn, centered and aspect-ratio preserved."""
        if pixmap.isNull():
            return QtCore.QRect()
        pw, ph = pixmap.width(), pixmap.height()
        ww, wh = self.width(), self.height()
        scale = min(ww / pw, wh / ph)
        dw = int(pw * scale)
        dh = int(ph * scale)
        dx = (ww - dw) // 2
        dy = (wh - dh) // 2
        return QtCore.QRect(dx, dy, dw, dh)

    def _video_to_widget(self, vx: float, vy: float) -> QtCore.QPoint:
        """Convert video pixel coordinates to widget coordinates."""
        if not self.frame_pixmap or self.frame_pixmap.isNull() or self.display_rect.isEmpty():
            return QtCore.QPoint(0, 0)
        sx = self.display_rect.width() / self.frame_pixmap.width()
        sy = self.display_rect.height() / self.frame_pixmap.height()
        return QtCore.QPoint(
            int(self.display_rect.x() + vx * sx),
            int(self.display_rect.y() + vy * sy),
        )

    def _widget_to_video(self, wx: int, wy: int) -> tuple[int, int]:
        """Convert widget coordinates to video pixel coordinates, clamped to bounds."""
        if not self.frame_pixmap or self.frame_pixmap.isNull() or self.display_rect.isEmpty():
            return 0, 0
        sx = self.frame_pixmap.width() / self.display_rect.width()
        sy = self.frame_pixmap.height() / self.display_rect.height()
        vx = int((wx - self.display_rect.x()) * sx)
        vy = int((wy - self.display_rect.y()) * sy)
        vx = max(0, min(vx, self.frame_pixmap.width()))
        vy = max(0, min(vy, self.frame_pixmap.height()))
        return vx, vy

    def _edges_at_pos(self, pos: QtCore.QPoint) -> list[str]:
        """Return which crop edges are near the given widget position (can be 2 for corners)."""
        if not self.frame_pixmap or self.frame_pixmap.isNull():
            return []
        crop = self.crop_window.crop_values
        video_w = self.crop_window.video_width
        video_h = self.crop_window.video_height

        # Crop edges in video coordinates
        left_v = crop["left"]
        right_v = video_w - crop["right"]
        top_v = crop["top"]
        bottom_v = video_h - crop["bottom"]

        # Convert to widget coordinates
        left_w = self._video_to_widget(left_v, 0).x()
        right_w = self._video_to_widget(right_v, 0).x()
        top_w = self._video_to_widget(0, top_v).y()
        bottom_w = self._video_to_widget(0, bottom_v).y()

        tol = self.EDGE_TOLERANCE
        px, py = pos.x(), pos.y()

        edges = []
        near_left = abs(px - left_w) <= tol
        near_right = abs(px - right_w) <= tol
        near_top = abs(py - top_w) <= tol
        near_bottom = abs(py - bottom_w) <= tol

        # Vertical edges need cursor within vertical range (with tolerance)
        in_v_range = top_w - tol <= py <= bottom_w + tol
        # Horizontal edges need cursor within horizontal range (with tolerance)
        in_h_range = left_w - tol <= px <= right_w + tol

        if near_top and in_h_range:
            edges.append("top")
        if near_bottom and in_h_range:
            edges.append("bottom")
        if near_left and in_v_range:
            edges.append("left")
        if near_right and in_v_range:
            edges.append("right")
        return edges

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        if self.crop_window.mode == "preview" and self.preview_pixmap and not self.preview_pixmap.isNull():
            rect = self._compute_display_rect(self.preview_pixmap)
            painter.drawPixmap(rect, self.preview_pixmap)
            self.display_rect = self._compute_display_rect(self.frame_pixmap) if self.frame_pixmap else rect
            painter.end()
            return

        if not self.frame_pixmap or self.frame_pixmap.isNull():
            painter.end()
            return

        self.display_rect = self._compute_display_rect(self.frame_pixmap)
        painter.drawPixmap(self.display_rect, self.frame_pixmap)

        # Draw crop overlay
        crop = self.crop_window.crop_values
        video_w = self.crop_window.video_width
        video_h = self.crop_window.video_height

        tl = self._video_to_widget(crop["left"], crop["top"])
        br = self._video_to_widget(video_w - crop["right"], video_h - crop["bottom"])
        crop_rect = QtCore.QRect(tl, br)

        # Semi-transparent overlay outside crop area
        overlay_color = QtGui.QColor(0, 0, 0, 140)
        dr = self.display_rect

        # Top strip
        painter.fillRect(QtCore.QRect(dr.left(), dr.top(), dr.width(), tl.y() - dr.top()), overlay_color)
        # Bottom strip
        painter.fillRect(QtCore.QRect(dr.left(), br.y(), dr.width(), dr.bottom() - br.y() + 1), overlay_color)
        # Left strip (between top and bottom)
        painter.fillRect(QtCore.QRect(dr.left(), tl.y(), tl.x() - dr.left(), br.y() - tl.y()), overlay_color)
        # Right strip (between top and bottom)
        painter.fillRect(QtCore.QRect(br.x(), tl.y(), dr.right() - br.x() + 1, br.y() - tl.y()), overlay_color)

        # Crop border
        pen = QtGui.QPen(QtGui.QColor(0, 180, 255), 2)
        painter.setPen(pen)
        painter.drawRect(crop_rect)

        # Drag handles at edge midpoints
        handle_size = 8
        handle_color = QtGui.QColor(0, 180, 255)
        painter.setBrush(handle_color)
        painter.setPen(QtCore.Qt.NoPen)
        mid_y = (tl.y() + br.y()) // 2
        mid_x = (tl.x() + br.x()) // 2

        # Edge midpoint handles
        painter.drawRect(tl.x() - handle_size // 2, mid_y - handle_size // 2, handle_size, handle_size)
        painter.drawRect(br.x() - handle_size // 2, mid_y - handle_size // 2, handle_size, handle_size)
        painter.drawRect(mid_x - handle_size // 2, tl.y() - handle_size // 2, handle_size, handle_size)
        painter.drawRect(mid_x - handle_size // 2, br.y() - handle_size // 2, handle_size, handle_size)
        # Corner handles
        painter.drawRect(tl.x() - handle_size // 2, tl.y() - handle_size // 2, handle_size, handle_size)
        painter.drawRect(br.x() - handle_size // 2, tl.y() - handle_size // 2, handle_size, handle_size)
        painter.drawRect(tl.x() - handle_size // 2, br.y() - handle_size // 2, handle_size, handle_size)
        painter.drawRect(br.x() - handle_size // 2, br.y() - handle_size // 2, handle_size, handle_size)

        painter.end()

    @staticmethod
    def _cursor_for_edges(edges: list[str]) -> QtCore.Qt.CursorShape:
        s = set(edges)
        if s in ({"top", "left"}, {"bottom", "right"}):
            return QtCore.Qt.SizeFDiagCursor
        if s in ({"top", "right"}, {"bottom", "left"}):
            return QtCore.Qt.SizeBDiagCursor
        if s & {"left", "right"}:
            return QtCore.Qt.SizeHorCursor
        if s & {"top", "bottom"}:
            return QtCore.Qt.SizeVerCursor
        return QtCore.Qt.ArrowCursor

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.crop_window.mode == "crop":
            edges = self._edges_at_pos(event.pos())
            if edges:
                self._dragging_edges = edges
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.crop_window.mode != "crop":
            return super().mouseMoveEvent(event)

        if self._dragging_edges:
            vx, vy = self._widget_to_video(event.pos().x(), event.pos().y())
            crop = self.crop_window.crop_values
            video_w = self.crop_window.video_width
            video_h = self.crop_window.video_height

            if "left" in self._dragging_edges:
                max_val = video_w - crop["right"] - self.MIN_CROP_SIZE
                crop["left"] = max(0, min(vx, max_val))
            if "right" in self._dragging_edges:
                max_val = video_w - crop["left"] - self.MIN_CROP_SIZE
                crop["right"] = max(0, min(video_w - vx, max_val))
            if "top" in self._dragging_edges:
                max_val = video_h - crop["bottom"] - self.MIN_CROP_SIZE
                crop["top"] = max(0, min(vy, max_val))
            if "bottom" in self._dragging_edges:
                max_val = video_h - crop["top"] - self.MIN_CROP_SIZE
                crop["bottom"] = max(0, min(video_h - vy, max_val))

            self.crop_window.update_size_label()
            self.update()
        else:
            # Update cursor based on edge proximity
            edges = self._edges_at_pos(event.pos())
            self.setCursor(self._cursor_for_edges(edges))

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._dragging_edges = []
        super().mouseReleaseEvent(event)


class TimelineWidget(QtWidgets.QWidget):
    """Custom widget that overlays start/end time markers on top of the slider area."""

    def __init__(self, qt_parent: QtWidgets.QWidget, crop_window: "CropPreviewWindow"):
        super().__init__(qt_parent)
        self.crop_window = crop_window
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        slider = self.crop_window.slider
        video = self.crop_window.main.app.fastflix.current_video
        if not video or video.duration <= 0:
            painter.end()
            return

        # Get slider geometry relative to this widget's parent (they share the same parent)
        slider_geo = slider.geometry()
        # The groove is inset from the slider widget edges by handle half-width
        handle_w = 12  # matches stylesheet
        groove_left = slider_geo.x() + handle_w // 2
        groove_right = slider_geo.x() + slider_geo.width() - handle_w // 2
        groove_width = groove_right - groove_left

        duration = video.duration
        marker_h = self.height()

        # Draw start time marker
        if self.crop_window.start_time is not None and self.crop_window.start_time > 0:
            frac = self.crop_window.start_time / duration
            x = int(groove_left + frac * groove_width)
            pen = QtGui.QPen(QtGui.QColor(0, 200, 80), 2)
            painter.setPen(pen)
            painter.drawLine(x, 0, x, marker_h)
            # Small label
            painter.setFont(QtGui.QFont("sans-serif", 7))
            painter.drawText(x + 3, 10, "S")

        # Draw end time marker
        if self.crop_window.end_time is not None and self.crop_window.end_time < duration:
            frac = self.crop_window.end_time / duration
            x = int(groove_left + frac * groove_width)
            pen = QtGui.QPen(QtGui.QColor(200, 60, 60), 2)
            painter.setPen(pen)
            painter.drawLine(x, 0, x, marker_h)
            painter.setFont(QtGui.QFont("sans-serif", 7))
            painter.drawText(x + 3, 10, "E")

        painter.end()


class CropPreviewWindow(QtWidgets.QWidget):
    """Window for visually setting crop values by dragging edges on a video frame."""

    def __init__(self, parent: "Main"):
        super().__init__()
        self.main = parent
        self.mode = "crop"  # "crop" or "preview"
        self.crop_values = {"top": 0, "bottom": 0, "left": 0, "right": 0}
        self.video_width = 0
        self.video_height = 0
        self.rotate = 0  # 0-3 matching main UI (0=0°, 1=90°CW, 2=180°, 3=270°CW)
        self.vertical_flip = False
        self.horizontal_flip = False
        self.start_time: Optional[float] = None  # None means not set by user in this window
        self.end_time: Optional[float] = None
        self.last_path: Optional[Path] = None

        self.setWindowTitle(t("Visual Crop"))
        self.setMinimumSize(600, 400)
        # Default size: ~90% of the 1200x680 reference resolution
        self.resize(scaler.scale(1080), scaler.scale(612))
        screen = self.main.app.primaryScreen()
        if screen:
            size = screen.size()
            self.setMaximumWidth(size.width())
            self.setMaximumHeight(size.height())

        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top bar
        top_bar = QtWidgets.QWidget()
        top_bar.setFixedHeight(scaler.scale(40))
        top_bar.setStyleSheet("background-color: #2d3136;")
        top_layout = QtWidgets.QHBoxLayout(top_bar)
        top_layout.setContentsMargins(scaler.scale(10), 0, scaler.scale(10), 0)

        self.reset_btn = QtWidgets.QPushButton()
        self.reset_btn.setFixedSize(scaler.scale(28), scaler.scale(28))
        self.reset_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_BrowserReload))
        self.reset_btn.setToolTip(t("Reset"))
        self.reset_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.reset_btn.clicked.connect(self.reset_crop)

        self.crop_btn = QtWidgets.QPushButton(t("Crop"))
        self.preview_btn = QtWidgets.QPushButton(t("Preview"))
        for btn in (self.crop_btn, self.preview_btn):
            btn.setFixedHeight(scaler.scale(28))
            btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.crop_btn.clicked.connect(lambda: self.switch_mode("crop"))
        self.preview_btn.clicked.connect(lambda: self.switch_mode("preview"))

        self.rotate_btn = QtWidgets.QPushButton("0\u00b0")
        self.rotate_btn.setFixedHeight(scaler.scale(28))
        self.rotate_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.rotate_btn.setToolTip(t("Rotate 90\u00b0 clockwise"))
        self.rotate_btn.clicked.connect(self._cycle_rotate)

        self.hflip_btn = QtWidgets.QPushButton(t("H Flip"))
        self.hflip_btn.setFixedHeight(scaler.scale(28))
        self.hflip_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.hflip_btn.setToolTip(t("Toggle horizontal flip"))
        self.hflip_btn.clicked.connect(self._toggle_hflip)

        self.vflip_btn = QtWidgets.QPushButton(t("V Flip"))
        self.vflip_btn.setFixedHeight(scaler.scale(28))
        self.vflip_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.vflip_btn.setToolTip(t("Toggle vertical flip"))
        self.vflip_btn.clicked.connect(self._toggle_vflip)

        self.set_start_btn = QtWidgets.QPushButton(t("Set Start Time"))
        self.set_start_btn.setFixedHeight(scaler.scale(28))
        self.set_start_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.set_start_btn.clicked.connect(self.set_start_time)

        self.set_end_btn = QtWidgets.QPushButton(t("Set End Time"))
        self.set_end_btn.setFixedHeight(scaler.scale(28))
        self.set_end_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.set_end_btn.clicked.connect(self.set_end_time)

        self.size_label = QtWidgets.QLabel("")
        self.size_label.setStyleSheet("color: #b5b5b5;")
        self.size_label.setAlignment(QtCore.Qt.AlignCenter)

        self.save_btn = QtWidgets.QPushButton(t("Save"))
        self.save_btn.setFixedHeight(scaler.scale(28))
        self.save_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self.save_crop)

        self.close_btn = QtWidgets.QPushButton(t("Close"))
        self.close_btn.setFixedHeight(scaler.scale(28))
        self.close_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.close_btn.clicked.connect(self.hide)

        top_layout.addWidget(self.reset_btn)
        top_layout.addWidget(self.crop_btn)
        top_layout.addWidget(self.preview_btn)
        top_layout.addWidget(self.rotate_btn)
        top_layout.addWidget(self.hflip_btn)
        top_layout.addWidget(self.vflip_btn)
        top_layout.addWidget(self.set_start_btn)
        top_layout.addWidget(self.set_end_btn)
        top_layout.addStretch(1)
        top_layout.addWidget(self.size_label)
        top_layout.addStretch(1)
        top_layout.addWidget(self.save_btn)
        top_layout.addWidget(self.close_btn)

        self._update_button_styles()

        layout.addWidget(top_bar)

        # Image widget
        self.image_widget = CropImageWidget(self)
        self.image_widget.setStyleSheet("background-color: #1a1d21;")
        layout.addWidget(self.image_widget, 1)

        # Bottom bar with slider
        bottom_bar = QtWidgets.QWidget()
        bottom_bar.setFixedHeight(scaler.scale(36))
        bottom_bar.setStyleSheet("background-color: #2d3136;")
        bottom_layout = QtWidgets.QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(scaler.scale(10), scaler.scale(4), scaler.scale(10), scaler.scale(4))

        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setMinimum(1)
        self.slider.setMaximum(100)
        self.slider.sliderReleased.connect(self.slider_changed)
        self.slider.valueChanged.connect(self._update_time_label)
        self.slider.installEventFilter(self)
        self.slider.setStyleSheet("""
            QSlider { background: transparent; }
            QSlider::groove:horizontal {
                background: rgba(255, 255, 255, 40);
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: rgba(255, 255, 255, 255);
                width: 12px;
                height: 16px;
                margin: -5px 0;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal { background: transparent; }
        """)

        self.time_label = QtWidgets.QLabel("0:00:00")
        self.time_label.setStyleSheet("color: white; font-weight: bold;")
        self.time_label.setFixedWidth(scaler.scale(70))
        self.time_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        bottom_layout.addWidget(self.slider)
        bottom_layout.addWidget(self.time_label)

        layout.addWidget(bottom_bar)

        # Timeline markers overlay (painted on top of the bottom bar)
        self.timeline_overlay = TimelineWidget(bottom_bar, self)
        self.timeline_overlay.setGeometry(bottom_bar.rect())
        self.timeline_overlay.raise_()

    def _update_button_styles(self):
        active = (
            "QPushButton { background: #567781; color: white; border: none; border-radius: 4px; padding: 4px 12px; }"
        )
        inactive = (
            "QPushButton { background: #4a555e; color: #b5b5b5; border: none; border-radius: 4px; padding: 4px 12px; }"
            "QPushButton:hover { background: #566068; }"
        )
        self.crop_btn.setStyleSheet(active if self.mode == "crop" else inactive)
        self.preview_btn.setStyleSheet(active if self.mode == "preview" else inactive)

        reset_style = (
            "QPushButton { background: #4a555e; border: none; border-radius: 4px; }"
            "QPushButton:hover { background: #566068; }"
        )
        save_style = (
            "QPushButton { background: #567781; color: white; border: none; border-radius: 4px; padding: 4px 12px; }"
            "QPushButton:hover { background: #678a94; }"
        )
        close_style = (
            "QPushButton { background: #4a555e; color: #b5b5b5; border: none; border-radius: 4px; padding: 4px 12px; }"
            "QPushButton:hover { background: #566068; }"
        )
        start_active = self.start_time is not None and self.start_time > 0
        end_active = (
            self.end_time is not None
            and self.main.app.fastflix.current_video
            and self.end_time < self.main.app.fastflix.current_video.duration
        )
        start_style = (
            "QPushButton { background: #2a6640; color: #80ff80; border: none; border-radius: 4px; padding: 4px 12px; }"
            if start_active
            else inactive
        )
        end_style = (
            "QPushButton { background: #662a2a; color: #ff8080; border: none; border-radius: 4px; padding: 4px 12px; }"
            if end_active
            else inactive
        )
        self.reset_btn.setStyleSheet(reset_style)
        self.set_start_btn.setStyleSheet(start_style)
        self.set_end_btn.setStyleSheet(end_style)
        self.save_btn.setStyleSheet(save_style)
        self.close_btn.setStyleSheet(close_style)
        self._update_transform_button_styles()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "timeline_overlay"):
            self.timeline_overlay.setGeometry(self.timeline_overlay.parentWidget().rect())
            self.timeline_overlay.update()

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() == QtCore.Qt.Key_Q:
            self.hide()
        elif event.key() == QtCore.Qt.Key_Escape:
            self.hide()
        super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        if obj == self.slider:
            if event.type() == QtCore.QEvent.KeyRelease and event.key() in (
                QtCore.Qt.Key_Left,
                QtCore.Qt.Key_Right,
                QtCore.Qt.Key_Up,
                QtCore.Qt.Key_Down,
                QtCore.Qt.Key_PageUp,
                QtCore.Qt.Key_PageDown,
            ):
                if not event.isAutoRepeat():
                    self.slider_changed()
        return super().eventFilter(obj, event)

    def open_window(self):
        """Initialize from current main window values and generate frame."""
        video = self.main.app.fastflix.current_video
        if not video:
            return

        # Read rotation/flip from main UI
        self.rotate = self.main.widgets.rotate.currentIndex()
        self.vertical_flip, self.horizontal_flip = self.main.get_flips()

        # Compute post-rotation dimensions (swap width/height for 90°/270°)
        if self.rotate in (1, 3):
            self.video_width = video.height
            self.video_height = video.width
        else:
            self.video_width = video.width
            self.video_height = video.height

        # Read current crop values from main UI (unrotated space)
        try:
            unrotated_crop = {
                "top": int(self.main.widgets.crop.top.text() or 0),
                "bottom": int(self.main.widgets.crop.bottom.text() or 0),
                "left": int(self.main.widgets.crop.left.text() or 0),
                "right": int(self.main.widgets.crop.right.text() or 0),
            }
        except (ValueError, AttributeError):
            unrotated_crop = {"top": 0, "bottom": 0, "left": 0, "right": 0}

        # Transform crop from unrotated (main UI / FFmpeg) to rotated (display) space
        self.crop_values = self._unrotated_to_rotated_crop(
            unrotated_crop, self.rotate, self.vertical_flip, self.horizontal_flip
        )

        # Read current start/end times from main UI
        self.start_time = time_to_number(self.main.widgets.start_time.text())
        self.end_time = time_to_number(self.main.widgets.end_time.text())

        # Sync slider range and position with main window slider
        main_slider = self.main.widgets.thumb_time
        self.slider.setMaximum(main_slider.maximum())
        self.slider.setPageStep(main_slider.pageStep())
        self.slider.setValue(main_slider.value())

        self.mode = "crop"
        self._update_button_styles()
        self.update_size_label()
        self.generate_image()

    def update_size_label(self):
        """Update the label showing original -> cropped dimensions."""
        crop = self.crop_values
        cw = self.video_width - crop["left"] - crop["right"]
        ch = self.video_height - crop["top"] - crop["bottom"]
        self.size_label.setText(f"{self.video_width}x{self.video_height}  →  {cw}x{ch}")

    def _get_preview_time(self) -> float:
        """Calculate time position from slider, same formula as Main.preview_place."""
        video = self.main.app.fastflix.current_video
        if not video:
            return 0
        ticks = video.duration / self.slider.maximum()
        return (self.slider.value() - 1) * ticks

    def _update_time_label(self):
        seconds = self._get_preview_time()
        self.time_label.setText(self.main.format_preview_time(seconds))
        if hasattr(self, "timeline_overlay"):
            self.timeline_overlay.update()

    def set_start_time(self):
        """Set start time from current slider position."""
        time = self._get_preview_time()
        if self.end_time is not None and time >= self.end_time:
            return
        self.start_time = time
        self._update_button_styles()
        self.timeline_overlay.update()

    def set_end_time(self):
        """Set end time from current slider position."""
        time = self._get_preview_time()
        if self.start_time is not None and time <= self.start_time:
            return
        self.end_time = time
        self._update_button_styles()
        self.timeline_overlay.update()

    def generate_image(self, with_crop=False):
        """Generate a video frame, optionally with crop applied."""
        video = self.main.app.fastflix.current_video
        if not video or not video.video_settings.video_encoder_settings:
            return

        settings = video.video_settings.model_dump()

        if video.video_settings.video_encoder_settings.pix_fmt == "yuv420p10le" and video.color_space.startswith(
            "bt2020"
        ):
            settings["remove_hdr"] = True
            if not settings.get("color_transfer"):
                settings["color_transfer"] = video.color_transfer

        if with_crop:
            # Transform rotated crop values to unrotated space for FFmpeg
            # (FFmpeg filter order: crop → scale → rotate → flip)
            unrotated_crop = self._rotated_to_unrotated_crop(
                self.crop_values, self.rotate, self.vertical_flip, self.horizontal_flip
            )
            cw = video.width - unrotated_crop["left"] - unrotated_crop["right"]
            ch = video.height - unrotated_crop["top"] - unrotated_crop["bottom"]
            settings["crop"] = {"width": cw, "height": ch, "left": unrotated_crop["left"], "top": unrotated_crop["top"]}
        else:
            # No crop for the base frame
            settings["crop"] = None

        # Don't apply scale for the crop window - we want full resolution frame
        settings["scale"] = None

        # Apply rotation/flip so the preview matches the final output
        settings["rotate"] = self.rotate
        settings["vertical_flip"] = self.vertical_flip
        settings["horizontal_flip"] = self.horizontal_flip

        filters = helpers.generate_filters(
            enable_opencl=False,
            start_filters="select=eq(pict_type\\,I)"
            if self.main.app.fastflix.config.use_keyframes_for_preview
            else None,
            **settings,
        )

        output = self.main.app.fastflix.config.work_path / f"crop_preview_{secrets.token_hex(16)}.tiff"

        thumb_command = generate_thumbnail_command(
            config=self.main.app.fastflix.config,
            source=self.main.source_material,
            output=output,
            filters=filters,
            start_time=self._get_preview_time(),
            input_track=video.video_settings.selected_track,
        )

        logger.info(f"Generating crop preview: {thumb_command}")

        thumb_run = run(thumb_command, shell=True, stderr=PIPE, stdout=PIPE)
        if thumb_run.returncode > 0:
            logger.warning(f"Could not generate crop preview: {thumb_run.stdout} |----| {thumb_run.stderr}")
            return

        pixmap = QtGui.QPixmap(str(output))

        if with_crop:
            self.image_widget.set_preview(pixmap)
        else:
            self.image_widget.set_frame(pixmap)

        # Clean up previous temp file
        if self.last_path:
            try:
                self.last_path.unlink(missing_ok=True)
            except OSError:
                logger.warning(f"Could not delete crop preview temp file {self.last_path}")
        self.last_path = output

    def switch_mode(self, mode: str):
        self.mode = mode
        self._update_button_styles()
        if mode == "preview":
            self.generate_image(with_crop=True)
        self.image_widget.update()

    def slider_changed(self):
        self.generate_image(with_crop=False)
        if self.mode == "preview":
            self.generate_image(with_crop=True)

    def reset_crop(self):
        """Reset all crop values to zero and clear start/end times."""
        self.crop_values = {"top": 0, "bottom": 0, "left": 0, "right": 0}
        self.start_time = 0
        video = self.main.app.fastflix.current_video
        if video:
            self.end_time = video.duration
        self.update_size_label()
        self._update_button_styles()
        self.timeline_overlay.update()
        if self.mode == "preview":
            self.generate_image(with_crop=True)
        self.image_widget.update()

    def save_crop(self):
        """Snap crop to divisible-by-8 dimensions and write back to main UI."""
        video = self.main.app.fastflix.current_video
        if not video:
            return

        # Transform rotated crop to unrotated space for FFmpeg
        crop = self._rotated_to_unrotated_crop(self.crop_values, self.rotate, self.vertical_flip, self.horizontal_flip)

        # Snap to divisible-by-8 in unrotated space
        w = video.width - crop["left"] - crop["right"]
        h = video.height - crop["top"] - crop["bottom"]

        target_w = (w // 8) * 8
        target_h = (h // 8) * 8

        w_diff = w - target_w
        h_diff = h - target_h

        # Distribute remainder evenly across both edges
        crop["left"] += w_diff // 2
        crop["right"] += w_diff - w_diff // 2
        crop["top"] += h_diff // 2
        crop["bottom"] += h_diff - h_diff // 2

        # Write unrotated crop to main UI
        self.main.widgets.crop.top.setText(str(crop["top"]))
        self.main.widgets.crop.bottom.setText(str(crop["bottom"]))
        self.main.widgets.crop.left.setText(str(crop["left"]))
        self.main.widgets.crop.right.setText(str(crop["right"]))

        # Write rotation/flip back to main UI
        self.main.widgets.rotate.setCurrentIndex(self.rotate)
        self.main.widgets.flip.setCurrentIndex(self.main.flip_to_int(self.vertical_flip, self.horizontal_flip))

        # Write start/end times back to main UI
        if self.start_time is not None:
            self.main.widgets.start_time.setText(self.main.number_to_time(self.start_time))
        if self.end_time is not None:
            self.main.widgets.end_time.setText(self.main.number_to_time(self.end_time))

        logger.info(
            f"Crop saved (unrotated): top={crop['top']} bottom={crop['bottom']} "
            f"left={crop['left']} right={crop['right']} "
            f"({video.width - crop['left'] - crop['right']}x"
            f"{video.height - crop['top'] - crop['bottom']})"
            f" | rotate={self.rotate} vflip={self.vertical_flip} hflip={self.horizontal_flip}"
        )
        self.hide()

    @staticmethod
    def _unrotated_to_rotated_crop(crop, rotate, vflip, hflip):
        """Transform crop from unrotated (FFmpeg) space to rotated (display) space.

        FFmpeg filter order: crop → scale → rotate → flip.
        Forward: apply rotation mapping, then flip.
        """
        ct, cr, cb, cl = crop["top"], crop["right"], crop["bottom"], crop["left"]
        if rotate == 1:
            ct, cr, cb, cl = cl, ct, cr, cb
        elif rotate == 2:
            ct, cr, cb, cl = cb, cl, ct, cr
        elif rotate == 3:
            ct, cr, cb, cl = cr, cb, cl, ct
        if hflip:
            cl, cr = cr, cl
        if vflip:
            ct, cb = cb, ct
        return {"top": ct, "right": cr, "bottom": cb, "left": cl}

    @staticmethod
    def _rotated_to_unrotated_crop(crop, rotate, vflip, hflip):
        """Transform crop from rotated (display) space to unrotated (FFmpeg) space.

        Inverse of _unrotated_to_rotated_crop: undo flips first, then undo rotation.
        """
        ct, cr, cb, cl = crop["top"], crop["right"], crop["bottom"], crop["left"]
        # Undo flips first
        if hflip:
            cl, cr = cr, cl
        if vflip:
            ct, cb = cb, ct
        # Undo rotation (apply inverse rotation)
        inv = (4 - rotate) % 4
        if inv == 1:
            ct, cr, cb, cl = cl, ct, cr, cb
        elif inv == 2:
            ct, cr, cb, cl = cb, cl, ct, cr
        elif inv == 3:
            ct, cr, cb, cl = cr, cb, cl, ct
        return {"top": ct, "right": cr, "bottom": cb, "left": cl}

    def _update_transform_button_styles(self):
        """Update rotate/flip button text and style to reflect current state."""
        labels = ["0\u00b0", "90\u00b0", "180\u00b0", "270\u00b0"]
        self.rotate_btn.setText(labels[self.rotate])

        active = (
            "QPushButton { background: #567781; color: white; border: none; border-radius: 4px; padding: 4px 12px; }"
        )
        inactive = (
            "QPushButton { background: #4a555e; color: #b5b5b5; border: none; border-radius: 4px; padding: 4px 12px; }"
            "QPushButton:hover { background: #566068; }"
        )
        self.rotate_btn.setStyleSheet(active if self.rotate != 0 else inactive)
        self.hflip_btn.setStyleSheet(active if self.horizontal_flip else inactive)
        self.vflip_btn.setStyleSheet(active if self.vertical_flip else inactive)

    def _cycle_rotate(self):
        """Cycle rotation 0 -> 90 -> 180 -> 270 -> 0, transforming crop accordingly."""
        old_rotate = self.rotate
        self.rotate = (self.rotate + 1) % 4

        # Transform crop: old rotated space -> unrotated -> new rotated space
        unrotated = self._rotated_to_unrotated_crop(
            self.crop_values, old_rotate, self.vertical_flip, self.horizontal_flip
        )
        self.crop_values = self._unrotated_to_rotated_crop(
            unrotated, self.rotate, self.vertical_flip, self.horizontal_flip
        )

        # Swap dimensions if transposition changed (0/2 vs 1/3)
        if (old_rotate in (1, 3)) != (self.rotate in (1, 3)):
            self.video_width, self.video_height = self.video_height, self.video_width

        self._update_button_styles()
        self.update_size_label()
        self.generate_image(with_crop=False)
        if self.mode == "preview":
            self.generate_image(with_crop=True)
        self.image_widget.update()

    def _toggle_hflip(self):
        """Toggle horizontal flip, swapping left/right crop in display space."""
        self.horizontal_flip = not self.horizontal_flip
        self.crop_values["left"], self.crop_values["right"] = self.crop_values["right"], self.crop_values["left"]

        self._update_button_styles()
        self.generate_image(with_crop=False)
        if self.mode == "preview":
            self.generate_image(with_crop=True)
        self.image_widget.update()

    def _toggle_vflip(self):
        """Toggle vertical flip, swapping top/bottom crop in display space."""
        self.vertical_flip = not self.vertical_flip
        self.crop_values["top"], self.crop_values["bottom"] = self.crop_values["bottom"], self.crop_values["top"]

        self._update_button_styles()
        self.generate_image(with_crop=False)
        if self.mode == "preview":
            self.generate_image(with_crop=True)
        self.image_widget.update()

    def hideEvent(self, event):
        # Clean up temp file on close
        if self.last_path:
            try:
                self.last_path.unlink(missing_ok=True)
            except OSError:
                pass
            self.last_path = None
        super().hideEvent(event)
