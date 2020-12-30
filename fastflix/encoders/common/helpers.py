# -*- coding: utf-8 -*-
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Tuple

import reusables

from fastflix.encoders.common.attachments import build_attachments
from fastflix.encoders.common.audio import build_audio
from fastflix.encoders.common.subtitles import build_subtitle
from fastflix.models.base import BaseDataClass
from fastflix.models.fastflix import FastFlix

null = "/dev/null"
if reusables.win_based:
    null = "NUL"


class Loop:
    item = "loop"

    def __init__(self, condition, commands, dirs=(), files=(), name="", ensure_paths=()):
        self.name = name
        self.condition = condition
        self.commands = commands
        self.ensure_paths = ensure_paths
        self.dirs = dirs
        self.files = files


@dataclass
class Command(BaseDataClass):
    command: str
    variables: List
    internal: bool
    item = "command"
    name: str = ""
    ensure_paths: List = ()
    exe: str = None
    shell: bool = False
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))


def generate_ffmpeg_start(
    source,
    ffmpeg,
    encoder,
    selected_track,
    start_time=0,
    end_time=None,
    pix_fmt="yuv420p10le",
    filters=None,
    max_muxing_queue_size="default",
    fast_time=True,
    video_title="",
    custom_map=False,
    **_,
):
    time_settings = f'{f"-ss {start_time}" if start_time else ""} {f"-to {end_time}" if end_time else ""} '
    time_one = time_settings if fast_time else ""
    time_two = time_settings if not fast_time else ""
    title = f'-metadata title="{video_title}"' if video_title else ""
    source = str(source).replace("\\", "/")
    ffmpeg = str(ffmpeg).replace("\\", "/")

    return (
        f'"{ffmpeg}" -y '
        f" {time_one} "
        f'-i "{source}" '
        f" {time_two} "
        f"{title} "
        f"{f'-max_muxing_queue_size {max_muxing_queue_size}' if max_muxing_queue_size != 'default' else ''} "
        f'{f"-map 0:{selected_track}" if not filters else ""} '
        f'{filters if filters else ""} '
        f"-c:v {encoder} "
        f"-pix_fmt {pix_fmt} "
    )


def generate_ending(
    audio,
    subtitles,
    cover="",
    output_video: Path = None,
    copy_chapters=True,
    remove_metadata=True,
    null_ending=False,
    extra="",
    **_,
):
    ending = (
        f" {'-map_metadata -1' if remove_metadata else ''} "
        f"{'-map_chapters 0' if copy_chapters else ''} "
        f"{audio} {subtitles} {cover} {extra} "
    )
    if output_video and not null_ending:
        output_video = str(output_video).replace("\\", "/")
        ending += f'"{output_video}"'
    else:
        ending += null
    return ending


def generate_filters(
    selected_track,
    crop=None,
    scale=None,
    scale_filter="lanczos",
    scale_width=None,
    scale_height=None,
    remove_hdr=False,
    rotate=None,
    vertical_flip=None,
    horizontal_flip=None,
    burn_in_subtitle_track=None,
    custom_filters=None,
    raw_filters=False,
    deinterlace=False,
    **_,
):

    filter_list = []
    if deinterlace:
        filter_list.append(f"yadif")
    if crop:
        filter_list.append(f"crop={crop}")
    if scale:
        filter_list.append(f"scale={scale}:flags={scale_filter}")
    elif scale_width:
        filter_list.append(f"scale={scale_width}:-8:flags={scale_filter}")
    elif scale_height:
        filter_list.append(f"scale=-8:{scale_height}:flags={scale_filter}")
    if rotate is not None:
        if rotate < 3:
            filter_list.append(f"transpose={rotate}")
        if rotate == 4:
            filter_list.append(f"transpose=2,transpose=2")
    if vertical_flip:
        filter_list.append("vflip")
    if horizontal_flip:
        filter_list.append("hflip")

    if remove_hdr:
        filter_list.append(
            "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
        )

    filters = ",".join(filter_list)
    if filters and custom_filters:
        filters = f"{filters},{custom_filters}"
    elif not filters and custom_filters:
        filters = custom_filters

    if burn_in_subtitle_track is not None:
        if filters:
            # You have to overlay first for it to work when scaled
            filter_complex = f"[0:{selected_track}][0:{burn_in_subtitle_track}]overlay[subbed];[subbed]{filters}[v]"

        else:
            filter_complex = f"[0:{selected_track}][0:{burn_in_subtitle_track}]overlay[v]"
    elif filters:
        filter_complex = f"[0:{selected_track}]{filters}[v]"
    else:
        return None
    if raw_filters:
        return filter_complex
    return f' -filter_complex "{filter_complex}" -map "[v]" '


def generate_all(
    fastflix: FastFlix, encoder: str, audio: bool = True, subs: bool = True, disable_filters: bool = False
) -> Tuple[str, str]:
    settings = fastflix.current_video.video_settings.video_encoder_settings

    audio = build_audio(fastflix.current_video.video_settings.audio_tracks) if audio else ""

    subtitles, burn_in_track = "", None
    if subs:
        subtitles, burn_in_track = build_subtitle(fastflix.current_video.video_settings.subtitle_tracks)

    attachments = build_attachments(fastflix.current_video.video_settings.attachment_tracks)

    filters = None
    if not disable_filters:
        filters = generate_filters(burn_in_track=burn_in_track, **asdict(fastflix.current_video.video_settings))

    ending = generate_ending(
        audio=audio,
        subtitles=subtitles,
        cover=attachments,
        output_video=fastflix.current_video.video_settings.output_path,
    )

    beginning = generate_ffmpeg_start(
        source=fastflix.current_video.source,
        ffmpeg=fastflix.config.ffmpeg,
        encoder=encoder,
        filters=filters,
        **asdict(fastflix.current_video.video_settings),
        **asdict(settings),
    )

    return beginning, ending


def generate_color_details(fastflix: FastFlix):
    if fastflix.current_video.video_settings.remove_hdr:
        return ""

    details = []
    if fastflix.current_video.color_primaries:
        details.append(f"-color_primaries {fastflix.current_video.color_primaries}")
    if fastflix.current_video.color_transfer:
        details.append(f"-color_trc {fastflix.current_video.color_transfer}")
    if fastflix.current_video.color_space:
        details.append(f"-colorspace {fastflix.current_video.color_space}")
    return " ".join(details)
