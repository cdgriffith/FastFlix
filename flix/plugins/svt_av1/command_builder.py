#!/usr/bin/env python

import reusables

from pathlib import Path
import logging
import os

from plugins.common.helpers import (generate_filters, Loop, Command)
from plugins.common.audio import build_audio

logger = logging.getLogger('flix')


class FlixError(Exception):
    pass


extension = "mkv"


def build_audio(audio_tracks, audio_file_index=0):
    command_list = []
    for track in audio_tracks:
        command_list.append(f'-map {audio_file_index}:{track.index}')
        if track.conversion.codec == 'none':
            command_list.append(f'-c:a:{track.index} copy')
        elif 'conversion' in track:
            command_list.append(f'-c:a:{track.index} {track.conversion.codec} '
                                f'-b:a:{track.index} {track.conversion.bitrate} ')

    return " ".join(command_list)


@reusables.log_exception('flix', show_traceback=True)
def build(source, video_track, streams, start_time, duration, speed=7, segment_size=60,
          qp=25, bitrate=None, audio_tracks=(), **kwargs):
    file = Path(source)

    filters = generate_filters(**kwargs)

    fps_num, fps_denom = [int(x) for x in
                          streams.video[0].get('avg_frame_rate', streams.video[0].r_frame_rate).split("/")]
    bit_depth = 10 if streams.video[0].pix_fmt == 'yuv420p10le' else 8
    crop = kwargs.get("crop")
    scale = kwargs.get("scale")

    if scale:
        width, height = (int(x) for x in scale.split(":"))
    else:
        height = int(streams.video[0].height)
        width = int(streams.video[0].width)
        if crop:
            crop_check = crop.split(":")
            try:
                assert crop_check[0] % 8 == 0
                assert crop_check[1] % 8 == 0
            except AssertionError:
                raise FlixError("CROP BAD: Video height and main_width must be divisible by 8")
        else:
            crop_height = height % 8
            crop_width = width % 8
            if crop_height or crop_width:
                raise FlixError('CROP BAD: Video height and main_width must be divisible by 8')

    assert height <= 2160
    assert width <= 4096

    command_1 = Command((f'{{ffmpeg}} -y '
                         f'-i "{source}" '
                         f'{f"-ss {start_time}" if start_time else ""} '
                         f'{f"-t {duration - start_time}" if duration else ""} '
                         f'{"-map_metadata -1" if kwargs.get("start_time") else ""} '
                         f'-map 0:{video_track} -c copy -sc_threshold 0 '
                         f'-reset_timestamps 1 -f segment -segment_time {segment_size} -an -sn -dn '
                         f'"<tempdir.1>{os.sep}%04d{file.suffix}"'),
                        ['ffmpeg'], False,
                        name="Semgment movie into smaller files",
                        exe='ffmpeg')

    def func(tempfiles, tempdirs):
        return sorted([(int(x.stem), x, Path(tempdirs['3'], f"{x.stem}.yuv")) for x in Path(tempdirs['1']).iterdir()],
                      key=lambda x: x[0])

    loop_command_1 = (f'"{{ffmpeg}}" -y -i "<loop.1>" '
                      f' {f"-vf {filters}" if filters else ""} "<loop.2>"')

    intra_period = 1
    for i in range(1, 31):
        intra_period = (i * 8) - 1
        if (intra_period + 8) > (fps_num / fps_denom):
            break
    logger.debug(f'setting intra-period to {intra_period} based of fps {float(fps_num / fps_denom):.2f}')

    quality = f"-tbr {bitrate}" if bitrate else f"-q {qp}"

    loop_command_2 = (f'"{{av1}}" -intra-period {intra_period} -enc-mode {speed} -bit-depth {bit_depth} '
                      f' -fps-num {fps_num} -fps-denom {fps_denom} -w {width} -h {height} '
                      f'{quality} -i "<loop.2>" -b "<tempdir.2>{os.sep}<loop.0>.ivf"')

    loop_command_3 = f"echo file '<tempdir.2>{os.sep}<loop.0>.ivf' >> <tempfile.5.log>"

    loop_command_4 = 'del /f "<loop.2>"'

    main_loop = Loop(name="Convert segmented input files into AV1 video files",
                     condition=func,
                     dirs=['2', '3'],
                     files=[],
                     commands=[
                         Command(loop_command_1, ['ffmpeg'], False, exe='ffmpeg', name='Convert segment to raw YUV'),
                         Command(loop_command_2, ['av1'], False, name='Convert YUV into AV1 binary IVF files'),
                         Command(loop_command_3, [], False, name='Add new IVF file to ffmpeg concat list'),
                         Command(loop_command_4, [], False, name='Remove large YUV temp file')
                     ])

    if not audio_tracks:
        command_2 = Command(
            f'"{{ffmpeg}}" -y -safe 0 -f concat -i "<tempfile.5.log>" -reset_timestamps 1 -c copy "{{output}}"',
            ['ffmpeg'], False, exe='ffmpeg', name='Wrap IVF binary output into MKV container')
        return command_1, main_loop, command_2

    no_audio_file = '<tempfile.6.mkv>'
    command_2 = Command(
        f'"{{ffmpeg}}" -y -safe 0 -f concat -i "<tempfile.5.log>" -reset_timestamps 1 -c copy "{no_audio_file}"',
        ['ffmpeg'], False, exe='ffmpeg')

    audio = build_audio(audio_tracks, audio_file_index=0)

    audio_file = 'tempfile.7.mkv'
    command_audio = Command((f'"{{ffmpeg}}" -y '
                             f'-i "{source}" '
                             f'{f"-ss {start_time}" if start_time else ""} '
                             f'{f"-t {duration - start_time}" if duration else ""} '
                             f'{audio} "{audio_file}"'
                             ), ['ffmpeg'], False, exe='ffmpeg',
                            name='Split audio at proper time offsets into new file')

    command_3 = Command((f'"{{ffmpeg}}" -y '
                         f'-i "{no_audio_file}" -i "{audio_file}" '
                         f'{"-map_metadata -1" if start_time or duration else ""} '
                         f'-c copy -map 0:v -map 1:a '  # shortest  
                         # -af "aresample=async=1:min_hard_comp=0.100000:first_pts=0"
                         f'"{{output}}"'),
                        ['ffmpeg', 'output'],
                        False, exe='ffmpeg',
                        name='Combine audio and video files into MKV container')

    return command_1, main_loop, command_2, command_audio, command_3
