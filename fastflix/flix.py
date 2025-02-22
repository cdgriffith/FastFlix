# -*- coding: utf-8 -*-
import logging
import os
import re
from pathlib import Path
from subprocess import PIPE, CompletedProcess, Popen, TimeoutExpired, run, check_output
from typing import List, Tuple, Union
from packaging import version
import shlex

import reusables
from box import Box, BoxError

from fastflix.exceptions import FlixError
from fastflix.language import t
from fastflix.models.config import Config
from fastflix.models.fastflix_app import FastFlixApp

here = os.path.abspath(os.path.dirname(__file__))
re_tff = re.compile(r"TFF:\s+(\d+)")
re_bff = re.compile(r"BFF:\s+(\d+)")
re_progressive = re.compile(r"Progressive:\s+(\d+)")

logger = logging.getLogger("fastflix")

HDR10_parser_version = None

ffmpeg_valid_color_primaries = [
    "bt709",
    "bt470m",
    "bt470bg",
    "smpte170m",
    "smpte240m",
    "film",
    "bt2020",
    "smpte428",
    "smpte428_1",
    "smpte431",
    "smpte432",
    "jedec-p22",
]

ffmpeg_valid_color_transfers = [
    "bt709",
    "gamma22",
    "gamma28",
    "smpte170m",
    "smpte240m",
    "linear",
    "log",
    "log100",
    "log_sqrt",
    "log316",
    "iec61966_2_4",
    "iec61966-2-4",
    "bt1361",
    "bt1361e",
    "iec61966_2_1",
    "iec61966-2-1",
    "bt2020_10",
    "bt2020_10bit",
    "bt2020_12",
    "bt2020_12bit",
    "bt2020-10",
    "bt2020-10bit",
    "bt2020-12",
    "bt2020-12bit",
    "smpte2084",
    "smpte428",
    "smpte428_1",
    "smpte428-1",
    "arib-std-b67",
]

ffmpeg_valid_color_space = [
    "rgb",
    "bt709",
    "fcc",
    "bt470bg",
    "smpte170m",
    "smpte240m",
    "ycocg",
    "bt2020nc",
    "bt2020_ncl",
    "bt2020c",
    "bt2020_cl",
    "smpte2085",
    "chroma-derived-nc",
    "chroma-derived-c",
    "ictcp",
]


def clean_file_string(source):
    return str(source).strip()


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
    return 8


def execute(command: List, work_dir: Union[Path, str] = None, timeout: int = None) -> CompletedProcess:
    logger.info(f"{t('Running command')}: {' '.join(command)}")
    return run(
        command,
        stdout=PIPE,
        stderr=PIPE,
        stdin=PIPE,
        cwd=work_dir,
        timeout=timeout,
        encoding="utf-8",
    )


def ffmpeg_configuration(app, config: Config, **_):
    """Extract the version and libraries available from the specified version of FFmpeg"""
    res = execute([f"{config.ffmpeg}", "-version"])
    if res.returncode != 0:
        logger.error(f"{config.ffmpeg} command stdout: {res.stdout}")
        logger.error(f"{config.ffmpeg} command stderr: {res.stderr}")
        raise FlixError(f'"{config.ffmpeg}" file not found or errored while executing. Return code {res.returncode}')
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


def ffprobe_configuration(app, config: Config, **_):
    """Extract the version of ffprobe"""
    res = execute([f"{config.ffprobe}", "-version"])
    if res.returncode != 0:
        raise FlixError(f'"{config.ffprobe}" file not found')
    try:
        version = res.stdout.split(" ", 4)[2]
    except (ValueError, IndexError):
        raise FlixError(f'Cannot parse version of ffprobe from "{res.stdout}"')
    app.fastflix.ffprobe_version = version


def probe(app: FastFlixApp, file: Path) -> Box:
    """
    Run FFprobe on a file
    ffprobe -v quiet -loglevel panic -print_format json -show_format -show_streams
    """
    command = [
        f"{app.fastflix.config.ffprobe}",
        "-v",
        "quiet",
        "-loglevel",
        "panic",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        clean_file_string(file),
    ]
    result = execute(command)
    if result.returncode != 0:
        raise FlixError(f"Error code returned running FFprobe: {result.stdout} - {result.stderr}")

    if result.stdout.strip() == "{}":
        raise FlixError(f"No output from FFprobe, not a known video type. stderr: {result.stderr}")

    try:
        return Box.from_json(result.stdout)
    except BoxError:
        logger.error(f"Could not read output: {result.stdout} - {result.stderr}")
        raise FlixError(result.stderr)


def get_all_concat_items(file):
    items = []
    with open(file) as f:
        for line in f:
            if line.strip().startswith("#"):
                continue
            elif line.strip().startswith("file"):
                filename = Path(line.strip()[5:].strip("'\""))
                if not filename.exists():
                    raise FlixError(f'No file "{filename}" exists')
                items.append(filename)
    return items


def get_concat_item(file, location=0):
    all_items = get_all_concat_items(file)
    if not all_items:
        raise FlixError("concat file must start with `file` on each line.")
    if location == 0:
        return all_items[0]
    section = len(all_items) // 10
    item_num = int((location * section)) - 1
    if item_num >= len(all_items):
        return all_items[-1]
    return all_items[item_num]


def parse(app: FastFlixApp, **_):
    source = app.fastflix.current_video.source
    if source.name.lower().endswith("txt"):
        source = get_concat_item(source)
        app.fastflix.current_video.concat = True
    data = probe(app, source)
    if "streams" not in data:
        raise FlixError(f"Not a video file, FFprobe output: {data}")
    streams = Box({"video": [], "audio": [], "subtitle": [], "attachment": [], "data": []})
    for track in data.streams:
        if track.codec_type == "video" and (
            track.get("disposition", {}).get("attached_pic")
            or track.get("tags", {}).get("MIMETYPE", "").startswith("image")
        ):
            streams.attachment.append(track)
        elif track.codec_type in streams:
            streams[track.codec_type].append(track)
        else:
            logger.error(f"Unknown codec: {track.codec_type}")

    if not streams.video:
        raise FlixError(f"There were no video streams detected: {data}")

    for stream in streams.video:
        if "bits_per_raw_sample" in stream:
            stream.bit_depth = int(stream.bits_per_raw_sample)
        else:
            stream.bit_depth = guess_bit_depth(stream.pix_fmt, stream.get("color_primaries"))

    app.fastflix.current_video.streams = streams
    app.fastflix.current_video.video_settings.selected_track = streams.video[0].index
    app.fastflix.current_video.format = data.format
    app.fastflix.current_video.duration = float(data.format.get("duration", 0))


def extract_attachments(app: FastFlixApp, **_):
    if app.fastflix.config.disable_cover_extraction:
        return
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


def extract_attachment(ffmpeg: Path, source: Path, stream: int, work_dir: Path, file_name: str):
    try:
        execute(
            [
                f"{ffmpeg}",
                "-y",
                "-i",
                clean_file_string(source),
                "-map",
                f"0:{stream}",
                "-c",
                "copy",
                "-vframes",
                "1",
                clean_file_string(file_name),
            ],
            work_dir=work_dir,
            timeout=5,
        )
    except TimeoutExpired:
        logger.warning(f"WARNING Timeout while extracting cover file {file_name}")


def generate_thumbnail_command(
    config: Config,
    source: Path,
    output: Path,
    filters: str,
    start_time: float = 0,
    input_track: int = 0,
    enable_opencl: bool = False,
) -> list[str]:
    command = [str(config.ffmpeg)]

    # Trim from start this many seconds
    if start_time:
        command += ["-ss", str(start_time)]

    # Less logging
    # Video file input
    command += ["-loglevel", "warning", "-i", clean_file_string(source)]

    # Hardware acceleration with OpenCL
    if enable_opencl:
        command += ["-init_hw_device", "opencl:0.0=ocl", "-filter_hw_device", "ocl"]

    command += shlex.split(filters)

    # Apply video track selection
    if "-map" not in filters:
        command += ["-map", f"0:{input_track}"]

    command += ["-an", "-y", "-map_metadata", "-1", "-frames:v", "1", clean_file_string(output)]

    return command


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
            f"{config.ffmpeg}",
            "-y",
            "-hide_banner",
            "-ss",
            f"{start_time}",
            "-i",
            clean_file_string(source),
            "-map",
            f"0:{input_track}",
            "-vf",
            "cropdetect=round=2",
            "-vframes",
            "10",
            "-f",
            "null",
            "-",
        ]
    )

    width, height, x_crop, y_crop = None, None, None, None
    if not output.stderr:
        return 0, 0, 0, 0

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


def detect_interlaced(app: FastFlixApp, config: Config, source: Path, **_):
    """http://www.aktau.be/2013/09/22/detecting-interlaced-video-with-ffmpeg/"""

    # Interlaced
    # [Parsed_idet_0 @ 00000] Repeated Fields: Neither:   815 Top:    88 Bottom:    98
    # [Parsed_idet_0 @ 00000] Single frame detection: TFF:   693 BFF:     0 Progressive:    39 Undetermined:   269
    # [Parsed_idet_0 @ 00000] Multi frame detection: TFF:   911 BFF:     0 Progressive:    41 Undetermined:    49

    # Progressive
    # [Parsed_idet_0 @ 00000] Repeated Fields: Neither:  1000 Top:     0 Bottom:     0
    # [Parsed_idet_0 @ 00000] Single frame detection: TFF:     0 BFF:     0 Progressive:   641 Undetermined:   359
    # [Parsed_idet_0 @ 00000] Multi frame detection: TFF:     0 BFF:     0 Progressive:   953 Undetermined:    47

    try:
        output = execute(
            [
                f"{config.ffmpeg}",
                "-hide_banner",
                "-i",
                clean_file_string(source),
                "-vf",
                "idet",
                "-frames:v",
                "100",
                "-an",
                "-sn",
                "-dn",
                "-f",
                "rawvideo",
                f"{'NUL' if reusables.win_based else '/dev/null'}",
                "-y",
            ]
        )
    except Exception:
        logger.exception("Error while running the interlace detection command")
        return

    if not output.stderr:
        logger.warning("Could not extract interlaced information")
        return

    for line in output.stderr.splitlines():
        if "Single frame detection" in line:
            try:
                tffs = re_tff.findall(line)[0]
                bffs = re_bff.findall(line)[0]
                progressive = re_progressive.findall(line)[0]
            except IndexError:
                logger.error(f"Could not extract interlaced information via regex: {line}")
            else:
                if int(tffs) + int(bffs) > int(progressive):
                    app.fastflix.current_video.video_settings.deinterlace = True
                    app.fastflix.current_video.interlaced = "tff" if int(tffs) > int(bffs) else "bff"
                    return
    app.fastflix.current_video.video_settings.deinterlace = False
    app.fastflix.current_video.interlaced = False


def ffmpeg_audio_encoders(app, config: Config) -> List:
    cmd = execute([f"{config.ffmpeg}", "-hide_banner", "-encoders"])
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


def ffmpeg_opencl_support(app, config: Config) -> bool:
    cmd = execute([f"{config.ffmpeg}", "-hide_banner", "-log_level", "error", "-init_hw_device", "opencl:0.0", "-h"])
    app.fastflix.opencl_support = cmd.returncode == 0
    return app.fastflix.opencl_support


def convert_mastering_display(data: Box) -> Tuple[Box, str]:
    master_display = None
    cll = None

    def s(a, v, base=50_000):
        try:
            upper, lower = [int(x) for x in a.get(v, "0/0").split("/")]
        except ValueError:
            raise FlixError(f"Could not parse HDR value {a} from {v}")
        if lower <= 0:  # avoid division by zero
            raise FlixError(f"HDR value outside expected range, {v} was {a}")
        if lower != base:
            upper *= base / lower
        value = int(upper)
        if value < 0 or value > 4_294_967_295:  # 32-bit unsigned int max size
            raise FlixError("HDR value outside expected range")
        return value

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
                    master_display, cll = convert_mastering_display(video_stream)
                except FlixError as err:
                    logger.error(str(err))
                except Exception:
                    logger.exception(f"Unexpected error while processing master-display from {video_stream}")
                else:
                    if master_display:
                        app.fastflix.current_video.hdr10_streams.append(
                            Box(index=video_stream.index, master_display=master_display, cll=cll)
                        )
                        continue

            result = execute(
                [
                    f"{app.fastflix.config.ffprobe}",
                    "-loglevel",
                    "panic",
                    "-select_streams",
                    f"{video_stream.index}",
                    "-print_format",
                    "json",
                    "-show_frames",
                    "-read_intervals",
                    "%+#1",
                    "-show_entries",
                    "frame=color_space,color_primaries,color_transfer,side_data_list,pix_fmt",
                    clean_file_string(app.fastflix.current_video.source),
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
                continue
            if "frames" not in data or not len(data.frames):
                continue
            data = data.frames[0]
            if not data.get("side_data_list"):
                continue

            try:
                master_display, cll = convert_mastering_display(data)
            except FlixError as err:
                logger.error(str(err))
            except Exception:
                logger.exception(f"Unexpected error while processing master-display from {streams.video[0]}")
            else:
                if master_display:
                    app.fastflix.current_video.hdr10_streams.append(
                        Box(index=video_stream.index, master_display=master_display, cll=cll)
                    )


def get_hdr10_parser_version(config: Config) -> version:
    global HDR10_parser_version
    if HDR10_parser_version:
        return HDR10_parser_version
    HDR10_parser_version_output = check_output([str(config.hdr10plus_parser), "--version"], encoding="utf-8")

    _, version_string = HDR10_parser_version_output.rsplit(sep=" ", maxsplit=1)
    HDR10_parser_version = version.parse(version_string)
    logger.debug(f"Using HDR10 parser version {str(HDR10_parser_version).strip()}")
    return HDR10_parser_version


def detect_hdr10_plus(app: FastFlixApp, config: Config, **_):
    if not config.hdr10plus_parser or not config.hdr10plus_parser.exists():
        return

    hdr10plus_streams = []

    parser_version = get_hdr10_parser_version(config)

    for stream in app.fastflix.current_video.streams.video:
        logger.debug(f"Checking for hdr10+ in stream {stream.index}")
        process = Popen(
            [
                str(config.ffmpeg),
                "-y",
                "-i",
                clean_file_string(app.fastflix.current_video.source),
                "-map",
                f"0:{stream.index}",
                "-loglevel",
                "panic",
                "-c:v",
                "copy",
                "-bsf:v",
                "hevc_mp4toannexb",
                "-f",
                "hevc",
                "-",
            ],
            stdout=PIPE,
            stderr=PIPE,
            stdin=PIPE,  # FFmpeg can try to read stdin and wrecks havoc
        )

        hdr10_parser_command = [str(config.hdr10plus_parser), "--verify", "-"]
        if parser_version >= version.parse("1.0.0"):
            hdr10_parser_command.insert(-1, "extract")

        process_two = Popen(
            hdr10_parser_command,
            stdout=PIPE,
            stderr=PIPE,
            stdin=process.stdout,
            encoding="utf-8",
        )

        try:
            stdout, stderr = process_two.communicate()
        except Exception:
            logger.exception(f"Unexpected error while trying to detect HDR10+ metadata in stream {stream.index}")
        else:
            if "Dynamic HDR10+ metadata detected." in stdout:
                hdr10plus_streams.append(stream.index)

    if hdr10plus_streams:
        app.fastflix.current_video.hdr10_plus = hdr10plus_streams
