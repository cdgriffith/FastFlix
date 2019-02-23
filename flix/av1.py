#!/usr/bin/env python
import os
import tempfile
from pathlib import Path
import time
import shutil
import logging

from box import Box

from flix import FlixError

logger = logging.getLogger('flix')


def convert(flix, source, output, build_dir=tempfile.gettempdir(), start_time='0',
            duration=None, save_segments=False, auto_crop=True, save_yuv=False, overwrite=False, crop=None,
            crf=30, mode=3, video_track=None, audio_track=None, segment_size=60):
    st = time.time()
    file = Path(source)
    if Path(output).exists() and not overwrite:
        raise FlixError(f'File {output} already exists')
    m = Path(build_dir)
    if not m.exists():
        m.mkdir(parents=True)
    outer_temp_dir = tempfile.mkdtemp(prefix='fast_flix_', dir=build_dir)
    parts_temp_dir = tempfile.mkdtemp(prefix="org_parts_", dir=outer_temp_dir)
    yuv_temp_dir = tempfile.mkdtemp(prefix="yuv_", dir=outer_temp_dir)
    av1_parts = tempfile.mkdtemp(prefix="av1_", dir=outer_temp_dir)
    info, fmt = flix.parse(file)
    if not video_track:
        video_track = info.video[0].index
    if not audio_track:
        audio_track = info.audio[0].index
    height = int(info.video[0].height)
    width = int(info.video[0].width)
    assert height <= 2160
    assert width <= 4096
    fps_num, fps_denom = [int(x) for x in info.video[0].r_frame_rate.split("/")]
    bit_depth = 10 if info.video[0].pix_fmt == 'yuv420p10le' else 8
    if crop:
        crop_check = crop.split(":")
        try:
            assert crop_check[0] % 8 == 0
            assert crop_check[1] % 8 == 0
        except AssertionError:
            raise FlixError("CROP BAD: Video height and width must be divisible by 8")
    else:
        crop_height = height % 8
        crop_width = width % 8
        crop = None
        if crop_height or crop_width:
            if not auto_crop:
                raise FlixError('CROP BAD: Video height and width must be divisible by 8')
            width = width - crop_width
            height = height - crop_height
            crop = f'{width}:{height}:0:0'
            logger.info(f'applying crop, new resolution of {width}x{height}')

    audio_codecs = Box({
        'ac3': {
            'format': 'ac3',
            'suffix': 'ac3',
            'convert': False
        },
        'mp3': {
            'format': 'mp3',
            'suffix': 'mp3',
            'convert': False
        },
        'opus': {
            'format': 'opus',
            'suffix': 'ogg',
            'convert': False
        },
        'pcm_s16le': {
            'format': 'opus',
            'suffix': 'ogg',
            'convert': True
        },
        'default': {
            'format': 'opus',
            'suffix': 'ogg',
            'convert': True
        },
    })

    cx = audio_codecs['default']
    if info.audio[0].codec_name in audio_codecs:
        cx = audio_codecs[info.audio[0].codec_name]
    else:
        logger.warning(f'unknown audio codec {info.audio[0].codec_name} converting to ogg')

    aud_out = Path(outer_temp_dir, f"audio.{cx.suffix}")

    aud = flix.extract_audio_command(file, start_time, duration=duration, output=str(aud_out), audio_track=audio_track,
                                     audio_format=cx.format, convert=cx.convert)
    flix.execute(aud).check_returncode()

    cmd1 = flix.video_split_command(file, start_time=start_time, duration=duration, segment_size=segment_size,
                                    build_dir=parts_temp_dir, video_track=video_track)
    flix.execute(cmd1).check_returncode()

    yuv_list = [(int(x.stem), x, Path(yuv_temp_dir, f"{x.stem}.yuv")) for x in Path(parts_temp_dir).iterdir()]
    video_list = []
    logger.info(f'File segments generated: {len(yuv_list)}')

    for num, src, yuv_output in sorted(yuv_list, key=lambda x: x[0]):
        logger.debug(f'Encoding segment {num + 1} of {len(yuv_list)}')
        yuv_cmd = flix.yuv_command(str(src), str(yuv_output), crop=crop)
        flix.execute(yuv_cmd).check_returncode()
        out_vid = Path(av1_parts, f'{num}.ivf')
        video_list.append(str(out_vid))
        svt_av1_cmd = flix.svt_av1_command(str(yuv_output),
                                           str(out_vid),
                                           height, width,
                                           fps_num=fps_num, fps_denom=fps_denom,
                                           bit_depth=bit_depth,
                                           crf=crf,
                                           mode=mode)
        flix.execute(svt_av1_cmd).check_returncode()
        if not save_yuv:
            os.remove(yuv_output)
        if not save_segments:
            src.unlink()

    main_bin = Path(outer_temp_dir, "no_audio.mkv")
    main_file = Path(output)
    cmb = flix.combine_command(video_list, str(main_bin), build_dir=outer_temp_dir)
    flix.execute(cmb).check_returncode()

    combine = flix.add_audio_command(main_bin,
                                     aud_out,
                                     main_file)
    flix.execute(combine).check_returncode()
    if not save_segments:
        logger.debug(f'cleaning up temp files for {outer_temp_dir}')
        try:
            shutil.rmtree(parts_temp_dir, ignore_errors=True)
            shutil.rmtree(av1_parts, ignore_errors=True)
            aud_out.unlink()
            main_bin.unlink()
        except OSError as err:
            logger.warning(f'Cannot delete all files under {outer_temp_dir}: {err}')
    if not save_yuv:
        try:
            shutil.rmtree(yuv_temp_dir, ignore_errors=True)
        except OSError as err:
            logger.warning(f'Cannot delete all files under {yuv_temp_dir}: {err}')
    if not save_yuv and not save_segments:
        # Can just do this, but if anything is still in open state want to clean up what is possible
        try:
            shutil.rmtree(outer_temp_dir, ignore_errors=True)
        except OSError as err:
            logger.warning(f'Cannot delete all files under {outer_temp_dir}: {err}')

    logger.info(f'AV1 encoding took {time.time() - st:.2f} seconds')
    return 0

