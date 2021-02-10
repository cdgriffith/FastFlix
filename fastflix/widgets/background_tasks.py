#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen, run

from qtpy import QtCore

from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.shared import unixy

logger = logging.getLogger("fastflix")

__all__ = ["ThumbnailCreator", "ExtractSubtitleSRT", "SubtitleFix", "ExtractHDR10"]


class ThumbnailCreator(QtCore.QThread):
    def __init__(self, main, command=""):
        super().__init__(main)
        self.main = main
        self.command = command

    def run(self):
        self.main.thread_logging_signal.emit(f"INFO:{t('Generating thumbnail')}: {self.command}")
        result = run(self.command, stdin=PIPE, stdout=PIPE, stderr=STDOUT, shell=True)
        if result.returncode > 0:
            if "No such filter: 'zscale'" in result.stdout.decode(encoding="utf-8", errors="ignore"):
                self.main.thread_logging_signal.emit(
                    "ERROR:Could not generate thumbnail because you are using an outdated FFmpeg! "
                    "Please use FFmpeg 4.3+ built against the latest zimg libraries. "
                    "Static builds available at https://ffmpeg.org/download.html "
                    "(Linux distributions are often slow to update)"
                )
            else:
                self.main.thread_logging_signal.emit(f"ERROR:{t('Could not generate thumbnail')}: {result.stdout}")

            self.main.thumbnail_complete.emit(0)
        else:
            self.main.thumbnail_complete.emit(1)


class SubtitleFix(QtCore.QThread):
    def __init__(self, main, mkv_prop_edit, video_path):
        super().__init__(main)
        self.main = main
        self.mkv_prop_edit = mkv_prop_edit
        self.video_path = video_path

    def run(self):
        output_file = unixy(self.video_path)
        self.main.thread_logging_signal.emit(f'INFO:{t("Will fix first subtitle track to not be default")}')
        try:
            result = run(
                [self.mkv_prop_edit, output_file, "--edit", "track:s1", "--set", "flag-default=0"],
                stdout=PIPE,
                stderr=STDOUT,
            )
        except Exception as err:
            self.main.thread_logging_signal.emit(f'ERROR:{t("Could not fix first subtitle track")} - {err}')
        else:
            if result.returncode != 0:
                self.main.thread_logging_signal.emit(
                    f'WARNING:{t("Could not fix first subtitle track")}: {result.stdout}'
                )


class ExtractSubtitleSRT(QtCore.QThread):
    def __init__(self, app: FastFlixApp, main, index, signal):
        super().__init__(main)
        self.main = main
        self.app = app
        self.index = index
        self.signal = signal

    def run(self):
        filename = str(Path(self.main.output_video).parent / f"{self.main.output_video}.{self.index}.srt").replace(
            "\\", "/"
        )
        self.main.thread_logging_signal.emit(f'INFO:{t("Extracting subtitles to")} {filename}')

        try:
            result = run(
                [
                    self.app.fastflix.config.ffmpeg,
                    "-y",
                    "-i",
                    self.main.input_video,
                    "-map",
                    f"0:{self.index}",
                    "-c",
                    "srt",
                    "-f",
                    "srt",
                    filename,
                ],
                stdout=PIPE,
                stderr=STDOUT,
            )
        except Exception as err:
            self.main.thread_logging_signal.emit(f'ERROR:{t("Could not extract subtitle track")} {self.index} - {err}')
        else:
            if result.returncode != 0:
                self.main.thread_logging_signal.emit(
                    f'WARNING:{t("Could not extract subtitle track")} {self.index}: {result.stdout}'
                )
            else:
                self.main.thread_logging_signal.emit(f'INFO:{t("Extracted subtitles successfully")}')
        self.signal.emit()


class ExtractHDR10(QtCore.QThread):
    def __init__(self, app: FastFlixApp, main, signal, ffmpeg_signal):
        super().__init__(main)
        self.main = main
        self.app = app
        self.signal = signal
        self.ffmpeg_signal = ffmpeg_signal

    def run(self):
        if not self.app.fastflix.current_video.hdr10_plus:
            self.main.thread_logging_signal.emit("ERROR:No tracks have HDR10+ data to extract")
            return

        output = self.app.fastflix.current_video.work_path / "metadata.json"

        track = self.app.fastflix.current_video.video_settings.selected_track
        if track not in self.app.fastflix.current_video.hdr10_plus:
            self.main.thread_logging_signal.emit(
                "WARNING:Selected video track not detected to have HDR10+ data, selecting first track that does"
            )
            track = self.app.fastflix.current_video.hdr10_plus[0]

        self.main.thread_logging_signal.emit(f'INFO:{t("Extracting HDR10+ metadata")} to {output}')

        self.ffmpeg_signal.emit("Extracting HDR10+ metadata")

        process = Popen(
            [
                self.app.fastflix.config.ffmpeg,
                "-y",
                "-i",
                unixy(self.app.fastflix.current_video.source),
                "-map",
                f"0:{track}",
                "-c:v",
                "copy",
                "-vbsf",
                "hevc_mp4toannexb",
                "-f",
                "hevc",
                "-",
            ],
            stdout=PIPE,
            stderr=open(self.app.fastflix.current_video.work_path / "hdr10extract_out.txt", "wb"),
            # stdin=PIPE,  # FFmpeg can try to read stdin and wrecks havoc
        )

        process_two = Popen(
            [self.app.fastflix.config.hdr10plus_parser, "-o", unixy(output), "-"],
            stdout=PIPE,
            stderr=PIPE,
            stdin=process.stdout,
            encoding="utf-8",
            cwd=str(self.app.fastflix.current_video.work_path),
        )

        with open(self.app.fastflix.current_video.work_path / "hdr10extract_out.txt", "r", encoding="utf-8") as f:
            while True:
                if process.poll() is not None or process_two.poll() is not None:
                    break
                if line := f.readline().rstrip():
                    if line.startswith("frame"):
                        self.ffmpeg_signal.emit(line)

        stdout, stderr = process_two.communicate()
        self.main.thread_logging_signal.emit(f"DEBUG: HDR10+ Extract: {stdout}")
        self.signal.emit(str(output))
