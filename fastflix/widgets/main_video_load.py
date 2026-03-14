#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import reusables
from PySide6 import QtGui, QtWidgets

from fastflix.exceptions import FastFlixInternalException, FlixError
from fastflix.flix import detect_hdr10_plus, detect_interlaced, parse, parse_hdr_details
from fastflix.language import t
from fastflix.models.video import Status, Video
from fastflix.shared import clean_file_string, error_message, yes_no_message
from fastflix.widgets.background_tasks import ExtractCovers
from fastflix.widgets.status_bar import Task

if TYPE_CHECKING:
    from fastflix.widgets.main import Main

logger = logging.getLogger("fastflix")


class VideoLoadMixin:
    """Mixin for Main: video loading, file operations, and video info display."""

    self: Main

    @reusables.log_exception("fastflix", show_traceback=False)
    def open_file(self):
        filename = QtWidgets.QFileDialog.getOpenFileName(
            self,
            caption="Open Video",
            filter="Video Files (*.mkv *.mp4 *.m4v *.mov *.avi *.divx *.webm *.mpg *.mp2 *.mpeg *.mpe *.mpv *.ogg *.m4p"
            " *.wmv *.mov *.qt *.flv *.hevc *.gif *.webp *.vob *.ogv *.ts *.mts *.m2ts *.yuv *.rm *.svi *.3gp *.3g2"
            " *.y4m *.avs *.vpy);;"
            "Concatenation Text File (*.txt *.concat);; All Files (*)",
            dir=str(
                self.app.fastflix.config.source_directory
                or (self.app.fastflix.current_video.source.parent if self.app.fastflix.current_video else Path.home())
            ),
        )
        if not filename or not filename[0]:
            return

        if self.app.fastflix.current_video:
            discard = yes_no_message(
                f"{t('There is already a video being processed')}<br>{t('Are you sure you want to discard it?')}",
                title="Discard current video",
            )
            if not discard:
                return

        self.input_video = Path(clean_file_string(filename[0]))
        if not self.input_video.exists():
            logger.error(f"Could not find the input file, does it exist at: {self.input_video}")
            return
        self.source_video_path_widget.setText(str(self.input_video))
        self.video_path_widget.setText(str(self.input_video))
        try:
            self.update_video_info()
        except Exception:
            logger.exception(f"Could not load video {self.input_video}")
            self.video_path_widget.setText("")
            self.output_video_path_widget.setText("")
            self.output_video_path_widget.setDisabled(True)
            self.widgets.output_directory.setText("")
            self.output_path_button.setDisabled(True)
            self.filename_truncation_warning.hide()
        self.page_update()

    def open_many(self, paths: list):
        if self.app.fastflix.current_video:
            discard = yes_no_message(
                f"{t('There is already a video being processed')}<br>{t('Are you sure you want to discard it?')}",
                title="Discard current video",
            )
            if not discard:
                return

        def open_em(signal, stop_signal, paths, **_):
            stop = False

            def stop_me():
                nonlocal stop
                stop = True

            stop_signal.connect(stop_me)

            total_items = len(paths)
            for i, path in enumerate(paths):
                if stop:
                    return
                self.input_video = path
                self.source_video_path_widget.setText(str(self.input_video))
                self.video_path_widget.setText(str(self.input_video))
                try:
                    self.update_video_info(hide_progress=True)
                except Exception:
                    logger.exception(f"Could not load video {self.input_video}")
                else:
                    self.page_update(build_thumbnail=False)
                    self.add_to_queue()
                signal.emit(int((i / total_items) * 100))

        self.disable_all()
        self.container.status_bar.run_tasks(
            [Task(t("Loading Videos"), open_em, {"paths": paths})], signal_task=True, can_cancel=True
        )
        self.enable_all()

    def clear_current_video(self):
        if self._cover_extract_thread and self._cover_extract_thread.isRunning():
            self._cover_extract_thread.wait(2000)
            self._cover_extract_thread = None
        self.widgets.queue_button.setEnabled(True)
        self.widgets.queue_button.setToolTip("")
        self.widgets.convert_button.setEnabled(True)
        self.widgets.convert_button.setToolTip("")

        self.loading_video = True
        self.app.fastflix.current_video = None
        self.input_video = None
        self.source_video_path_widget.setText("")
        self.video_path_widget.setText(t("No Source Selected"))
        self.output_video_path_widget.setText("")
        self.widgets.output_directory.setText("")
        self.output_path_button.setDisabled(True)
        self.output_video_path_widget.setDisabled(True)
        self.filename_truncation_warning.hide()
        for i in range(self.widgets.video_track.count()):
            self.widgets.video_track.removeItem(0)
        self.widgets.preview.setText(t("No Video File"))

        self.widgets.flip.setCurrentIndex(0)
        self.widgets.rotate.setCurrentIndex(0)

        self.widgets.crop.top.setText("0")
        self.widgets.crop.left.setText("0")
        self.widgets.crop.right.setText("0")
        self.widgets.crop.bottom.setText("0")
        self.widgets.start_time.setText(self.number_to_time(0))
        self.widgets.end_time.setText(self.number_to_time(0))
        self.widgets.preview.setPixmap(QtGui.QPixmap())
        self.video_options.clear_tracks()
        self.video_bit_depth_label.hide()
        self.video_chroma_label.hide()
        self.video_hdr10_label.hide()
        self.video_hdr10plus_label.hide()
        self.disable_all()
        self.loading_video = False

    @reusables.log_exception("fastflix", show_traceback=True)
    def reload_video_from_queue(self, video: Video):
        if video.video_settings.video_encoder_settings.name not in self.app.fastflix.encoders:
            error_message(
                t("That video was added with an encoder that is no longer available, unable to load from queue")
            )
            raise FastFlixInternalException(
                t("That video was added with an encoder that is no longer available, unable to load from queue")
            )

        self.loading_video = True

        self.app.fastflix.current_video = video
        self.app.fastflix.current_video.work_path.mkdir(parents=True, exist_ok=True)
        self.input_video = video.source
        self.source_video_path_widget.setText(str(self.input_video))
        hdr10_indexes = [x.index for x in self.app.fastflix.current_video.hdr10_streams]
        text_video_tracks = [
            (
                f"{x.index}: {x.codec_name} {x.get('bit_depth', '8')}-bit "
                f"{x['color_primaries'] if x.get('color_primaries') else ''}"
                f"{' - HDR10' if x.index in hdr10_indexes else ''}"
                f"{' | HDR10+' if x.index in self.app.fastflix.current_video.hdr10_plus else ''}"
            )
            for x in self.app.fastflix.current_video.streams.video
        ]
        self.widgets.video_track.clear()
        self.widgets.video_track.addItems(text_video_tracks)
        # Show video track selector only when there's more than one video track
        if len(self.app.fastflix.current_video.streams.video) > 1:
            self.widgets.video_track_widget.show()
        else:
            self.widgets.video_track_widget.hide()
        for i, track in enumerate(text_video_tracks):
            if int(track.split(":")[0]) == self.app.fastflix.current_video.video_settings.selected_track:
                self.widgets.video_track.setCurrentIndex(i)
                break
        else:
            logger.warning(
                f"Could not find selected track {self.app.fastflix.current_video.video_settings.selected_track} "
                f"in {text_video_tracks}"
            )

        end_time = self.app.fastflix.current_video.video_settings.end_time or video.duration
        if self.app.fastflix.current_video.video_settings.crop:
            self.widgets.crop.top.setText(str(self.app.fastflix.current_video.video_settings.crop.top))
            self.widgets.crop.left.setText(str(self.app.fastflix.current_video.video_settings.crop.left))
            self.widgets.crop.right.setText(str(self.app.fastflix.current_video.video_settings.crop.right))
            self.widgets.crop.bottom.setText(str(self.app.fastflix.current_video.video_settings.crop.bottom))
        else:
            self.widgets.crop.top.setText("0")
            self.widgets.crop.left.setText("0")
            self.widgets.crop.right.setText("0")
            self.widgets.crop.bottom.setText("0")
        self.widgets.start_time.setText(self.number_to_time(video.video_settings.start_time))
        self.widgets.end_time.setText(self.number_to_time(end_time))

        fn = Path(video.video_settings.output_path)
        self.widgets.output_directory.setText(str(fn.parent.absolute()).rstrip("/").rstrip("\\"))
        self.output_video_path_widget.setText(fn.stem)
        self.widgets.output_type_combo.setCurrentText(fn.suffix)

        self.widgets.deinterlace.setChecked(self.app.fastflix.current_video.video_settings.deinterlace)
        self.widgets.remove_metadata.setChecked(self.app.fastflix.current_video.video_settings.remove_metadata)
        self.widgets.chapters.setChecked(self.app.fastflix.current_video.video_settings.copy_chapters)
        self.widgets.remove_hdr.setChecked(self.app.fastflix.current_video.video_settings.remove_hdr)
        self.widgets.rotate.setCurrentIndex(video.video_settings.rotate)
        self.widgets.fast_time.setCurrentIndex(0 if video.video_settings.fast_seek else 1)
        if video.video_settings.vertical_flip and video.video_settings.horizontal_flip:
            self.widgets.flip.setCurrentIndex(3)
        elif video.video_settings.vertical_flip:
            self.widgets.flip.setCurrentIndex(1)
        elif video.video_settings.horizontal_flip:
            self.widgets.flip.setCurrentIndex(2)

        self.video_options.advanced.video_title.setText(video.video_settings.video_title)
        self.video_options.advanced.video_track_title.setText(video.video_settings.video_track_title)

        self.video_options.reload()
        self.enable_all()

        self._start_cover_extraction()

        self.app.fastflix.current_video.status = Status()
        self.update_video_info_labels()
        self.loading_video = False
        self.page_update(build_thumbnail=True, force_build_thumbnail=True)

    @reusables.log_exception("fastflix", show_traceback=False)
    def update_video_info(self, hide_progress=False):
        self.loading_video = True
        folder, name = self.generate_output_filename
        self.output_video_path_widget.setText(name)
        self.widgets.output_directory.setText(folder.rstrip("/").rstrip("\\"))
        self._update_truncation_warning()
        self.output_video_path_widget.setDisabled(False)
        self.output_path_button.setDisabled(False)
        self.app.fastflix.current_video = Video(source=self.input_video, work_path=self.get_temp_work_path())
        self.app.fastflix.current_video.video_settings.template_generated_name = name
        tasks = [
            Task(t("Parse Video details"), parse),
            Task(t("Determine HDR details"), parse_hdr_details),
            Task(t("Detect HDR10+"), detect_hdr10_plus),
        ]
        if not self.app.fastflix.config.disable_deinterlace_check:
            tasks.append(Task(t("Detecting Interlace"), detect_interlaced, dict(source=self.source_material)))

        try:
            self.container.status_bar.run_tasks(tasks)
        except FlixError:
            error_message(f"{t('Not a video file')}<br>{self.input_video}")
            self.clear_current_video()
            return
        except Exception:
            logger.exception(f"Could not properly read the files {self.input_video}")
            self.clear_current_video()
            error_message(f"Could not properly read the file {self.input_video}")
            return

        hdr10_indexes = [x.index for x in self.app.fastflix.current_video.hdr10_streams]
        text_video_tracks = [
            (
                f"{x.index}: {x.codec_name} {x.get('bit_depth', '8')}-bit "
                f"{x['color_primaries'] if x.get('color_primaries') else ''}"
                f"{' - HDR10' if x.index in hdr10_indexes else ''}"
                f"{' | HDR10+' if x.index in self.app.fastflix.current_video.hdr10_plus else ''}"
            )
            for x in self.app.fastflix.current_video.streams.video
        ]
        self.widgets.video_track.clear()
        self.widgets.crop.top.setText("0")
        self.widgets.crop.left.setText("0")
        self.widgets.crop.right.setText("0")
        self.widgets.crop.bottom.setText("0")
        self.widgets.start_time.setText("0:00:00")

        self.widgets.video_track.addItems(text_video_tracks)

        # Show video track selector only when there's more than one video track
        if len(self.app.fastflix.current_video.streams.video) > 1:
            self.widgets.video_track_widget.show()
        else:
            self.widgets.video_track_widget.hide()

        logger.debug(f"{len(self.app.fastflix.current_video.streams['video'])} {t('video tracks found')}")
        logger.debug(f"{len(self.app.fastflix.current_video.streams['audio'])} {t('audio tracks found')}")

        if self.app.fastflix.current_video.streams["subtitle"]:
            logger.debug(f"{len(self.app.fastflix.current_video.streams['subtitle'])} {t('subtitle tracks found')}")
        if self.app.fastflix.current_video.streams["attachment"]:
            logger.debug(f"{len(self.app.fastflix.current_video.streams['attachment'])} {t('attachment tracks found')}")
        if self.app.fastflix.current_video.streams["data"]:
            logger.debug(f"{len(self.app.fastflix.current_video.streams['data'])} {t('data tracks found')}")

        self.widgets.end_time.setText(self.number_to_time(self.app.fastflix.current_video.duration))
        title_name = [
            v for k, v in self.app.fastflix.current_video.format.get("tags", {}).items() if k.lower() == "title"
        ]
        if title_name:
            self.video_options.advanced.video_title.setText(title_name[0])
        else:
            self.video_options.advanced.video_title.setText("")

        video_track_title_name = [
            v
            for k, v in self.app.fastflix.current_video.streams.video[0].get("tags", {}).items()
            if k.upper() == "TITLE"
        ]

        if video_track_title_name:
            self.video_options.advanced.video_track_title.setText(video_track_title_name[0])
        else:
            self.video_options.advanced.video_track_title.setText("")

        self.widgets.deinterlace.setChecked(self.app.fastflix.current_video.video_settings.deinterlace)

        logger.info("Updating video info")
        self.video_options.new_source()
        self.enable_all()

        self._start_cover_extraction()

        self.loading_video = False
        self.update_resolution_labels()
        self.update_video_info_labels()

        # Set preview slider steps: ~1 per 10 seconds, minimum 100
        slider_steps = max(100, int(self.app.fastflix.current_video.duration / 10))
        self.widgets.thumb_time.setMaximum(slider_steps)
        self.widgets.thumb_time.setPageStep(max(1, slider_steps // 20))
        self.widgets.thumb_time.setValue(max(1, slider_steps // 4))

        if self.app.fastflix.config.opt("auto_crop"):
            self.get_auto_crop()

        encoder = self.current_encoder
        if encoder and not getattr(encoder, "enable_concat", False) and self.app.fastflix.current_video.concat:
            error_message(f"{encoder.name} {t('does not support concatenating files together')}")

    @staticmethod
    def _chroma_from_pix_fmt(pix_fmt: str) -> str:
        if not pix_fmt:
            return ""
        fmt = pix_fmt.lower()
        if "444" in fmt:
            return "4:4:4"
        if "422" in fmt:
            return "4:2:2"
        if "420" in fmt or fmt in ("nv12", "nv12m", "nv21", "p010le"):
            return "4:2:0"
        if "411" in fmt:
            return "4:1:1"
        if "410" in fmt:
            return "4:1:0"
        if "440" in fmt:
            return "4:4:0"
        return ""

    def update_video_info_labels(self):
        if not self.app.fastflix.current_video:
            self.video_info_label.hide()
            self.video_codec_label.hide()
            self.video_bit_depth_label.hide()
            self.video_chroma_label.hide()
            self.video_hdr10_label.hide()
            self.video_hdr10plus_label.hide()
            return

        track_index = self.widgets.video_track.currentIndex()
        if track_index < 0:
            return
        stream = self.app.fastflix.current_video.streams.video[track_index]
        stream_idx = stream.index

        codec = stream.get("codec_name", "")
        if codec:
            self.video_codec_label.setText(codec.upper())
            self.video_codec_label.show()
        else:
            self.video_codec_label.hide()

        bit_depth = stream.get("bit_depth", "8")
        self.video_bit_depth_label.setText(f"{bit_depth}-bit")
        self.video_bit_depth_label.show()
        self.video_info_label.show()

        chroma = self._chroma_from_pix_fmt(stream.get("pix_fmt", ""))
        if chroma:
            self.video_chroma_label.setText(chroma)
            self.video_chroma_label.show()
        else:
            self.video_chroma_label.hide()

        hdr10_indexes = [x.index for x in self.app.fastflix.current_video.hdr10_streams]
        if stream_idx in hdr10_indexes:
            self.video_hdr10_label.setText("\u2714 HDR10")
            self.video_hdr10_label.setStyleSheet("color: #00cc00;")
            self.video_hdr10_label.show()
        else:
            self.video_hdr10_label.hide()

        if self.app.fastflix.config.hdr10plus_parser and stream_idx in self.app.fastflix.current_video.hdr10_plus:
            self.video_hdr10plus_label.setText("\u2714 HDR10+")
            self.video_hdr10plus_label.setStyleSheet("color: #00cc00;")
            self.video_hdr10plus_label.show()
        else:
            self.video_hdr10plus_label.hide()

    def _load_dropped_video(self):
        self.source_video_path_widget.setText(str(self.input_video))
        self.video_path_widget.setText(str(self.input_video))
        try:
            self.update_video_info()
        except Exception:
            logger.exception(f"Could not load video {self.input_video}")
            self.video_path_widget.setText("")
            self.output_video_path_widget.setText("")
            self.output_video_path_widget.setDisabled(True)
            self.widgets.output_directory.setText("")
            self.output_path_button.setDisabled(True)
            self.filename_truncation_warning.hide()
        self.page_update()

    def _start_cover_extraction(self):
        """Start background cover extraction thread."""
        if self.app.fastflix.config.disable_cover_extraction:
            return
        if not self.app.fastflix.current_video:
            return
        has_covers = any(
            track.get("tags", {}).get("filename", "").rsplit(".", 1)[0]
            in ("cover", "small_cover", "cover_land", "small_cover_land")
            for track in self.app.fastflix.current_video.streams.attachment
        )
        if not has_covers:
            return

        self.widgets.queue_button.setDisabled(True)
        self.widgets.queue_button.setToolTip(t("Extracting cover images..."))
        self.widgets.convert_button.setDisabled(True)
        self.widgets.convert_button.setToolTip(t("Extracting cover images..."))

        self.video_options.attachments.set_extracting(True)

        self._cover_extract_video_source = self.app.fastflix.current_video.source
        self._cover_extract_thread = ExtractCovers(app=self.app, main=self, signal=self.cover_extraction_complete)
        self._cover_extract_thread.start()

    def on_cover_extraction_complete(self):
        """Called when background cover extraction finishes."""
        self._cover_extract_thread = None

        self.widgets.queue_button.setEnabled(True)
        self.widgets.queue_button.setToolTip("")
        self.widgets.convert_button.setEnabled(True)
        self.widgets.convert_button.setToolTip("")

        if (
            self.app.fastflix.current_video
            and self.app.fastflix.current_video.source == self._cover_extract_video_source
        ):
            self.video_options.attachments.covers_extracted()
        self._cover_extract_video_source = None
