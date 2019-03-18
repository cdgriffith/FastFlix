#!/usr/bin/env python

import reusables
from box import Box

from pathlib import Path
import logging
import os
from tempfile import TemporaryDirectory

from flix.builders.helpers import (generate_filters, start_and_input, Loop, Command)
from flix.builders.audio import build as audio_builder

logger = logging.getLogger('flix')


class FlixError(Exception):
    pass

extension = "mkv"


@reusables.log_exception('flix', show_traceback=True)
def build(source, video_track, streams, format_info, mode=7, segment_size=60,
          qp=50, audio_tracks=(), **kwargs):
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
    assert height <= 2160
    assert width <= 4096
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

    start_time = kwargs.get('start_time')
    total_time = kwargs.get("duration", format_info.duration) - start_time

    frames = int(total_time * int(fps_num / fps_denom))

    intra_period = 1
    for i in range(1, 31):
        intra_period = (i * 8) - 1
        if (intra_period + 8) > (fps_num / fps_denom):
            break

    command_1 = Command((f'"{{ffmpeg}}" {f"-ss {start_time}" if start_time else ""} '
                         f'-nostdin -i "{source}" -vframes {frames} -f rawvideo '
                         f'{f"-vf {filters}" if filters else ""} '
                         f'-pix_fmt {"yuv420p" if bit_depth == 8 else "yuv420p10le"} -an pipe: | '
                         f'"{{av1}}" -intra-period {intra_period} -enc-mode {mode} -w {width} -h {height} '
                         f'-bit-depth {bit_depth} -n {frames} -i stdin -q {qp} '
                         f'-fps-num {fps_num} -fps-denom {fps_denom} -b <tempfile.1.ivf>'),
                        ['ffmpeg', 'av1'], False)

    audio = audio_builder(audio_tracks, audio_file_index=1)

    command_3 = Command((f'"{{ffmpeg}}" -i "<tempfile.1.ivf>" -i "{file}" '
                         f'-c:v copy -map 0:{video_track} '
                         f'{audio} "{{output}}"'),
                        ['ffmpeg', 'output'],
                        False)

    # return (command_1, main_loop, command_2, command_3)

    return command_1, command_3

    # OLD WAY
    #
    # command_1 = Command((f'{start_and_input(source, **kwargs)} '
    #                      f'{"-map_metadata -1" if kwargs.get("start_time") else ""} '
    #                      f'-map 0:{video_track} -c copy -sc_threshold 0 '
    #                      f'-reset_timestamps 1 -f segment -segment_time {segment_size} -an -sn -dn '
    #                      f'"{Path(path.origional_parts, f"%04d{file.suffix}")}"'),
    #                     ['ffmpeg'], False,
    #                     name="Semgment movie into smaller files",
    #                     ensure_paths=[build_dir] + list(path.values()))
    #
    # def func(y4m_dir, parts_dir):
    #     return sorted([(int(x.stem), x, Path(y4m_dir, f"{x.stem}.y4m")) for x in Path(parts_dir).iterdir()],
    #                   key=lambda x: x[0])
    #
    # concat_list = Path(build_dir, 'concat_list.txt')
    #
    # loop_command_1 = (f'"{{ffmpeg}}" -i "<loop.1>" '
    #                   f' {f"-vf {filters}" if filters else ""} "<loop.2>"')
    #
    # intra_period = 1
    # for i in range(1, 31):
    #     intra_period = (i * 8) - 1
    #     if (intra_period + 8) > (fps_num / fps_denom):
    #         break
    # logger.debug(f'setting intra-period to {intra_period} based of fps {float(fps_num / fps_denom):.2f}')
    # loop_command_2 = (f'"{{av1}}" -intra-period {intra_period} -enc-mode {mode} -bit-depth {bit_depth} '
    #                   f' -fps-num {fps_num} -fps-denom {fps_denom} '
    #                   f'-q {crf} -i "<loop.2>" -b "{path.av1_parts}{os.sep}<loop.0>.ivf"')
    # loop_command_3 = f"echo file '{path.av1_parts}{os.sep}<loop.0>.ivf'' > {concat_list}"
    #
    # # TODO internal cleanup command
    #
    # main_loop = Loop(condition=lambda: func(path.y4m, path.origional_parts),
    #                  commands=[
    #                      Command(loop_command_1, ['ffmpeg'], False),
    #                      Command(loop_command_2, ['av1'], False),
    #                      Command(loop_command_3, [], False)
    #                  ])
    #
    # no_audio_file = Path(build_dir, "combined.mkv")
    # command_2 = Command(
    #     (f'"{{ffmpeg}}" -safe 0 -f concat -i "{concat_list}" -reset_timestamps 1 -c copy "{no_audio_file}"'),
    #     ['ffmpeg'], False)
    #