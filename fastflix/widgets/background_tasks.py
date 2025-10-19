#!/usr/bin/env python
# -*- coding: utf-8 -*-
import importlib.util
import logging
import os
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen, run, check_output
from packaging import version

from PySide6 import QtCore
from ffmpeg_normalize import FFmpegNormalize

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
    def __init__(self, app: FastFlixApp, main, index, signal, language, use_ocr=False):
        super().__init__(main)
        self.main = main
        self.app = app
        self.index = index
        self.signal = signal
        self.language = language
        self.use_ocr = use_ocr

    def run(self):
        subtitle_format = self._get_subtitle_format()
        if subtitle_format is None:
            self.main.thread_logging_signal.emit(
                f"WARNING:{t('Could not determine subtitle format for track')} {self.index}, {t('skipping extraction')}"
            )
            self.signal.emit()
            return

        # Flag to track if we need OCR conversion after extraction
        should_convert_to_srt = False

        if subtitle_format == "srt":
            extension = "srt"
            output_args = ["-c", "srt", "-f", "srt"]
        elif subtitle_format == "ass":
            extension = "ass"
            output_args = ["-c", "copy"]
        elif subtitle_format == "ssa":
            extension = "ssa"
            output_args = ["-c", "copy"]
        elif subtitle_format == "pgs":
            extension = "sup"
            output_args = ["-c", "copy"]
            # If OCR is requested, we'll extract .sup first, then convert after
            should_convert_to_srt = self.use_ocr and self.app.fastflix.config.enable_pgs_ocr
        else:
            self.main.thread_logging_signal.emit(
                f"WARNING:{t('Subtitle Track')} {self.index} {t('is not in supported format (SRT, ASS, SSA, PGS), skipping extraction')}: {subtitle_format}"
            )
            self.signal.emit()
            return

        # filename = str(
        # Path(self.main.output_video).parent / f"{self.main.output_video}.{self.index}.{self.language}.srt"
        # ).replace("\\", "/")
        filename = str(
            Path(self.main.output_video).parent / f"{self.main.output_video}.{self.index}.{self.language}.{extension}"
        ).replace("\\", "/")
        self.main.thread_logging_signal.emit(f"INFO:{t('Extracting subtitles to')} {filename}")

        try:
            result = run(
                [
                    self.app.fastflix.config.ffmpeg,
                    "-y",
                    "-i",
                    self.main.input_video,
                    "-map",
                    f"0:s:{self.index}",
                    *output_args,
                    filename,
                ],
                stdout=PIPE,
                stderr=STDOUT,
            )
        except Exception as err:
            self.main.thread_logging_signal.emit(f"ERROR:{t('Could not extract subtitle track')} {self.index} - {err}")
        else:
            if result.returncode != 0:
                self.main.thread_logging_signal.emit(
                    f"WARNING:{t('Could not extract subtitle track')} "
                    f"{self.index}: {result.stdout.decode('utf-8', errors='ignore')}"
                )
            else:
                self.main.thread_logging_signal.emit(f"INFO:{t('Extracted subtitles successfully')}")

                # If this is PGS and OCR was requested, convert the .sup to .srt
                if subtitle_format == "pgs" and should_convert_to_srt:
                    if self._convert_sup_to_srt(filename):
                        self.main.thread_logging_signal.emit(f"INFO:{t('Successfully converted to SRT with OCR')}")
                    else:
                        self.main.thread_logging_signal.emit(f"WARNING:{t('OCR conversion failed, kept .sup file')}")
        self.signal.emit()

    def _get_subtitle_format(self):
        try:
            result = run(
                [
                    self.app.fastflix.config.ffprobe,
                    "-v",
                    "error",
                    "-select_streams",
                    f"s:{self.index}",
                    "-show_entries",
                    "stream=codec_name",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    self.main.input_video,
                ],
                stdout=PIPE,
                stderr=STDOUT,
                text=True,
            )

            if result.returncode != 0:
                self.main.thread_logging_signal.emit(
                    f"WARNING:{t('Could not probe subtitle track')} {self.index}: {result.stdout}"
                )
                return None

            codec_name = result.stdout.strip().lower()
            if codec_name in ["subrip", "xsub", "webvtt", "mov_text"]:
                return "srt"
            elif codec_name == "ass":
                return "ass"
            elif codec_name == "ssa":
                return "ssa"
            elif codec_name == "hdmv_pgs_subtitle":
                return "pgs"
            else:
                self.main.thread_logging_signal.emit(
                    f"WARNING:{t('Subtitle Track')} {self.index} {t('is not in supported format (SRT, ASS, SSA, PGS), skipping extraction')}: {codec_name}"
                )
                return None

        except Exception as err:
            self.main.thread_logging_signal.emit(
                f"WARNING:{t('Error checking subtitle format for track')} {self.index} - {err}"
            )
            return None

    def _check_pgsrip_dependencies(self) -> bool:
        """Check all required dependencies for pgsrip OCR conversion"""
        missing = []

        # Check tesseract (auto-detected from PATH or config)
        if not self.app.fastflix.config.tesseract_path:
            missing.append("tesseract-ocr")

        # Check mkvmerge (CRITICAL - required by pgsrip but not documented)
        if not self.app.fastflix.config.mkvmerge_path:
            missing.append("mkvtoolnix")

        # Check if pgsrip Python library is available
        if importlib.util.find_spec("pgsrip") is None:
            missing.append("pgsrip (Python library)")

        if missing:
            self.main.thread_logging_signal.emit(
                f"ERROR:{t('Missing dependencies for PGS OCR')}: {', '.join(missing)}\n\n"
                f"Install instructions:\n"
                f"  pgsrip: pip install pgsrip\n"
                f"  Linux: sudo apt install tesseract-ocr mkvtoolnix\n"
                f"  macOS: brew install tesseract mkvtoolnix\n"
                f"  Windows:\n"
                f"    - Tesseract: https://github.com/UB-Mannheim/tesseract/wiki\n"
                f"    - MKVToolNix: https://mkvtoolnix.download/downloads.html"
            )
            return False

        return True

    def _convert_sup_to_srt(self, sup_filepath: str) -> bool:
        """Convert PGS subtitle to .srt using pgsrip OCR by processing the original MKV

        Args:
            sup_filepath: Path to the extracted .sup file (used for naming output)

        Returns:
            True if conversion successful, False otherwise
        """
        # Check dependencies first
        if not self._check_pgsrip_dependencies():
            return False

        try:
            self.main.thread_logging_signal.emit(
                f"INFO:{t('Converting .sup to .srt using OCR')} (this may take 3-5 minutes)..."
            )

            # Import pgsrip Python API
            from pgsrip import pgsrip, Mkv, Options
            from babelfish import Language as BabelLanguage

            # Set environment variables for pgsrip to find tesseract
            if self.app.fastflix.config.tesseract_path:
                # Add tesseract directory to PATH so pytesseract can find it
                tesseract_dir = str(Path(self.app.fastflix.config.tesseract_path).parent)
                os.environ["PATH"] = f"{tesseract_dir}{os.pathsep}{os.environ.get('PATH', '')}"
                os.environ["TESSERACT_CMD"] = str(self.app.fastflix.config.tesseract_path)

            # pgsrip needs the original MKV file, not the extracted .sup
            # The .sup file is a raw subtitle stream, but pgsrip expects an MKV container
            sup_path = Path(sup_filepath)
            media = Mkv(self.main.input_video)

            # Configure options for pgsrip
            # BabelLanguage needs different constructors for 2-letter vs 3-letter codes
            try:
                # Detect if language code is 2-letter or 3-letter
                if len(self.language) == 2:
                    babel_lang = BabelLanguage.fromalpha2(self.language)
                elif len(self.language) == 3:
                    babel_lang = BabelLanguage(self.language)
                else:
                    # Try as language name
                    babel_lang = BabelLanguage.fromname(self.language)

                options = Options(
                    languages={babel_lang},
                    overwrite=True,  # Overwrite existing .srt files
                    one_per_lang=True,  # Create one .srt per language
                )
            except Exception:
                # Fallback to English if language code is invalid
                options = Options(
                    languages={BabelLanguage("eng")},
                    overwrite=True,
                    one_per_lang=True,
                )

            # Run pgsrip conversion using Python API on the original MKV
            # This will create .srt files in the same directory as the video
            pgsrip.rip(media, options)

            # Look for the created .srt file
            # pgsrip creates files with pattern: basename.language.srt
            video_path = Path(self.main.input_video)
            srt_pattern = f"{video_path.stem}.*.srt"
            srt_files = list(video_path.parent.glob(srt_pattern))

            if not srt_files:
                # Fallback: look for any .srt in the video directory
                srt_files = list(video_path.parent.glob(f"{video_path.stem}.srt"))

            if not srt_files:
                raise Exception(f"pgsrip completed but no .srt file found in {video_path.parent}")

            # Move the .srt file to the expected location (same dir as .sup was)
            created_srt = srt_files[0]
            expected_srt = sup_path.with_suffix(".srt")

            if created_srt != expected_srt:
                # Move/rename to expected location
                import shutil

                shutil.move(str(created_srt), str(expected_srt))

            self.main.thread_logging_signal.emit(f"INFO:{t('OCR conversion successful')}: {expected_srt.name}")

            # Optionally delete the .sup file since we have .srt now
            try:
                sup_path.unlink()
                self.main.thread_logging_signal.emit(f"INFO:{t('Removed .sup file, kept .srt')}")
            except Exception:
                pass

            return True

        except Exception as err:
            self.main.thread_logging_signal.emit(f"ERROR:{t('OCR conversion failed')}: {err}")
            return False


class AudioNoramlize(QtCore.QThread):
    def __init__(self, app: FastFlixApp, main, audio_type, signal):
        super().__init__(main)
        self.main = main
        self.app = app
        self.signal = signal
        self.audio_type = audio_type

    def run(self):
        try:
            os.putenv("FFMPEG_PATH", str(self.app.fastflix.config.ffmpeg))
            out_file = self.app.fastflix.current_video.video_settings.output_path
            if not out_file:
                self.signal.emit("No source video provided")
            normalizer = FFmpegNormalize(
                audio_codec=self.audio_type, extension=out_file.suffix.lstrip("."), video_codec="copy", progress=True
            )
            logger.info(f"Running audio normalization - will output video to {str(out_file)}")
            normalizer.add_media_file(str(self.app.fastflix.current_video.source), str(out_file))
            normalizer.run_normalization()
            self.signal.emit("Completed")
        except Exception as e:
            logger.error(f"Audio normalization failed: {e}")
            self.signal.emit("Failed")


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

        self.main.thread_logging_signal.emit(f"INFO:{t('Extracting HDR10+ metadata')} to {output}")

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
