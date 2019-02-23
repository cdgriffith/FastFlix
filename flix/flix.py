from subprocess import run, PIPE
import logging
import os
from pathlib import Path

from box import Box, BoxError

__all__ = ['FlixError', 'ff_version', 'Flix']

here = os.path.abspath(os.path.dirname(__file__))

logger = logging.getLogger('flix')


class FlixError(Exception):
    """This flix won't fly"""


def ff_version(ff, throw=True):
    res = Flix.execute(f'"{ff}" -version')
    if res.returncode != 0:
        if throw:
            raise FlixError(f'"{ff}" file not found')
        else:
            return None
    return res.stdout.decode("utf-8").split(" ", 4)[2]


class Flix:

    def __init__(self, ffmpeg='ffmpeg', ffprobe='ffprobe', svt_av1='SvtAv1EncApp'):
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe
        self.av1 = svt_av1
        ff_version(self.ffmpeg)
        ff_version(self.ffprobe)

    def probe(self, file):
        command = f'"{self.ffprobe}" -v quiet -print_format json -show_format -show_streams "{file}"'
        logger.debug(f'running probe command: {command}')
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
        for line in output.split('\n'):
            if line.startswith(line_denote):
                config = [x[9:].strip() for x in line[len(line_denote):].split(" ")]
        return config

    def parse(self, file):
        data = self.probe(file)
        if 'streams' not in data:
            raise FlixError('Not a video file')
        streams = Box({'video': [],
                       'audio': [],
                       'subtitle': [],
                       'attachment': [],
                       'data': []})

        for track in data.streams:
            if track.codec_type in streams:
                streams[track.codec_type].append(track)
            else:
                logger.error(f'Unknown codec: {track.codec_type}')
        return streams, data.format

    def generate_x265_command(self, source, output, video_track, audio_track=None, additional_tracks=(),
                              start_time=0, duration=None, crf=20, preset="medium", disable_hdr=False, scale_width=None,
                              scale_height=None, keep_subtitles=False, crop=None):
        start = ''
        if duration:
            start = f'-ss {start_time} -t {duration}'

        maps = ""
        for track in additional_tracks:
            maps += f" -map 0:{track} "

        filter_list = []

        if disable_hdr:
            filter_list.append('zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,'
                               'zscale=t=bt709:m=bt709:r=tv,format=yuv420p')

        if scale_width:
            filter_list.append(f'scale={scale_width}:-1')
        elif scale_height:
            filter_list.append(f'scale=-1:{scale_height}')

        if crop:
            filter_list.append(f'crop={crop}')

        filters = ",".join(filter_list)

        return (f'"{self.ffmpeg}" -loglevel fatal {start} -i "{source}" '
                f'-c:v libx265 -preset {preset} -x265-params log-level=error:crf={crf} -pix_fmt yuv420p '
                f'{"-map_metadata -1 -write_tmcd 0 -shortest" if start else ""} {f"-vf {filters}" if filters else ""} '
                f'-map 0:{video_track} {"-an" if audio_track is None else f"-map 0:{audio_track}"} {maps} '
                f'{"-map 0:s" if keep_subtitles else "-sn"} '
                # -filter_complex "[0:v:0][0:3]overlay"
                f' -y "{output}"')

    def generate_av1_command(self, source, output, video_track, audio_track=None, additional_tracks=(),
                             start_time=0, duration=None, crf=20, disable_hdr=False, scale_width=None,
                             scale_height=None, keep_subtitles=False, crop=None):
        start = ''
        if start_time:
            start += '-ss {start_time}'
        if duration:
            start += f' -t {duration} -write_tmcd 0'

        maps = ""
        for track in additional_tracks:
            maps += f" -map 0:{track} "

        filter_list = []

        if disable_hdr:
            filter_list.append('zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,'
                               'zscale=t=bt709:m=bt709:r=tv,format=yuv420p')

        if scale_width:
            filter_list.append(f'scale={scale_width}:-1')
        elif scale_height:
            filter_list.append(f'scale=-1:{scale_height}')

        if crop:
            filter_list.append(f'crop={crop}')

        filters = ",".join(filter_list)

        return (f'"{self.ffmpeg}" -loglevel fatal -i "{source}" {start} '
                f'-c:v libaom-av1 -b:v 0 -strict experimental -crf {crf} -pix_fmt yuv420p '
                f'{"-map_metadata -1" if start else ""} {f"-vf {filters}" if filters else ""} '
                f'-map 0:{video_track} {"-an" if audio_track is None else f"-map 0:{audio_track}"} {maps} '
                f'{"-map 0:s" if keep_subtitles else "-sn"} '
                f' -y "{output}"')

    def generate_thumbnail_command(self, source, output, video_track, start_time=0, disable_hdr=False,
                                   crop=None):
        start = ''
        if start_time:
            start = f'-ss {start_time}'

        filter_list = []

        if disable_hdr:
            filter_list.append('zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,'
                               'zscale=t=bt709:m=bt709:r=tv,format=yuv420p')

        if crop:
            filter_list.append(f'crop={crop}')

        filters = ",".join(filter_list) + "," if filter_list else ""

        return (f'"{self.ffmpeg}" {start} -loglevel error -i "{source}" '
                f" -vf {filters}scale=min(600\\,iw):-1 "
                f'-map 0:{video_track} -an -y '
                f'-vframes 1 "{output}"')

    @staticmethod
    def execute(command):
        logger.debug(f"running command: {command}")
        return run(command, stdout=PIPE, stderr=PIPE, stdin=PIPE, shell=True)

    def video_split_command(self, source, video_track=0, start_time=0,
                            duration=None, build_dir=".", segment_size=60):
        start = ''
        if start_time:
            start += f'-ss {start_time}'
        if duration:
            start += f' -t {duration}'
        src = Path(source)
        out = Path(build_dir, f"%04d{src.suffix}")

        return (f'"{self.ffmpeg}" -loglevel fatal {start} -i "{source}" '
                f'{"-map_metadata -1" if start else ""} -map 0:{video_track} -c copy '
                f'-f segment -segment_time {segment_size} -an -sn -dn "{out}"')

    def yuv_command(self, source, output, bit_depth=8, crop=None):
        assert output.endswith('yuv')

        return (f'"{self.ffmpeg}" -loglevel fatal -i "{source}" -c:v rawvideo '
                f'-pix_fmt {"yuv420p10le" if bit_depth == 10 else "yuv420p"}'
                f' {f"-vf crop={crop}" if crop else ""} "{output}"')

    def svt_av1_command(self, source, output, height, width, fps_num, fps_denom, crf=30, mode=3, bit_depth=8):
        if not self.av1:
            raise FlixError("AV1 not defined")
        intra_period = 1
        for i in range(1, 31):
            intra_period = (i * 8) - 1
            if (intra_period + 8) > (fps_num / fps_denom):
                break
        # currently broke  -fps-num {fps_num} -fps-denom {fps_denom}

        logger.debug(f'setting intra-period to {intra_period} based of fps {float(fps_num / fps_denom):.2f}')
        return (f'"{self.av1}" -intra-period {intra_period} -enc-mode {mode} -bit-depth {bit_depth} '
                f'-w {width} -h {height} -fps {round(fps_num/fps_denom)} '
                f'-q {crf} -i "{source}" -b "{output}"')

    def combine_command(self, videos, output, build_dir="."):
        import uuid
        file_list = os.path.abspath(os.path.join(build_dir, uuid.uuid4().hex))
        with open(file_list, 'w') as f:
            f.write("\n".join(['file {}'.format(video.replace("\\", "\\\\")) for video in videos]))
        return f'"{self.ffmpeg}" -safe 0 -f concat -i "{file_list}" -c copy "{output}"'

    def extract_audio_command(self, video, start_time, duration, output, audio_track=0,
                              audio_format="adts", convert=False):
        start = ''
        if start_time:
            start += f'-ss {start_time}'
        if duration:
            start += f' -t {duration}'

        options = f"-acodec copy -f {audio_format}" if not convert else f"-acodec libvorbis"

        return (f'"{self.ffmpeg}" {start} -i "{video}" '
                f'-vn {options} -map 0:{audio_track} "{output}"')

    def add_audio_command(self, video_source, audio_source, output, video_track=0, audio_track=0):
        return (f'"{self.ffmpeg}" -i "{video_source}" -i "{audio_source}" '
                f'-c copy -map 0:{video_track} -map 1:{audio_track} -shortest "{output}"')
