# -*- coding: utf-8 -*-
import reusables

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


class Command:
    item = "command"

    def __init__(self, command, variables, internal, name="", ensure_paths=(), exe=None, shell=False):
        self.name = name
        self.command = command
        self.variables = variables
        self.internal = internal
        self.ensure_paths = ensure_paths
        self.exe = exe
        self.shell = shell


def generate_ffmpeg_start(
    source,
    ffmpeg,
    encoder,
    video_track,
    start_time=0,
    end_time=None,
    pix_fmt="yuv420p10le",
    filters=None,
    max_mux="default",
    fast_time=True,
    video_title="",
    **_,
):
    time_settings = f'{f"-ss {start_time}" if start_time else ""} {f"-to {end_time}" if end_time else ""} '
    time_one = time_settings if fast_time else ""
    time_two = time_settings if not fast_time else ""
    title = f'-metadata title="{video_title}"' if video_title else ""

    return (
        f'"{ffmpeg}" -y '
        f" {time_one} "
        f'-i "{source}" '
        f" {time_two} "
        f"{title} "
        f"{f'-max_muxing_queue_size {max_mux}' if max_mux != 'default' else ''} "
        f"-map 0:{video_track} "
        f"-c:v:0 {encoder} "
        f"-pix_fmt {pix_fmt} "
        f'{f"-vf {filters}" if filters else ""} '
    )


def generate_ending(
    audio,
    subtitles,
    cover,
    output_video=None,
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
        ending += f'"{output_video}"'
    else:
        ending += null
    return ending


def generate_filters(**kwargs):
    crop = kwargs.get("crop")
    scale = kwargs.get("scale")
    scale_filter = kwargs.get("scale_filter", "lanczos")
    scale_width = kwargs.get("scale_width")
    scale_height = kwargs.get("scale_height")
    disable_hdr = kwargs.get("disable_hdr")
    rotate = kwargs.get("rotate")
    vflip = kwargs.get("v_flip")
    hflip = kwargs.get("h_flip")

    filter_list = []
    if crop:
        filter_list.append(f"crop={crop}")
    if scale:
        filter_list.append(f"scale={scale}:flags={scale_filter}")
    elif scale_width:
        filter_list.append(f"scale={scale_width}:-1:flags={scale_filter}")
    elif scale_height:
        filter_list.append(f"scale=-1:{scale_height}:flags={scale_filter}")
    if rotate is not None:
        if rotate < 3:
            filter_list.append(f"transpose={rotate}")
        if rotate == 4:
            filter_list.append(f"transpose=2,transpose=2")
    if vflip:
        filter_list.append("vflip")
    if hflip:
        filter_list.append("hflip")

    if disable_hdr:
        filter_list.append(
            "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
            "zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
        )

    return ",".join(filter_list)
