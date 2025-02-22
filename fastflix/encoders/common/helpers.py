# -*- coding: utf-8 -*-
import uuid
from pathlib import Path
from typing import Tuple, Union, Optional

import reusables
from pydantic import BaseModel, Field

from fastflix.encoders.common.attachments import build_attachments
from fastflix.encoders.common.audio import build_audio
from fastflix.encoders.common.subtitles import build_subtitle
from fastflix.models.fastflix import FastFlix
from fastflix.shared import clean_file_string, sanitize, quoted_path

null = "/dev/null"
if reusables.win_based:
    null = "NUL"


class Command(BaseModel):
    command: str
    item: str = "command"
    name: str = ""
    exe: str = None
    shell: bool = False
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))


def generate_ffmpeg_start(
    source,
    ffmpeg,
    encoder,
    selected_track,
    ffmpeg_version,
    start_time=0,
    end_time=None,
    pix_fmt="yuv420p10le",
    filters=None,
    max_muxing_queue_size="default",
    fast_seek=True,
    video_title="",
    video_track_title="",
    maxrate=None,
    bufsize=None,
    source_fps: Union[str, None] = None,
    vsync: Union[str, None] = None,
    concat: bool = False,
    enable_opencl: bool = False,
    remove_hdr: bool = True,
    start_extra: str = "",
    **_,
) -> str:
    time_settings = f'{f"-ss {start_time}" if start_time else ""} {f"-to {end_time}" if end_time else ""} '
    time_one = time_settings if fast_seek else ""
    time_two = time_settings if not fast_seek else ""
    incoming_fps = f"-r {source_fps}" if source_fps else ""

    vsync_type = "vsync"
    try:
        if ffmpeg_version.startswith("n") and int(ffmpeg_version[1:].split(".")[0]) >= 5:
            vsync_type = "fps_mode"
    except Exception:
        pass

    vsync_text = f"-{vsync_type} {vsync}" if vsync else ""

    if video_title:
        video_title = video_title.replace('"', '\\"')
    title = f'-metadata title="{video_title}"' if video_title else ""
    source = clean_file_string(source)
    ffmpeg = clean_file_string(ffmpeg)
    if video_track_title:
        video_track_title = video_track_title.replace('"', '\\"')
    track_title = f'-metadata:s:v:0 title="{video_track_title}"'

    return " ".join(
        [
            f'"{ffmpeg}"',
            start_extra,
            ("-init_hw_device opencl:0.0=ocl -filter_hw_device ocl " if enable_opencl and remove_hdr else ""),
            "-y",
            time_one,
            incoming_fps,
            f"{'-f concat -safe 0' if concat else ''}",
            f'-i "{source}"',
            time_two,
            title,
            f"{f'-max_muxing_queue_size {max_muxing_queue_size}' if max_muxing_queue_size != 'default' else ''}",
            f'{f"-map 0:{selected_track}" if not filters else ""}',
            vsync_text,
            f'{filters if filters else ""}',
            f"-c:v {encoder}",
            f"-pix_fmt {pix_fmt}",
            f"{f'-maxrate:v {maxrate}k' if maxrate else ''}",
            f"{f'-bufsize:v {bufsize}k' if bufsize else ''}",
            f"{track_title if video_track_title else ''}",
            " ",  # Leave space after commands
        ]
    )


def rigaya_data(streams, copy_data=False, **_):
    if not copy_data:
        return ""
    datas = []
    for stream in streams:
        if stream["codec_type"] == "data":
            datas.append(str(stream["index"]))
    if not datas:
        return ""
    return f"--data-copy {','.join(datas)}"


def generate_ending(
    audio,
    subtitles,
    cover="",
    output_video: Path = None,
    copy_chapters=True,
    remove_metadata=True,
    null_ending=False,
    output_fps: Union[str, None] = None,
    disable_rotate_metadata=False,
    copy_data=False,
    **_,
):
    ending = (
        f" {'-map_metadata -1' if remove_metadata else '-map_metadata 0'} "
        f"{'-map_chapters 0' if copy_chapters else '-map_chapters -1'} "
        f"{f'-r {output_fps}' if output_fps else ''} "
        f"{audio} {subtitles} {cover} "
        f"{'-map 0:d -c:d copy ' if copy_data else ''}"
    )

    # In case they use a mp4 container, nix the rotation
    if not disable_rotate_metadata and not remove_metadata:
        ending = f"-metadata:s:v rotate=0 {ending}"

    if output_video and not null_ending:
        ending += f'"{clean_file_string(sanitize(output_video))}"'
    else:
        ending += null
    return ending, f"{f'-r {output_fps}' if output_fps else ''} "


def generate_filters(
    selected_track,
    source=None,
    crop: Optional[dict] = None,
    scale=None,
    scale_filter="lanczos",
    remove_hdr=False,
    vaapi: bool = False,
    rotate=0,
    vertical_flip=None,
    horizontal_flip=None,
    burn_in_subtitle_track=None,
    burn_in_subtitle_type=None,
    custom_filters=None,
    start_filters=None,
    raw_filters=False,
    deinterlace=False,
    contrast=None,
    brightness=None,
    saturation=None,
    enable_opencl: bool = False,
    tone_map: str = "hable",
    video_speed: Union[float, int] = 1,
    deblock: Union[str, None] = None,
    deblock_size: int = 4,
    denoise: Union[str, None] = None,
    **_,
):
    filter_list = []
    if start_filters:
        filter_list.append(start_filters)
    if deinterlace:
        filter_list.append(f"yadif")
    if crop:
        filter_list.append(f"crop={crop['width']}:{crop['height']}:{crop['left']}:{crop['top']}")
    if scale:
        if not vaapi:
            filter_list.append(f"scale={scale}:flags={scale_filter},setsar=1:1")
    if rotate:
        if rotate == 1:
            filter_list.append(f"transpose=1")
        if rotate == 2:
            filter_list.append(f"transpose=2,transpose=2")
        if rotate == 3:
            filter_list.append(f"transpose=2")
    if vertical_flip:
        filter_list.append("vflip")
    if horizontal_flip:
        filter_list.append("hflip")
    if video_speed and video_speed != 1:
        filter_list.append(f"setpts={video_speed}*PTS")
    if deblock:
        filter_list.append(f"deblock=filter={deblock}:block={deblock_size}")
    if denoise:
        filter_list.append(denoise)

    eq_filters = []
    if brightness:
        eq_filters.append(f"brightness={brightness}")
    if saturation:
        eq_filters.append(f"saturation={saturation}")
    if contrast:
        eq_filters.append(f"contrast={contrast}")
    if eq_filters:
        eq_filters.insert(0, "eq=eval=frame")
        filter_list.append(":".join(eq_filters))

    if filter_list and vaapi:
        filter_list.insert(0, "hwdownload")
    if vaapi:
        filter_list.append("format=nv12|vaapi,hwupload")

    if remove_hdr:
        if enable_opencl:
            filter_list.append(
                f"format=p010,hwupload,tonemap_opencl=tonemap={tone_map}:desat=0:r=tv:p=bt709:t=bt709:m=bt709:format=nv12,hwdownload,format=nv12"
            )
        elif vaapi:
            filter_list.append(f"tonemap_vaapi=format=nv12:p=bt709:t=bt709:m=bt709")
        else:
            filter_list.append(
                f"zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap={tone_map}:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
            )

    filters = ",".join(filter_list)
    if filters and custom_filters:
        filters = f"{filters},{custom_filters}"
    elif not filters and custom_filters:
        filters = custom_filters

    if burn_in_subtitle_track is not None:
        if burn_in_subtitle_type == "picture":
            if filters:
                # You have to overlay first for it to work when scaled
                filter_complex = f"[0:{selected_track}][0:{burn_in_subtitle_track}]overlay[subbed];[subbed]{filters}[v]"
            else:
                filter_complex = f"[0:{selected_track}][0:{burn_in_subtitle_track}]overlay[v]"
        else:
            filter_complex = f"[0:{selected_track}]{f'{filters},' if filters else ''}subtitles='{quoted_path(clean_file_string(source))}':si={burn_in_subtitle_track}[v]"
    elif filters:
        filter_complex = f"[0:{selected_track}]{filters}[v]"
    else:
        return ""

    if raw_filters:
        return filter_complex
    return f' -filter_complex "{filter_complex}" -map "[v]" '


def generate_all(
    fastflix: FastFlix,
    encoder: str,
    audio: bool = True,
    subs: bool = True,
    disable_filters: bool = False,
    vaapi: bool = False,
    start_extra: str = "",
    **filters_extra,
) -> Tuple[str, str, str]:
    settings = fastflix.current_video.video_settings.video_encoder_settings

    audio = build_audio(fastflix.current_video.audio_tracks) if audio else ""

    subtitles, burn_in_track, burn_in_type = "", None, None
    if subs:
        subtitles, burn_in_track, burn_in_type = build_subtitle(fastflix.current_video.subtitle_tracks)
        if burn_in_type == "text":
            for i, x in enumerate(fastflix.current_video.streams["subtitle"]):
                if x["index"] == burn_in_track:
                    burn_in_track = i
                    break

    attachments = build_attachments(fastflix.current_video.attachment_tracks)

    enable_opencl = fastflix.opencl_support
    if "enable_opencl" in filters_extra:
        enable_opencl = filters_extra.pop("enable_opencl")

    filters = None
    if not disable_filters:
        filter_details = fastflix.current_video.video_settings.model_dump().copy()
        filter_details.update(filters_extra)
        filters = generate_filters(
            source=fastflix.current_video.source,
            burn_in_subtitle_track=burn_in_track,
            burn_in_subtitle_type=burn_in_type,
            scale=fastflix.current_video.scale,
            enable_opencl=enable_opencl,
            vaapi=vaapi,
            **filter_details,
        )

    ending, output_fps = generate_ending(
        audio=audio,
        subtitles=subtitles,
        cover=attachments,
        output_video=fastflix.current_video.video_settings.output_path,
        disable_rotate_metadata=encoder == "copy",
        **fastflix.current_video.video_settings.model_dump(),
    )

    beginning = generate_ffmpeg_start(
        source=fastflix.current_video.source,
        ffmpeg=fastflix.config.ffmpeg,
        encoder=encoder,
        filters=filters,
        concat=fastflix.current_video.concat,
        enable_opencl=enable_opencl,
        ffmpeg_version=fastflix.ffmpeg_version,
        start_extra=start_extra,
        **fastflix.current_video.video_settings.model_dump(),
        **settings.model_dump(),
    )

    return beginning, ending, output_fps


def generate_color_details(fastflix: FastFlix) -> str:
    if fastflix.current_video.video_settings.remove_hdr:
        return ""

    details = []
    if fastflix.current_video.video_settings.color_primaries:
        details.append(f"-color_primaries {fastflix.current_video.video_settings.color_primaries}")
    if fastflix.current_video.video_settings.color_transfer:
        details.append(f"-color_trc {fastflix.current_video.video_settings.color_transfer}")
    if fastflix.current_video.video_settings.color_space:
        details.append(f"-colorspace {fastflix.current_video.video_settings.color_space}")
    return " ".join(details)
