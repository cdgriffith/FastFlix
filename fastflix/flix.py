# -*- coding: utf-8 -*-
import logging
import os
from multiprocessing.pool import Pool
from subprocess import PIPE, run, TimeoutExpired, CompletedProcess
from typing import Tuple, List, Union
from pathlib import Path

from box import Box, BoxError
import reusables

from fastflix.models.config import Config

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

    if color_primaries == "bt2020":
        return 10
    else:
        return 8


def execute(command: List, work_dir: Path = None, timeout: int = None) -> CompletedProcess:
    print(f"running command: {' '.join(command)}")
    return run(
        " ".join(command) if reusables.win_based else command,
        stdout=PIPE,
        stderr=PIPE,
        stdin=PIPE,
        cwd=work_dir,
        timeout=timeout,
        encoding="utf-8",
    )


def ffmpeg_configuration(app, config: Config, **_) -> Tuple[str, list]:
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
    app.fastflix.ffmpeg.version = version
    app.fastflix.ffmpeg.config = config
    # return version, config


def probe(config: Config, file: Path) -> Box:
    """ Run FFprobe on a file """
    command = [
        f'"{config.ffprobe}"',
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
        return Box.from_json(result.stdout.decode("utf-8"))
    except BoxError:
        logger.error(f"Could not decode output: {result.stderr}")
        raise FlixError(result.stderr)


def parse(config: Config, file: Path, temp_dir: Path, extract_covers: bool = False) -> Tuple[Box, str]:
    data = probe(config, file)
    if "streams" not in data:
        raise FlixError("Not a video file")
    streams = Box({"video": [], "audio": [], "subtitle": [], "attachment": [], "data": []})
    covers = []
    for track in data.streams:
        if track.codec_type == "video" and track.get("disposition", {}).get("attached_pic"):
            filename = track.get("tags", {}).get("filename", "")
            if filename.rsplit(".", 1)[0] in ("cover", "small_cover", "cover_land", "small_cover_land"):
                covers.append((file, track.index, temp_dir, filename))
            streams.attachment.append(track)
        elif track.codec_type in streams:
            streams[track.codec_type].append(track)
        else:
            logger.error(f"Unknown codec: {track.codec_type}")

    if extract_covers:
        with Pool(processes=4) as pool:
            pool.starmap(extract_attachment, covers)

    for stream in streams.video:
        if "bits_per_raw_sample" in stream:
            stream.bit_depth = int(stream.bits_per_raw_sample)
        else:
            stream.bit_depth = guess_bit_depth(stream.pix_fmt, stream.get("color_primaries"))
    return streams, data.format


def extract_attachment(config: Config, source: Path, stream: int, work_dir: Path, file_name: str):
    try:
        execute(
            [f'"{config.ffmpeg}"', "-y", "-i", f'"{source}"', "-map", f"0:{stream}", "-c", "copy", f'"{file_name}"'],
            work_dir=work_dir,
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
    config: Config, source: Path, video_width: int, video_height: int, start_time: float, input_track: int
) -> Tuple[int, int, int, int]:
    output = execute(
        [
            f'"{config.ffmpeg}"',
            "-ss",
            f"{start_time}",
            "-hide_banner",
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

    return video_width - width - x_crop, video_height - height - y_crop, x_crop, y_crop


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
    app.fastflix.ffmpeg.audio_encoders = encoders
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


def parse_hdr_details(config: Config, source: Path, video_track: int = 0, streams: Box = None) -> Union[Box, None]:
    if streams and streams.video and streams.video[video_track].get("side_data_list"):
        try:
            master_display, cll = convert_mastering_display(streams.video[0])
        except Exception:
            logger.exception(f"Unexpected error while processing master-display from {streams.video[0]}")
        else:
            if master_display:
                return Box(
                    pix_fmt=streams.video[video_track].get("pix_fmt"),
                    color_space=streams.video[video_track].get("color_space"),
                    color_primaries=streams.video[video_track].get("color_primaries"),
                    color_transfer=streams.video[video_track].get("color_transfer"),
                    master_display=master_display,
                    cll=cll,
                )

    result = execute(
        [
            f'"{config.ffprobe}"',
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
            f'"{source}"',
        ]
    )

    try:
        data = Box.from_json(result.stdout, default_box=True, default_box_attr=None)
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
        return Box(
            pix_fmt=data.pix_fmt,
            color_space=data.color_space,
            color_primaries=data.color_primaries,
            color_transfer=data.color_transfer,
            master_display=master_display,
            cll=cll,
        )
