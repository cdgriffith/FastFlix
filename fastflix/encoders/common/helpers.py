# -*- coding: utf-8 -*-
import re
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

BITMAP_SUBTITLE_TYPES = ("picture", "pgs")

_COLOR_NAME = re.compile(r"^[A-Za-z]+$")
_COLOR_HEX = re.compile(r"^(0x|#)[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$")
_COLOR_ALPHA = re.compile(r"^(0x[0-9A-Fa-f]{1,2}|[0-9]*\.?[0-9]+)$")


def validate_ffmpeg_color(value, default="black") -> str:
    """Return value if it is an ffmpeg colour (name or 0xRRGGBB/#RRGGBB, optional @alpha), otherwise default."""
    if not isinstance(value, str):
        return default
    value = value.strip()
    color, _, alpha = value.partition("@")
    if not (_COLOR_NAME.match(color) or _COLOR_HEX.match(color)):
        return default
    if "@" in value and not _COLOR_ALPHA.match(alpha):
        return default
    return value


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


def split_extra_args(text: str) -> List[str]:
    """Split user supplied custom arguments like a shell; backslashes stay literal on Windows (paths)."""
    lex = shlex.shlex(text, posix=True)
    lex.whitespace_split = True
    lex.commenters = ""
    if sys.platform == "win32":
        lex.escape = ""
    return list(lex)


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
    gop_length=None,
    denoise: Optional[str] = None,
    reverse_video: bool = False,
    **_,
) -> List[str]:
    command = [str(ffmpeg)]
    uses_nlmeans_opencl = bool(denoise) and denoise.startswith("nlmeans_opencl")
    # The reverse filter operates on the filtergraph output, so output-side (exact) seeking would trim the
    # already reversed timeline (mirrored segment) and desync copied streams. Always seek on the input side.
    if reverse_video and filters:
        fast_seek = True

    if start_extra:
        command.extend(start_extra if isinstance(start_extra, list) else split_extra_args(start_extra))

    if enable_opencl and (remove_hdr or uses_nlmeans_opencl):
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

    if vsync:
        command.extend(["-fps_mode", str(vsync)])

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

    if gop_length is not None and gop_length > 0:
        command.extend(["-g", str(gop_length)])

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
    source_has_rotation=False,
    copy_data=False,
    data_tracks=None,
    faststart=True,
    **_,
):
    command = []

    # When source had rotation and metadata is preserved, clear the legacy rotate tag
    # to prevent players from double-rotating (the tag gets copied via -map_metadata 0)
    if source_has_rotation and not remove_metadata:
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

    mapped_data = False
    if data_tracks:
        has_data = False
        has_attachment = False
        # Compute the real output stream index from what is actually mapped (video + audio + subtitles that are
        # not burned in), instead of trusting the stored outdex which can go stale.
        next_outdex = (
            1 + sum(1 for x in (audio or []) if x == "-map") + sum(1 for x in (subtitles or []) if x == "-map")
        )
        for track in data_tracks:
            if not track.enabled:
                continue
            mapped_data = True
            command.extend(["-map", f"0:{track.index}"])
            outdex = next_outdex
            next_outdex += 1
            # Clear title/handler metadata (same as audio tracks)
            if track.title:
                command.extend([f"-metadata:s:{outdex}", f"title={track.title}"])
                command.extend([f"-metadata:s:{outdex}", f"handler={track.title}"])
            else:
                command.extend([f"-metadata:s:{outdex}", "title="])
                command.extend([f"-metadata:s:{outdex}", "handler="])
            if track.codec_type == "data":
                has_data = True
            elif track.codec_type == "attachment":
                has_attachment = True
                # Restore mimetype/filename stripped by -map_metadata -1
                # (required by the matroska muxer for attachment streams)
                if track.mimetype:
                    command.extend([f"-metadata:s:{outdex}", f"mimetype={track.mimetype}"])
                if track.filename:
                    command.extend([f"-metadata:s:{outdex}", f"filename={track.filename}"])
        if has_data:
            command.extend(["-c:d", "copy"])
        if has_attachment:
            command.extend(["-c:t", "copy"])
    elif copy_data:
        mapped_data = True
        command.extend(["-map", "0:d", "-c:d", "copy"])

    # Explicitly disable data/attachment streams when none are mapped to prevent
    # FFmpeg from auto-including them (causes failures with formats like MKV)
    if not mapped_data:
        command.append("-dn")

    if faststart and output_video and output_video.suffix.lower() in (".mp4", ".mov", ".m4v"):
        command.extend(["-movflags", "+faststart"])

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
    sar=None,
    remove_hdr=False,
    vaapi: bool = False,
    vaapi_format: str = "nv12",
    rotate=0,
    vertical_flip=None,
    horizontal_flip=None,
    burn_in_subtitle_track=None,
    burn_in_subtitle_type=None,
    burn_in_file_index: int = 0,
    source_width: Optional[int] = None,
    source_height: Optional[int] = None,
    custom_filters=None,
    start_filters=None,
    raw_filters=False,
    deinterlace=False,
    deinterlace_filter="yadif",
    contrast=None,
    brightness=None,
    saturation=None,
    gamma=None,
    hue=None,
    sharpen=None,
    enable_opencl: bool = False,
    tone_map: str = "hable",
    video_speed: Union[float, int] = 1,
    reverse_video: bool = False,
    deblock: Union[str, None] = None,
    deblock_size: int = 4,
    denoise: Union[str, None] = None,
    color_transfer: Optional[str] = None,
    color_primaries: Optional[str] = None,
    color_space: Optional[str] = None,
    source_pix_fmt: Optional[str] = None,
    target_pix_fmt: Optional[str] = None,
    **_kw,
):
    filter_list = []
    if start_filters:
        filter_list.append(start_filters)
    if deinterlace:
        filter_list.append(deinterlace_filter or "yadif")
    if crop:
        filter_list.append(f"crop={crop['width']}:{crop['height']}:{crop['left']}:{crop['top']}")
    if scale:
        filter_list.append(f"scale={scale}:flags={scale_filter},setsar=1:1")
    elif sar and sar != "1:1" and sar != "1/1":
        filter_list.append("setsar=1:1")
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
    # Pad after rotation/flip so the target aspect is applied to the final orientation
    pad_aspect = _kw.get("pad_aspect")
    if pad_aspect and pad_aspect != "none":
        pad_color = validate_ffmpeg_color(_kw.get("pad_color", "black") or "black")
        num, den = pad_aspect.split(":")
        target_ratio = int(num) / int(den)
        filter_list.append(
            f"pad=w=if(gt(a\\,{target_ratio})\\,iw\\,ceil(ih*{target_ratio}/2)*2)"
            f":h=if(gt(a\\,{target_ratio})\\,ceil(iw/{target_ratio}/2)*2\\,ih)"
            f":x=(ow-iw)/2:y=(oh-ih)/2:color={pad_color}"
        )
    if video_speed and video_speed != 1:
        filter_list.append(f"setpts={video_speed}*PTS")
    text_sub_filter = None
    if burn_in_subtitle_track is not None and burn_in_subtitle_type not in BITMAP_SUBTITLE_TYPES:
        original_size = f":original_size={source_width}x{source_height}" if source_width and source_height else ""
        text_sub_filter = f"subtitles='{quoted_path(str(source))}':si={burn_in_subtitle_track}{original_size}"
    if reverse_video:
        if text_sub_filter:
            # Burn subtitles in before reversing so they stay in sync with the reversed video
            filter_list.append(text_sub_filter)
            text_sub_filter = None
        filter_list.append("reverse")
    if deblock:
        filter_list.append(f"deblock=filter={deblock}:block={deblock_size}")
    if denoise:
        if denoise.startswith("nlmeans_opencl"):
            if enable_opencl:
                bits_fmt = "p010" if any(x in (source_pix_fmt or "") for x in ("10", "12", "16")) else "yuv420p"
                filter_list.append(f"format={bits_fmt},hwupload,{denoise},hwdownload,format={bits_fmt}")
            else:
                # No OpenCL device available (e.g. previews), fall back to the equivalent CPU filter
                filter_list.append(denoise.replace("nlmeans_opencl", "nlmeans", 1))
        else:
            filter_list.append(denoise)
    if _kw.get("deflicker"):
        filter_list.append(_kw["deflicker"])
    if _kw.get("unsharp"):
        filter_list.append(_kw["unsharp"])

    software_tonemap = None
    if remove_hdr and not enable_opencl and not vaapi:
        tin = color_transfer if color_transfer else "smpte2084"
        pin = color_primaries if color_primaries else "bt2020"
        min_val = color_space if color_space else "bt2020nc"
        keep_bits = (
            bool(target_pix_fmt)
            and target_pix_fmt.startswith("yuv")
            and ("10" in target_pix_fmt or "12" in target_pix_fmt)
        )
        out_fmt = target_pix_fmt if keep_bits else "yuv420p"
        software_tonemap = (
            f"zscale=tin={tin}:pin={pin}:min={min_val}:t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
            f"tonemap=tonemap={tone_map}:desat=0,zscale=t=bt709:m=bt709:r=tv,format={out_fmt}"
        )
    bitmap_burn_in = burn_in_subtitle_track is not None and burn_in_subtitle_type in BITMAP_SUBTITLE_TYPES
    # Bitmap subtitles are overlaid on the tone-mapped (SDR) frames, so tone map first and overlay straight after.
    tonemap_before_overlay = software_tonemap if bitmap_burn_in else None
    if software_tonemap and not bitmap_burn_in:
        filter_list.append(software_tonemap)

    eq_filters = []
    if brightness:
        eq_filters.append(f"brightness={brightness}")
    if saturation:
        eq_filters.append(f"saturation={saturation}")
    if contrast:
        eq_filters.append(f"contrast={contrast}")
    if gamma:
        eq_filters.append(f"gamma={gamma}")
    if eq_filters:
        filter_list.append("eq=" + ":".join(eq_filters))
    if hue:
        filter_list.append(f"hue=h={hue}")
    if _kw.get("vibrance"):
        filter_list.append(f"vibrance=intensity={_kw['vibrance']}")
    if _kw.get("colorbalance"):
        filter_list.append(_kw["colorbalance"])
    if _kw.get("color_temperature"):
        filter_list.append(f"colortemperature=temperature={_kw['color_temperature']}")
    if _kw.get("curves_preset"):
        filter_list.append(f"curves=preset={_kw['curves_preset']}")
    if _kw.get("lut3d_path"):
        filter_list.append(f"lut3d=file='{quoted_path(str(_kw['lut3d_path']))}'")

    if sharpen:
        filter_list.append(f"cas=strength={sharpen}")

    # VAAPI frames are processed as software frames and uploaded last (after custom filters and subtitle burn-in)
    vaapi_tail = f"format={vaapi_format},hwupload" if vaapi else ""

    if remove_hdr:
        if enable_opencl and not vaapi:
            filter_list.append(
                f"format=p010,hwupload,tonemap_opencl=tonemap={tone_map}:desat=0:r=tv:p=bt709:t=bt709:m=bt709:format=nv12,hwdownload,format=nv12"
            )
        elif vaapi:
            tonemap_format = "p010" if vaapi_format == "p010le" else "nv12"
            vaapi_tail = f"format=p010le,hwupload,tonemap_vaapi=format={tonemap_format}:p=bt709:t=bt709:m=bt709"

    filters = ",".join(filter_list) if filter_list else ""

    if filters and custom_filters:
        filters = f"{filters},{custom_filters}"
    elif not filters and custom_filters:
        filters = custom_filters

    if vaapi_tail:
        if text_sub_filter:
            text_sub_filter = f"{text_sub_filter},{vaapi_tail}"
        else:
            filters = f"{filters},{vaapi_tail}" if filters else vaapi_tail

    if burn_in_subtitle_track is not None:
        if bitmap_burn_in:
            # You have to overlay first for it to work when scaled
            base = f"[0:{selected_track}]"
            tonemap_prefix = ""
            if tonemap_before_overlay:
                tonemap_prefix = f"{base}{tonemap_before_overlay}[tonemapped];"
                base = "[tonemapped]"
            overlay = f"{base}[{burn_in_file_index}:{burn_in_subtitle_track}]overlay"
            if filters:
                filter_complex = f"{tonemap_prefix}{overlay}[subbed];[subbed]{filters}[v]"
            else:
                filter_complex = f"{tonemap_prefix}{overlay}[v]"
        else:
            filter_prefix = f"{filters}," if filters else ""
            if text_sub_filter:
                filter_complex = f"[0:{selected_track}]{filter_prefix}{text_sub_filter}[v]"
            else:
                filter_complex = f"[0:{selected_track}]{filters}[v]"
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

    # Detect source rotation for metadata clearing (FFmpeg auto-rotates during re-encoding)
    source_rotation_degrees = fastflix.current_video.source_rotation

    audio_cmd = (
        build_audio(
            fastflix.current_video.audio_tracks,
            # Video filters (including reverse) are not applied when disabled (copy), keep audio forward then
            reverse_video=fastflix.current_video.video_settings.reverse_video and not disable_filters,
        )
        if audio
        else []
    )

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
        burn_in_is_external = any(x.burn_in and x.enabled and x.external for x in subtitle_tracks)
        if burn_in_type == "text" and not burn_in_is_external:
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

    mapped_attachment_count = sum(
        1 for track in fastflix.current_video.data_tracks if track.enabled and track.codec_type == "attachment"
    )
    attachments_cmd = build_attachments(fastflix.current_video.attachment_tracks, mapped_attachment_count)

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
            source_width=fastflix.current_video.width,
            source_height=fastflix.current_video.height,
            scale=fastflix.current_video.scale,
            sar=fastflix.current_video.sar,
            enable_opencl=enable_opencl,
            source_pix_fmt=fastflix.current_video.pix_fmt,
            target_pix_fmt=getattr(settings, "pix_fmt", None),
            vaapi=vaapi,
            **filter_details,
        )

    ending, output_fps = generate_ending(
        audio=audio_cmd,
        subtitles=subtitles_cmd,
        cover=attachments_cmd,
        output_video=fastflix.current_video.video_settings.output_path,
        source_has_rotation=bool(source_rotation_degrees) and encoder != "copy",
        data_tracks=fastflix.current_video.data_tracks,
        **fastflix.current_video.video_settings.model_dump(),
    )

    # Build extra -i arguments for external subtitle files
    # When fast seek is used, -ss/-to before -i only apply to the next input.
    # External inputs need their own -ss/-to to stay in sync with the seeked video.
    vs = fastflix.current_video.video_settings
    extra_inputs = []
    # Reverse forces input-side seeking (see generate_ffmpeg_start)
    input_seek = vs.fast_seek or bool(filters_cmd and vs.reverse_video)
    for file_path in extra_input_files:
        if input_seek:
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
        start_extra=start_extra,
        extra_inputs=extra_inputs if extra_inputs else None,
        **fastflix.current_video.video_settings.model_dump(),
        **settings.model_dump(),
    )

    return beginning, ending, output_fps


def generate_color_details(fastflix: FastFlix) -> List[str]:
    if fastflix.current_video.video_settings.remove_hdr:
        return ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]

    details = []
    if fastflix.current_video.video_settings.color_primaries:
        details.extend(["-color_primaries", fastflix.current_video.video_settings.color_primaries])
    if fastflix.current_video.video_settings.color_transfer:
        details.extend(["-color_trc", fastflix.current_video.video_settings.color_transfer])
    if fastflix.current_video.video_settings.color_space:
        details.extend(["-colorspace", fastflix.current_video.video_settings.color_space])

    return details


def hevc_tag_args(output_path: Union[str, Path, None]) -> List[str]:
    """Tag HEVC as hvc1 for mp4/m4v/mov, FFmpeg defaults to hev1 which QuickTime, iOS and Safari will not play."""
    if output_path and Path(output_path).suffix.lower() in (".mp4", ".m4v", ".mov"):
        return ["-tag:v", "hvc1"]
    return []
