from subprocess import run, PIPE
import logging
import os

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

    def __init__(self, ffmpeg='ffmpeg', ffprobe='ffprobe'):
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe
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

    def parse(self, file):
        data = self.probe(file)
        if 'streams' not in data:
            raise FlixError('Not a video file')
        streams = {'video': [],
                   'audio': [],
                   'subtitle': [],
                   'attachment': [],
                   'data': []}

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
            start = f'-ss {start_time} -t {duration} -write_tmcd 0'

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
                f'-c:v libx265 -preset {preset} -x265-params log-level=error:crf={crf} -pix_fmt yuv420p '
                f'{"-map_metadata -1" if start else ""} {f"-vf {filters}" if filters else ""} '
                f'-map 0:{video_track} {"-an" if audio_track is None else f"-map 0:{audio_track}"} {maps} '
                f'{"-map 0:s" if keep_subtitles else "-sn"} '  
                #-filter_complex "[0:v:0][0:3]overlay"
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

        return (f'"{self.ffmpeg}" {start} -loglevel error -i "{source}"  '
                f" -vf {filters}scale=min(600\,iw):-1 "
                f'-map 0:{video_track} -an -y '
                f'-vframes 1 "{output}"')

    @staticmethod
    def execute(command):
        return run(command, stdout=PIPE, stderr=PIPE, stdin=PIPE, shell=True)


# Subtitle info
"""
Bitmap:


Text:
codec_name=ass
codec_name=mov_text

TAG:language=eng
TAG:title=English Signs/Songs

"""