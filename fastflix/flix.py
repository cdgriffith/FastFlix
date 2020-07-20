# -*- coding: utf-8 -*-
from subprocess import run, PIPE, Popen, STDOUT
import logging
import os
from pathlib import Path

from box import Box, BoxError, BoxList

__all__ = ["FlixError", "ff_version", "Flix", "svt_av1_version"]

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


def svt_av1_version(sv1_av1):
    """
    SVT AV1 Currently does not have a version associated with it's build so can only check for existence

    :param sv1_av1: Path to executable
    :return: True if SVT-AV1 else False
    """
    res = Flix.execute(f'"{sv1_av1}" -help')
    if res.returncode != 0:
        logger.warning(f"{sv1_av1} errored while checking version")
        return False
    try:
        lines = res.stdout.decode("utf-8").split("\n")
    except (ValueError, AttributeError):
        logger.warning(f"{sv1_av1} errored while decoding output")
        return False
    if len(lines) < 2:
        logger.warning(f"{sv1_av1} did not have enough output to check, must not be right")
        return False
    if lines[1].startswith("SVT-AV1"):
        return True
    logger.warning(f"{sv1_av1} not a SVT-AV1 file")
    return False


class Flix:
    def __init__(self, ffmpeg="ffmpeg", ffprobe="ffprobe", svt_av1="SvtAv1EncApp"):
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe
        self.av1 = svt_av1

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
        output = self.execute(f'"{self.ffmpeg}" -version').stdout.decode("utf-8")
        config = []
        line_denote = "configuration: "
        for line in output.split("\n"):
            if line.startswith(line_denote):
                config = [x[9:].strip() for x in line[len(line_denote) :].split(" ") if x.startswith("--enable")]
        return config

    def parse(self, file):
        data = self.probe(file)
        if "streams" not in data:
            raise FlixError("Not a video file")
        streams = Box({"video": [], "audio": [], "subtitle": [], "attachment": [], "data": []})

        for track in data.streams:
            if track.codec_type in streams:
                streams[track.codec_type].append(track)
            else:
                logger.error(f"Unknown codec: {track.codec_type}")
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

    def generate_pallet_command(self, source, output, filters, video_track, start_time=0, duration=None):
        start = ""
        if duration:
            start = f"-ss {start_time} -t {duration}"

        return (
            f'"{self.ffmpeg}" {start} -i "{source}" -map 0:{video_track} '
            f'-vf "{f"{filters}," if filters else ""}palettegen" -y "{output}"'
        )

    def generate_gif_command(
        self,
        source,
        output,
        pallet_file,
        video_track,
        additional_tracks=(),
        start_time=0,
        duration=None,
        filters=None,
        fps=15,
        dither="sierra2_4a",
    ):
        start = ""
        if duration:
            start = f"-ss {start_time} -t {duration}"

        maps = ""
        for track in additional_tracks:
            maps += f" -map 0:{track} "

        gif_filters = f"fps={fps:.2f}"
        if filters:
            gif_filters += f",{filters}"

        return (
            f'"{self.ffmpeg}" {start} -i "{source}" -i "{pallet_file}" -map 0:{video_track} '
            f'-lavfi "{gif_filters} [x]; [x][1:v] paletteuse=dither={dither}" -y "{output}" '
        )

    def generate_x265_command(
        self,
        source,
        output,
        video_track,
        audio_track=None,
        additional_tracks=(),
        start_time=0,
        duration=None,
        crf=20,
        preset="medium",
        disable_hdr=False,
        scale_width=None,
        scale_height=None,
        keep_subtitles=False,
        crop=None,
        scale=None,
    ):
        start = ""
        if duration:
            start = f"-ss {start_time} -t {duration}"

        maps = ""
        for track in additional_tracks:
            maps += f" -map 0:{track} "

        filter_list = []

        if disable_hdr:
            filter_list.append(
                "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
                "zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
            )

        if scale:
            filter_list.append(f"scale={scale}")
        elif scale_width:
            filter_list.append(f"scale={scale_width}:-1")
        elif scale_height:
            filter_list.append(f"scale=-1:{scale_height}")

        if crop:
            filter_list.append(f"crop={crop}")

        filters = ",".join(filter_list)

        return (
            f'"{self.ffmpeg}" -loglevel error {start} -i "{source}" '
            f"-c:v libx265 -preset {preset} -x265-params log-level=error:crf={crf} -pix_fmt yuv420p "
            f'{"-map_metadata -1 -write_tmcd 0 -shortest" if start else ""} {f"-vf {filters}" if filters else ""} '
            f'-map 0:{video_track} {"-an" if audio_track is None else f"-map 0:{audio_track}"} {maps} '
            f'{"-map 0:s" if keep_subtitles else "-sn"} '
            # -filter_complex "[0:v:0][0:3]overlay"
            f' -y "{output}"'
        )

    def generate_av1_command(
        self,
        source,
        output,
        video_track,
        audio_track=None,
        additional_tracks=(),
        start_time=0,
        duration=None,
        crf=20,
        disable_hdr=False,
        scale_width=None,
        scale_height=None,
        keep_subtitles=False,
        crop=None,
    ):
        start = ""
        if start_time:
            start += "-ss {start_time}"
        if duration:
            start += f" -t {duration} -write_tmcd 0"

        maps = ""
        for track in additional_tracks:
            maps += f" -map 0:{track} "

        filter_list = []

        if disable_hdr:
            filter_list.append(
                "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
                "zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
            )

        if scale_width:
            filter_list.append(f"scale={scale_width}:-1")
        elif scale_height:
            filter_list.append(f"scale=-1:{scale_height}")

        if crop:
            filter_list.append(f"crop={crop}")

        filters = ",".join(filter_list)

        return (
            f'"{self.ffmpeg}" -loglevel error -i "{source}" {start} '
            f"-c:v libaom-av1 -b:v 0 -strict experimental -crf {crf} -pix_fmt yuv420p "
            f'{"-map_metadata -1" if start else ""} {f"-vf {filters}" if filters else ""} '
            f'-map 0:{video_track} {"-an" if audio_track is None else f"-map 0:{audio_track}"} {maps} '
            f'{"-map 0:s" if keep_subtitles else "-sn"} '
            f' -y "{output}"'
        )

    def generate_thumbnail_command(self, source, output, video_track, start_time=0, filters=None):
        start = ""
        if start_time:
            start = f"-ss {start_time}"
        return (
            f'"{self.ffmpeg}" {start} -loglevel error -i "{source}" '
            f' -vf {filters + "," if filters else ""}scale="min(320\\,iw):-1" '
            f"-map 0:{video_track} -an -y "
            f'-vframes 1 "{output}"'
        )

    @staticmethod
    def execute(command):
        logger.debug(f"running command: {command}")
        return run(command, stdout=PIPE, stderr=PIPE, stdin=PIPE, shell=True)

    def video_split_command(self, source, video_track=0, start_time=0, duration=None, build_dir=".", segment_size=60):
        start = ""
        if start_time:
            start += f"-ss {start_time}"
        if duration:
            start += f" -t {duration}"
        src = Path(source)
        out = Path(build_dir, f"%04d{src.suffix}")

        return (
            f'"{self.ffmpeg}" -loglevel error {start} -i "{source}" '
            f'{"-map_metadata -1" if start else ""} -map 0:{video_track} -c copy -sc_threshold 0 '
            f'-reset_timestamps 1 -f segment -segment_time {segment_size} -an -sn -dn "{out}"'
        )

    def yuv_command(self, source, output, bit_depth=8, crop=None, scale=None):
        assert str(output).endswith(("yuv", "y4m"))

        filter_list = []
        if crop:
            filter_list.append(f"crop={crop}")
        if scale:
            filter_list.append(f"scale={scale}")

        filters = ",".join(filter_list) if filter_list else ""

        return (
            f'"{self.ffmpeg}" -loglevel error -i "{source}" -c:v rawvideo '
            f'-pix_fmt {"yuv420p10le" if bit_depth == 10 else "yuv420p"}'
            f' {f"-vf {filters}" if filters else ""} "{output}"'
        )

    def svt_av1_command(self, source, output, height, width, fps_num, fps_denom, crf=30, mode=3, bit_depth=8):
        if not self.av1:
            raise FlixError("AV1 not defined")
        intra_period = 1
        for i in range(1, 31):
            intra_period = (i * 8) - 1
            if (intra_period + 8) > (fps_num / fps_denom):
                break
        logger.debug(f"setting intra-period to {intra_period} based of fps {float(fps_num / fps_denom):.2f}")
        return (
            f'"{self.av1}" -intra-period {intra_period} -enc-mode {mode} -bit-depth {bit_depth} '
            f"-w {width} -h {height} -fps-num {fps_num} -fps-denom {fps_denom} "
            f'-q {crf} -i "{source}" -b "{output}"'
        )

    def combine_command(self, videos, output, build_dir="."):
        import uuid

        file_list = os.path.abspath(os.path.join(build_dir, uuid.uuid4().hex))
        with open(file_list, "w") as f:
            f.write("\n".join(["file {}".format(str(video).replace("\\", "\\\\")) for video in videos]))
        return f'"{self.ffmpeg}" -safe 0 -f concat -i "{file_list}" -reset_timestamps 1 -c copy "{output}"'

    def extract_audio_command(
        self, video, start_time, duration, output, audio_track=0, audio_format="adts", convert=False
    ):
        start = ""
        if start_time:
            start += f"-ss {start_time}"
        if duration:
            start += f" -t {duration}"

        options = f"-acodec copy -f {audio_format}" if not convert else f"-acodec libvorbis"

        return f'"{self.ffmpeg}" {start} -i "{video}" ' f'-vn {options} -map 0:{audio_track} "{output}"'

    def add_audio_command(self, video_source, audio_source, output, video_track=0, audio_track=0):
        # -shortest ?
        # https://videoblerg.wordpress.com/2017/11/10/ffmpeg-and-how-to-use-it-wrong/
        return (
            f'"{self.ffmpeg}" -i "{video_source}" -i "{audio_source}" '
            f'-c copy -map 0:{video_track} -af "aresample=async=1:min_hard_comp=0.100000:first_pts=0" '
            f'-map 1:{audio_track} "{output}"'
        )

    def get_audio_encoders(self):
        cmd = Popen(
            f'"{self.ffmpeg}" -hide_banner -encoders', shell=True, stderr=STDOUT, stdout=PIPE, universal_newlines=True
        )
        encoders = []
        start_line = " ------"
        started = False
        for line in cmd.stdout:
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

        result = run(command, shell=True, stdout=PIPE, stderr=PIPE)
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

        master_display = None
        cll = None

        def s(a, v):
            return int(a.get(v, "0").split("/")[0])

        for item in data.get("side_data_list", BoxList(default_box=True)):
            if item.side_data_type == "Mastering display metadata":
                master_display = Box(
                    red=f"({s(item, 'red_x')},{s(item, 'red_y')})",
                    green=f"({s(item, 'green_x')},{s(item, 'green_y')})",
                    blue=f"({s(item, 'blue_x')},{s(item, 'blue_y')})",
                    white=f"({s(item, 'white_point_x')},{s(item, 'white_point_y')})",
                    luminance=f"({s(item, 'max_luminance')},{s(item, 'min_luminance')})",
                )
            if item.side_data_type == "Content light level metadata":
                cll = f"({item.max_content},{item.max_average})"

        return Box(
            pix_fmt=data.pix_fmt,
            color_space=data.color_space,
            color_primaries=data.color_primaries,
            color_transfer=data.color_transfer,
            master_display=master_display,
            cll=cll,
        )
