#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen, run, check_output
from packaging import version

from PySide6 import QtCore

from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.shared import clean_file_string

logger = logging.getLogger("fastflix")

__all__ = ["ThumbnailCreator", "ExtractSubtitleSRT", "ExtractHDR10"]


class ThumbnailCreator(QtCore.QThread):
    def __init__(self, main, command=""):
        super().__init__(main)
        self.main = main
        self.command = command

    def run(self):
        self.main.thread_logging_signal.emit(f"DEBUG:{t('Generating thumbnail')}: {self.command}")
        result = run(self.command, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        if result.returncode > 0:
            if "No such filter: 'zscale'" in result.stdout.decode(encoding="utf-8", errors="ignore"):
                self.main.thread_logging_signal.emit(
                    "ERROR:Could not generate thumbnail because you are using an outdated FFmpeg! "
                    "Please use FFmpeg 4.3+ built against the latest zimg libraries. "
                    "Static builds available at https://ffmpeg.org/download.html "
                )
            if "OpenCL mapping not usable" in result.stdout.decode(encoding="utf-8", errors="ignore"):
                self.main.thread_logging_signal.emit("ERROR trying to use OpenCL for thumbnail generation")
                self.main.thumbnail_complete.emit(2)
            else:
                self.main.thread_logging_signal.emit(f"ERROR:{t('Could not generate thumbnail')}: {result.stdout}")

            self.main.thumbnail_complete.emit(0)
        else:
            self.main.thumbnail_complete.emit(1)


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

        hdr10_parser_version_output = check_output(
            [str(self.app.fastflix.config.hdr10plus_parser), "--version"], encoding="utf-8"
        )
        _, version_string = hdr10_parser_version_output.rsplit(sep=" ", maxsplit=1)
        hdr10_parser_version = version.parse(version_string)
        self.main.thread_logging_signal.emit(f"Using HDR10 parser version {str(hdr10_parser_version).strip()}")

        ffmpeg_command = [
            str(self.app.fastflix.config.ffmpeg),
            "-y",
            "-i",
            clean_file_string(self.app.fastflix.current_video.source),
            "-map",
            f"0:{track}",
            "-c:v",
            "copy",
            "-bsf:v",
            "hevc_mp4toannexb",
            "-f",
            "hevc",
            "-",
        ]

        hdr10_parser_command = [str(self.app.fastflix.config.hdr10plus_parser), "-o", clean_file_string(output), "-"]
        if hdr10_parser_version >= version.parse("1.0.0"):
            hdr10_parser_command.insert(1, "extract")

        self.main.thread_logging_signal.emit(
            f"Running command: {' '.join(ffmpeg_command)} | {' '.join(hdr10_parser_command)}"
        )

        process = Popen(
            ffmpeg_command,
            stdout=PIPE,
            stderr=open(self.app.fastflix.current_video.work_path / "hdr10extract_out.txt", "wb"),
            # stdin=PIPE,  # FFmpeg can try to read stdin and wrecks havoc
        )

        process_two = Popen(
            hdr10_parser_command,
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
