# -*- coding: utf-8 -*-
import logging
import os
from multiprocessing.pool import Pool
from pathlib import Path
from subprocess import PIPE, CompletedProcess, TimeoutExpired, run
from typing import List, Tuple, Union
from tempfile import TemporaryDirectory

import reusables
from box import Box, BoxError

from fastflix.language import t
from fastflix.models.config import Config
from fastflix.models.fastflix_app import FastFlixApp
from functools import partial
import time
from multiprocessing.pool import ThreadPool

# __all__ = ["FlixError", "ff_version", "Flix", "guess_bit_depth"]

here = os.path.abspath(os.path.dirname(__file__))

logger = logging.getLogger("fastflix")


class FlixError(Exception):
    """This fastflix won't fly"""


def guess_bit_depth(pix_fmt: str, color_primaries: str = None) -> int:
    eight = (
        "bgr0",
        "bgra",
        "gbrp",
        "gray",
        "monob",
        "monow",
        "nv12",
        "nv12m",
        "nv16",
        "nv20le",
        "nv21",
        "pal8",
        "rgb24",
        "rgb48le",
        "rgba",
        "rgba64le",
        "ya8",
        "yuv410p",
        "yuv411p",
        "yuv420p",
        "yuv422p",
        "yuv440p",
        "yuv444p",
        "yuva420p",
        "yuva422p",
        "yuva444p",
        "yuvj420p",
        "yuvj422p",
        "yuvj444p",
    )

    ten = ("yuv420p10le", "yuv422p10le", "yuv444p10le", "gbrp10le", "gray10le", "p010le")
    twelve = ("yuv420p12le", "yuv422p12le", "yuv444p12le", "gbrp12le", "gray12le")

    if pix_fmt in eight:
        return 8
    if pix_fmt in ten:
        return 10
    if pix_fmt in twelve:
        return 12

    if color_primaries and color_primaries.startswith("bt2020"):
        return 10
    else:
        return 8


def execute(command: List, work_dir: Union[Path, str] = None, timeout: int = None) -> CompletedProcess:
    logger.info(f"{t('Running command')}: {' '.join(command)}")
    return run(
        " ".join(command) if reusables.win_based else command,
        stdout=PIPE,
        stderr=PIPE,
        stdin=PIPE,
        cwd=work_dir,
        timeout=timeout,
        encoding="utf-8",
    )


def ffmpeg_configuration(app, config: Config, **_):
    """ Extract the version and libraries available from the specified version of FFmpeg """
    res = execute([f'"{config.ffmpeg}"', "-version"])
    if res.returncode != 0:
        raise FlixError(f'"{config.ffmpeg}" file not found')
    config = []
    try:
        version = res.stdout.split(" ", 4)[2]
    except (ValueError, IndexError):
        raise FlixError(f'Cannot parse version of ffmpeg from "{res.stdout}"')
    line_denote = "configuration: "
    for line in res.stdout.split("\n"):
        if line.startswith(line_denote):
            config = [x[9:].strip() for x in line[len(line_denote) :].split(" ") if x.startswith("--enable")]
    app.fastflix.ffmpeg_version = version
    app.fastflix.ffmpeg_config = config
    # return version, config


def probe(app: FastFlixApp, file: Path) -> Box:
    """ Run FFprobe on a file """
    command = [
        f'"{app.fastflix.config.ffprobe}"',
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        f'"{file}"',
    ]
    result = execute(command)
    try:
        return Box.from_json(result.stdout)
    except BoxError:
        logger.error(f"Could not read output: {result.stdout} - {result.stderr}")
        raise FlixError(result.stderr)


def determine_rotation(streams) -> Tuple[int, int]:
    rotation = 0
    if "rotate" in streams.video[0].get("tags", {}):
        rotation = abs(int(streams.video[0].tags.rotate))
    # elif 'side_data_list' in self.streams.video[0]:
    #     rots = [abs(int(x.rotation)) for x in self.streams.video[0].side_data_list if 'rotation' in x]
    #     rotation = rots[0] if rots else 0

    if rotation in (90, 270):
        video_width = streams.video[0].height
        video_height = streams.video[0].width
    else:
        video_width = streams.video[0].width
        video_height = streams.video[0].height
    return video_width, video_height


def parse(app: FastFlixApp, **_):
    data = probe(app, app.fastflix.current_video.source)
    if "streams" not in data:
        raise FlixError("Not a video file")
    streams = Box({"video": [], "audio": [], "subtitle": [], "attachment": [], "data": []})
    covers = []
    for track in data.streams:
        if track.codec_type == "video" and track.get("disposition", {}).get("attached_pic"):
            streams.attachment.append(track)
        elif track.codec_type in streams:
            streams[track.codec_type].append(track)
        else:
            logger.error(f"Unknown codec: {track.codec_type}")

    if not streams.video:
        raise FlixError("There were no video streams detected")

    for stream in streams.video:
        if "bits_per_raw_sample" in stream:
            stream.bit_depth = int(stream.bits_per_raw_sample)
        else:
            stream.bit_depth = guess_bit_depth(stream.pix_fmt, stream.get("color_primaries"))

    app.fastflix.current_video.streams = streams
    app.fastflix.current_video.video_settings.selected_track = streams.video[0].index
    app.fastflix.current_video.width, app.fastflix.current_video.height = determine_rotation(streams)
    app.fastflix.current_video.format = data.format
    app.fastflix.current_video.duration = float(data.format.get("duration", 0))


def extract_attachments(app: FastFlixApp, **_):
    for track in app.fastflix.current_video.streams.attachment:
        filename = track.get("tags", {}).get("filename", "")
        if filename.rsplit(".", 1)[0] in ("cover", "small_cover", "cover_land", "small_cover_land"):
            extract_attachment(
                app.fastflix.config.ffmpeg,
                app.fastflix.current_video.source,
                track.index,
                app.fastflix.current_video.work_path,
                filename,
            )


def extract_attachment(ffmpeg: Path, source: Path, stream: int, work_dir: TemporaryDirectory, file_name: str):
    try:
        execute(
            [
                f'"{ffmpeg}"',
                "-y",
                "-i",
                f'"{source}"',
                "-map",
                f"0:{stream}",
                "-c",
                "copy",
                "-vframes",
                "1",
                f'"{file_name}"',
            ],
            work_dir=work_dir.name,
            timeout=5,
        )
    except TimeoutExpired:
        logger.warning(f"WARNING Timeout while extracting cover file {file_name}")


def generate_thumbnail_command(
    config: Config, source: Path, output: Path, filters: str, start_time: float = 0, input_track: int = 0
) -> str:
    start = ""
    if start_time:
        start = f"-ss {start_time}"
    return (
        f'"{config.ffmpeg}" {start} -loglevel error -i "{source}" '
        f" {filters} -an -y -map_metadata -1 -map 0:{input_track} "
        f'-vframes 1 "{output}" '
    )


def get_auto_crop(
    config: Config,
    source: Path,
    video_width: int,
    video_height: int,
    input_track: int,
    start_time: float,
    result_list: List,
    **_,
):
    output = execute(
        [
            f'"{config.ffmpeg}"',
            "-hide_banner",
            "-ss",
            f"{start_time}",
            "-i",
            f'"{source}"',
            "-map",
            f"0:{input_track}",
            "-vf",
            "cropdetect",
            "-vframes",
            "10",
            "-f",
            "null",
            "-",
        ]
    )

    width, height, x_crop, y_crop = None, None, None, None
    for line in output.stderr.splitlines():
        if line.startswith("[Parsed_cropdetect"):
            w, h, x, y = [int(x) for x in line.rsplit("=")[1].split(":")]
            if (not x_crop or (x_crop and x > x_crop)) and (not width or (width and w < width)):
                width = w
                x_crop = x
            if (not height or (height and h < height)) and (not y_crop or (y_crop and y > y_crop)):
                height = h
                y_crop = y

    if None in (width, height, x_crop, y_crop):
        return 0, 0, 0, 0

    result_list.append([video_width - width - x_crop, video_height - height - y_crop, x_crop, y_crop])


def ffmpeg_audio_encoders(app, config: Config) -> List:
    cmd = execute([f'"{config.ffmpeg}"', "-hide_banner", "-encoders"])
    encoders = []
    start_line = " ------"
    started = False
    for line in cmd.stdout.splitlines():
        if started:
            if line.strip().startswith("A"):
                encoders.append(line.strip().split(" ")[1])
        elif line.startswith(start_line):
            started = True
    app.fastflix.audio_encoders = encoders
    return encoders


def convert_mastering_display(data: Box) -> Tuple[Box, str]:
    master_display = None
    cll = None

    def s(a, v, base=50_000):
        upper, lower = [int(x) for x in a.get(v, "0/0").split("/")]
        if lower != base:
            upper *= base / lower
        return int(upper)

    for item in data["side_data_list"]:
        if item.side_data_type == "Mastering display metadata":
            # TODO make into dataclass
            master_display = Box(
                red=f"({s(item, 'red_x')},{s(item, 'red_y')})",
                green=f"({s(item, 'green_x')},{s(item, 'green_y')})",
                blue=f"({s(item, 'blue_x')},{s(item, 'blue_y')})",
                white=f"({s(item, 'white_point_x')},{s(item, 'white_point_y')})",
                luminance=f"({s(item, 'max_luminance', base=10_000)},{s(item, 'min_luminance', base=10_000)})",
            )
        if item.side_data_type == "Content light level metadata":
            cll = f"{item.max_content},{item.max_average}"
    return master_display, cll


def parse_hdr_details(app: FastFlixApp, **_):
    streams = app.fastflix.current_video.streams
    video_track = app.fastflix.current_video.video_settings.selected_track
    if streams and streams.video:
        for video_stream in streams.video:
            if video_stream["index"] == video_track and video_stream.get("side_data_list"):
                try:
                    master_display, cll = convert_mastering_display(streams.video[0])
                except Exception:
                    logger.exception(f"Unexpected error while processing master-display from {streams.video[0]}")
                else:
                    if master_display:
                        app.fastflix.current_video.pix_fmt = streams.video[video_track].get("pix_fmt", "")
                        app.fastflix.current_video.color_space = streams.video[video_track].get("color_space", "")
                        app.fastflix.current_video.color_primaries = streams.video[video_track].get(
                            "color_primaries", ""
                        )
                        app.fastflix.current_video.color_transfer = streams.video[video_track].get("color_transfer", "")
                        app.fastflix.current_video.master_display = master_display
                        app.fastflix.current_video.cll = cll
                        return
    result = execute(
        [
            f'"{app.fastflix.config.ffprobe}"',
            "-select_streams",
            f"v:{video_track}",
            "-print_format",
            "json",
            "-show_frames",
            "-read_intervals",
            '"%+#1"',
            "-show_entries",
            '"frame=color_space,color_primaries,color_transfer,side_data_list,pix_fmt"',
            "-i",
            f'"{app.fastflix.current_video.source}"',
        ]
    )

    try:
        data = Box.from_json(result.stdout, default_box=True, default_box_attr="")
    except BoxError:
        # Could not parse details
        logger.error(
            "COULD NOT PARSE FFPROBE HDR METADATA, PLEASE OPEN ISSUE WITH THESE DETAILS:"
            f"\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )
        return
    if "frames" not in data or not len(data.frames):
        return
    data = data.frames[0]
    if not data.get("side_data_list"):
        return

    try:
        master_display, cll = convert_mastering_display(data)
    except Exception:
        logger.exception(f"Unexpected error while processing master-display from {streams.video[0]}")
    else:
        app.fastflix.current_video.pix_fmt = data.pix_fmt
        app.fastflix.current_video.color_space = data.color_space
        app.fastflix.current_video.color_primaries = data.color_primaries
        app.fastflix.current_video.color_transfer = data.color_transfer
        app.fastflix.current_video.master_display = master_display
        app.fastflix.current_video.cll = cll
