# -*- coding: utf-8 -*-
import logging
import os
from multiprocessing.pool import Pool
from subprocess import PIPE, STDOUT, run, TimeoutExpired
import shlex

from box import Box, BoxError

__all__ = ["FlixError", "ff_version", "Flix", "guess_bit_depth"]

here = os.path.abspath(os.path.dirname(__file__))

logger = logging.getLogger("fastflix")


class FlixError(Exception):
    """This fastflix won't fly"""


def ff_version(ff, throw=True):
    res = Flix.execute(f'"{ff}" -version')
    if res.returncode != 0:
        if throw:
            raise FlixError(f'"{ff}" file not found')
        else:
            return False
    return res.stdout.decode("utf-8").split(" ", 4)[2]


def guess_bit_depth(pix_fmt, color_primaries):
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

    ten = ("yuv420p10le", "yuv422p10le", "yuv444p10le", "gbrp10le", "gray10le")

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


class Flix:
    def __init__(self, ffmpeg="ffmpeg", ffprobe="ffprobe"):
        self.update(ffmpeg, ffprobe)

    def update(self, ffmpeg, ffprobe):
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe
        self.config, self.filters, self.ffmpeg_version = self.ffmpeg_configuration()
        self.ffprobe_version = ff_version(self.ffprobe, True)

    def probe(self, file):
        command = f'"{self.ffprobe}" -v quiet -print_format json -show_format -show_streams "{file}"'
        logger.debug(f"running probe command: {command}")
        result = self.execute(command)
        try:
            return Box.from_json(result.stdout.decode("utf-8"))
        except BoxError:
            logger.error(f"Could not decode output: {result.stderr}")
            raise FlixError(result.stderr)

    def ffmpeg_configuration(self):
        res = self.execute(f'"{self.ffmpeg}" -version')
        if res.returncode != 0:
            raise FlixError(f'"{self.ffmpeg}" file not found')
        output = res.stdout.decode("utf-8")
        config = []
        try:
            version = output.split(" ", 4)[2]
        except (ValueError, IndexError):
            raise FlixError(f'Cannot parse version of ffmpeg from "{output}"')
        line_denote = "configuration: "
        for line in output.split("\n"):
            if line.startswith(line_denote):
                config = [x[9:].strip() for x in line[len(line_denote) :].split(" ") if x.startswith("--enable")]

        filter_output = self.execute(f'"{self.ffmpeg}" -hide_banner -filters').stdout.decode("utf-8")

        filters = []
        for i, line in enumerate(filter_output.split("\n")):
            if i < 8 or not line.strip():
                continue
            filters.append(line.strip().split(" ")[1])

        return config, filters, version

    def extract_attachment(self, args):
        file, stream, work_dir, file_name = args
        try:
            self.execute(
                f'"{self.ffmpeg}" -y -i "{file}" -map 0:{stream} -c copy "{file_name}"', work_dir=work_dir, timeout=5
            )
        except TimeoutExpired:
            logger.warning(f"WARNING Timeout while extracting cover file {file_name}")

    def parse(self, file, temp_dir=None, extract_covers=False):
        data = self.probe(file)
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
                pool.map(self.extract_attachment, covers)

        for stream in streams.video:
            if "bits_per_raw_sample" in stream:
                stream.bit_depth = int(stream.bits_per_raw_sample)
            else:
                stream.bit_depth = guess_bit_depth(stream.pix_fmt, stream.get("color_primaries"))
        return streams, data.format

    @staticmethod
    def generate_filters(
        disable_hdr=False, scale_width=None, scale_height=None, crop=None, scale=None, scale_filter="lanczos"
    ):
        filter_list = []
        if crop:
            filter_list.append(f"crop={crop}")
        if scale:
            filter_list.append(f"scale={scale}:flags={scale_filter}")
        elif scale_width:
            filter_list.append(f"scale={scale_width}:-1:flags={scale_filter}")
        elif scale_height:
            filter_list.append(f"scale=-1:{scale_height}:flags={scale_filter}")

        if disable_hdr:
            filter_list.append(
                "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
                "zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
            )

        return ",".join(filter_list)

    def generate_thumbnail_command(self, source, output, filters, start_time=0, input_track=0):
        start = ""
        if start_time:
            start = f"-ss {start_time}"
        return (
            f'"{self.ffmpeg}" {start} -loglevel error -i "{source}" '
            f" {filters} -an -y -map_metadata -1 -map 0:{input_track} "
            f'-vframes 1 "{output}" '
        )

    def get_auto_crop(self, source, video_width, video_height, start_time, input_track):
        output = self.execute(
            f'"{self.ffmpeg}" -ss {start_time} -hide_banner -i "{source}" '
            f"-map 0:{input_track} -vf cropdetect -vframes 10 -f null - "
        )

        width, height, x_crop, y_crop = None, None, None, None
        for line in output.stderr.decode("utf-8").splitlines():
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

    @staticmethod
    def execute(command, work_dir=None, timeout=None):
        logger.debug(f"running command: {command}")
        return run(shlex.split(command), stdout=PIPE, stderr=PIPE, stdin=PIPE, cwd=work_dir, timeout=timeout)

    def get_audio_encoders(self):
        cmd = run(
            [f"{self.ffmpeg}", "-hide_banner", "-encoders"],
            stdin=PIPE,
            stdout=PIPE,
            stderr=STDOUT,
            encoding="utf-8",
            universal_newlines=True,
        )
        encoders = []
        start_line = " ------"
        started = False
        for line in cmd.stdout.splitlines():
            if started:
                if line.strip().startswith("A"):
                    encoders.append(line.strip().split(" ")[1])
            elif line.startswith(start_line):
                started = True
        return encoders

    def parse_hdr_details(self, video_source, video_track=0):
        command = (
            f'"{self.ffprobe}" -select_streams v:{video_track} -print_format json -show_frames '
            '-read_intervals "%+#1" '
            '-show_entries "frame=color_space,color_primaries,color_transfer,side_data_list,pix_fmt" '
            f'-i "{video_source}"'
        )

        result = run(command, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        try:
            data = Box.from_json(result.stdout.decode("utf-8"), default_box=True, default_box_attr=None)
        except BoxError:
            # Could not parse details
            logger.error(
                "COULD NOT PARSE FFPROBE HDR METADATA, PLEASE OPEN ISSUE WITH THESE DETAILS:"
                f"\nSTDOUT: {result.stdout.decode('utf-8')}\nSTDERR: {result.stderr.decode('utf-8')}"
            )
            return
        if "frames" not in data or not len(data.frames):
            return
        data = data.frames[0]
        if not data.get("side_data_list"):
            return

        master_display = None
        cll = None

        def s(a, v):
            return int(a.get(v, "0").split("/")[0])

        for item in data["side_data_list"]:
            if item.side_data_type == "Mastering display metadata":
                master_display = Box(
                    red=f"({s(item, 'red_x')},{s(item, 'red_y')})",
                    green=f"({s(item, 'green_x')},{s(item, 'green_y')})",
                    blue=f"({s(item, 'blue_x')},{s(item, 'blue_y')})",
                    white=f"({s(item, 'white_point_x')},{s(item, 'white_point_y')})",
                    luminance=f"({s(item, 'max_luminance')},{s(item, 'min_luminance')})",
                )
            if item.side_data_type == "Content light level metadata":
                cll = f"{item.max_content},{item.max_average}"

        return Box(
            pix_fmt=data.pix_fmt,
            color_space=data.color_space,
            color_primaries=data.color_primaries,
            color_transfer=data.color_transfer,
            master_display=master_display,
            cll=cll,
        )
