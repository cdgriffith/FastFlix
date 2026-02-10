# -*- coding: utf-8 -*-
import shlex
import subprocess
import sys
import uuid
from pathlib import Path
from typing import List, Tuple, Union, Optional

import reusables
from pydantic import BaseModel, Field

from fastflix.encoders.common.attachments import build_attachments
from fastflix.encoders.common.audio import build_audio
from fastflix.encoders.common.subtitles import build_subtitle
from fastflix.models.fastflix import FastFlix
from fastflix.shared import sanitize, quoted_path

null = "/dev/null"


if reusables.win_based:
    null = "NUL"


class Command(BaseModel):
    command: Union[List[str], str]
    item: str = "command"
    name: str = ""
    exe: str = None
    shell: bool = False
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))

    def to_list(self) -> List[str]:
        """Convert command to a list suitable for Popen."""
        if isinstance(self.command, list):
            return self.command
        # Legacy fallback for string commands
        if sys.platform == "win32":
            return shlex.split(self.command.replace("\\", "\\\\"))
        return shlex.split(self.command)

    def to_string(self) -> str:
        """Convert command to a display string."""
        if isinstance(self.command, str):
            return self.command
        if sys.platform == "win32":
            return subprocess.list2cmdline(self.command)
        return shlex.join(self.command)


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
    start_extra: Union[List[str], str] = "",
    extra_inputs: Optional[List[str]] = None,
    **_,
) -> List[str]:
    command = [str(ffmpeg)]

    if start_extra:
        command.extend(start_extra if isinstance(start_extra, list) else shlex.split(start_extra))

    if enable_opencl and remove_hdr:
        command.extend(["-init_hw_device", "opencl:0.0=ocl", "-filter_hw_device", "ocl"])

    command.append("-y")

    # Time settings for fast seek (before -i)
    if fast_seek:
        if start_time:
            command.extend(["-ss", str(start_time)])
        if end_time:
            command.extend(["-to", str(end_time)])

    if source_fps:
        command.extend(["-r", str(source_fps)])

    if concat:
        command.extend(["-f", "concat", "-safe", "0"])

    command.extend(["-i", str(source)])

    if extra_inputs:
        command.extend(extra_inputs)

    # Time settings for non-fast seek (after -i)
    if not fast_seek:
        if start_time:
            command.extend(["-ss", str(start_time)])
        if end_time:
            command.extend(["-to", str(end_time)])

    if video_title:
        command.extend(["-metadata", f"title={video_title}"])

    if max_muxing_queue_size != "default":
        command.extend(["-max_muxing_queue_size", str(max_muxing_queue_size)])

    if not filters:
        command.extend(["-map", f"0:{selected_track}"])

    vsync_type = "vsync"
    try:
        if ffmpeg_version.startswith("n") and int(ffmpeg_version[1:].split(".")[0]) >= 5:
            vsync_type = "fps_mode"
    except Exception:
        pass

    if vsync:
        command.extend([f"-{vsync_type}", str(vsync)])

    if filters:
        command.extend(filters)

    command.extend(["-c:v", encoder])
    command.extend(["-pix_fmt", pix_fmt])

    if maxrate:
        command.extend(["-maxrate:v", f"{maxrate}k"])
    if bufsize:
        command.extend(["-bufsize:v", f"{bufsize}k"])

    if video_track_title:
        command.extend(["-metadata:s:v:0", f"title={video_track_title}"])

    return command


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
    command = []

    if not disable_rotate_metadata and not remove_metadata:
        command.extend(["-metadata:s:v", "rotate=0"])

    if remove_metadata:
        command.extend(["-map_metadata", "-1"])
    else:
        command.extend(["-map_metadata", "0"])

    if copy_chapters:
        command.extend(["-map_chapters", "0"])
    else:
        command.extend(["-map_chapters", "-1"])

    fps_option = []
    if output_fps:
        fps_option = ["-r", str(output_fps)]
        command.extend(fps_option)

    if audio:
        command.extend(audio)
    if subtitles:
        command.extend(subtitles)
    if cover:
        command.extend(cover)

    if copy_data:
        command.extend(["-map", "0:d", "-c:d", "copy"])

    if output_video and not null_ending:
        command.append(str(sanitize(output_video)))
    else:
        command.append(null)

    return command, fps_option


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
    burn_in_file_index: int = 0,
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
    color_transfer: Optional[str] = None,
    **_,
):
    filter_list = []
    if start_filters:
        filter_list.append(start_filters)
    if deinterlace:
        filter_list.append("yadif")
    if crop:
        filter_list.append(f"crop={crop['width']}:{crop['height']}:{crop['left']}:{crop['top']}")
    if scale:
        if not vaapi:
            filter_list.append(f"scale={scale}:flags={scale_filter},setsar=1:1")
    if rotate:
        if rotate == 1:
            filter_list.append("transpose=1")
        if rotate == 2:
            filter_list.append("transpose=2,transpose=2")
        if rotate == 3:
            filter_list.append("transpose=2")
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
            filter_list.append("tonemap_vaapi=format=nv12:p=bt709:t=bt709:m=bt709")
        else:
            tin = color_transfer if color_transfer else "smpte2084"
            filter_list.append(
                f"zscale=tin={tin}:t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap={tone_map}:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
            )

    filters = ",".join(filter_list) if filter_list else ""

    if filters and custom_filters:
        filters = f"{filters},{custom_filters}"
    elif not filters and custom_filters:
        filters = custom_filters

    if burn_in_subtitle_track is not None:
        if burn_in_subtitle_type == "picture":
            if filters:
                # You have to overlay first for it to work when scaled
                filter_complex = f"[0:{selected_track}][{burn_in_file_index}:{burn_in_subtitle_track}]overlay[subbed];[subbed]{filters}[v]"
            else:
                filter_complex = f"[0:{selected_track}][{burn_in_file_index}:{burn_in_subtitle_track}]overlay[v]"
        else:
            filter_prefix = f"{filters}," if filters else ""
            filter_complex = f"[0:{selected_track}]{filter_prefix}subtitles='{quoted_path(str(source))}':si={burn_in_subtitle_track}[v]"
    elif filters:
        filter_complex = f"[0:{selected_track}]{filters}[v]"
    else:
        if raw_filters:
            return ""
        return []

    if raw_filters:
        return filter_complex

    return ["-filter_complex", filter_complex, "-map", "[v]"]


def generate_all(
    fastflix: FastFlix,
    encoder: str,
    audio: bool = True,
    subs: bool = True,
    disable_filters: bool = False,
    vaapi: bool = False,
    start_extra: Union[List[str], str] = "",
    **filters_extra,
) -> Tuple[List[str], List[str], List[str]]:
    settings = fastflix.current_video.video_settings.video_encoder_settings

    audio_cmd = build_audio(fastflix.current_video.audio_tracks) if audio else []

    # Assign file_index to external subtitle tracks and collect unique external file paths
    subtitle_tracks = fastflix.current_video.subtitle_tracks
    extra_input_files = []
    for track in subtitle_tracks:
        if track.external and track.file_path:
            if track.file_path not in extra_input_files:
                extra_input_files.append(track.file_path)
            track.file_index = extra_input_files.index(track.file_path) + 1
        else:
            track.file_index = 0

    subtitles_cmd, burn_in_track, burn_in_type = [], None, None
    if subs:
        subtitles_cmd, burn_in_track, burn_in_type = build_subtitle(
            subtitle_tracks, output_path=fastflix.current_video.video_settings.output_path
        )
        if burn_in_type == "text":
            for i, x in enumerate(fastflix.current_video.streams["subtitle"]):
                if x["index"] == burn_in_track:
                    burn_in_track = i
                    break

    # Look up external burn-in info from the track list
    burn_in_file_path = None
    burn_in_file_index = 0
    if burn_in_track is not None:
        for track in subtitle_tracks:
            if track.burn_in and track.enabled:
                if track.external and track.file_path:
                    burn_in_file_path = track.file_path
                    burn_in_file_index = track.file_index
                break

    attachments_cmd = build_attachments(fastflix.current_video.attachment_tracks)

    enable_opencl = fastflix.opencl_support
    if "enable_opencl" in filters_extra:
        enable_opencl = filters_extra.pop("enable_opencl")

    filters_cmd = None
    if not disable_filters:
        filter_details = fastflix.current_video.video_settings.model_dump().copy()
        filter_details.update(filters_extra)
        # For text burn-in from external file, pass the external file path as source
        filter_source = (
            burn_in_file_path if (burn_in_file_path and burn_in_type == "text") else fastflix.current_video.source
        )
        filters_cmd = generate_filters(
            source=filter_source,
            burn_in_subtitle_track=burn_in_track,
            burn_in_subtitle_type=burn_in_type,
            burn_in_file_index=burn_in_file_index,
            scale=fastflix.current_video.scale,
            enable_opencl=enable_opencl,
            vaapi=vaapi,
            **filter_details,
        )

    ending, output_fps = generate_ending(
        audio=audio_cmd,
        subtitles=subtitles_cmd,
        cover=attachments_cmd,
        output_video=fastflix.current_video.video_settings.output_path,
        disable_rotate_metadata=encoder == "copy",
        **fastflix.current_video.video_settings.model_dump(),
    )

    # Build extra -i arguments for external subtitle files
    # When fast seek is used, -ss/-to before -i only apply to the next input.
    # External inputs need their own -ss/-to to stay in sync with the seeked video.
    vs = fastflix.current_video.video_settings
    extra_inputs = []
    for file_path in extra_input_files:
        if vs.fast_seek:
            if vs.start_time:
                extra_inputs.extend(["-ss", str(vs.start_time)])
            if vs.end_time:
                extra_inputs.extend(["-to", str(vs.end_time)])
        extra_inputs.extend(["-i", str(file_path)])

    beginning = generate_ffmpeg_start(
        source=fastflix.current_video.source,
        ffmpeg=fastflix.config.ffmpeg,
        encoder=encoder,
        filters=filters_cmd,
        concat=fastflix.current_video.concat,
        enable_opencl=enable_opencl if not disable_filters else False,
        ffmpeg_version=fastflix.ffmpeg_version,
        start_extra=start_extra,
        extra_inputs=extra_inputs if extra_inputs else None,
        **fastflix.current_video.video_settings.model_dump(),
        **settings.model_dump(),
    )

    return beginning, ending, output_fps


def generate_color_details(fastflix: FastFlix) -> List[str]:
    if fastflix.current_video.video_settings.remove_hdr:
        return []

    details = []
    if fastflix.current_video.video_settings.color_primaries:
        details.extend(["-color_primaries", fastflix.current_video.video_settings.color_primaries])
    if fastflix.current_video.video_settings.color_transfer:
        details.extend(["-color_trc", fastflix.current_video.video_settings.color_transfer])
    if fastflix.current_video.video_settings.color_space:
        details.extend(["-colorspace", fastflix.current_video.video_settings.color_space])

    return details
