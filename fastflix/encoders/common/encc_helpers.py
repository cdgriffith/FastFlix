# -*- coding: utf-8 -*-
import logging
from typing import List, Optional

from fastflix.models.video import SubtitleTrack, AudioTrack, DataTrack, Video
from fastflix.encoders.common.audio import lossless
from fastflix.models.fastflix import FastFlix
from fastflix.models.encode import VCEEncCAVCSettings, VCEEncCAV1Settings, VCEEncCSettings

logger = logging.getLogger("fastflix")


def audio_quality_converter(quality, codec, channels=2, track_number=1):
    base = [120, 96, 72, 48, 24, 24, 16, 8, 8, 8][quality]

    match codec:
        case "libopus":
            return f" --audio-bitrate {track_number}?{base * channels}k "
        case "aac":
            return f" --audio-quality {track_number}?{[2, 1.8, 1.6, 1.4, 1.2, 1, 0.8, 0.6, 0.4, 0.2][quality]} "
        case "libfdk_aac":
            return f" --audio-quality {track_number}?{[1, 1, 2, 2, 3, 3, 4, 4, 5, 5][quality]} "
        case "libvorbis" | "vorbis":
            return f" --audio-quality {track_number}?{[10, 9, 8, 7, 6, 5, 4, 3, 2, 1][quality]} "
        case "libmp3lame" | "mp3":
            return f" --audio-quality {track_number}?{quality} "
        case "ac3" | "eac3" | "truehd":
            return f" --audio-bitrate {track_number}?{base * channels * 4}k "
        case _:
            return f" --audio-bitrate {track_number}?{base * channels}k "


def rigaya_avformat_reader(fastflix: FastFlix) -> List[str]:
    # Avisynth reader 	avs
    # VapourSynth reader 	vpy
    # avi reader 	avi
    # y4m reader 	y4m
    # raw reader 	yuv
    # avhw/avsw reader 	others
    ending = fastflix.current_video.source.suffix
    if fastflix.current_video.video_settings.video_encoder_settings.decoder not in ("Hardware", "Software"):
        if ending.lower() in (".avs", ".vpy", ".avi", ".y4m", ".yuv"):
            return []
    return (
        ["--avhw"] if fastflix.current_video.video_settings.video_encoder_settings.decoder == "Hardware" else ["--avsw"]
    )


def rigaya_auto_options(fastflix: FastFlix) -> List[str]:
    reader_format = rigaya_avformat_reader(fastflix)
    if not reader_format:
        output = []
        if fastflix.current_video.video_settings.color_space:
            output.extend(["--colormatrix", fastflix.current_video.video_settings.color_space])
        if fastflix.current_video.video_settings.color_transfer:
            output.extend(["--transfer", fastflix.current_video.video_settings.color_transfer])
        if fastflix.current_video.video_settings.color_primaries:
            output.extend(["--colorprim", fastflix.current_video.video_settings.color_primaries])
        return output

    return [
        "--chromaloc",
        "auto",
        "--colorrange",
        "auto",
        "--colormatrix",
        (fastflix.current_video.video_settings.color_space or "auto"),
        "--transfer",
        (fastflix.current_video.video_settings.color_transfer or "auto"),
        "--colorprim",
        (fastflix.current_video.video_settings.color_primaries or "auto"),
    ]


def parse_frame_rate(frame_rate_str: str) -> Optional[float]:
    """Parse a frame rate string like '24000/1001' or '30' into a float.

    Returns None if the string is empty or cannot be parsed.
    """
    if not frame_rate_str:
        return None
    try:
        if "/" in frame_rate_str:
            num, den = frame_rate_str.split("/", 1)
            denominator = float(den)
            if denominator == 0:
                return None
            return float(num) / denominator
        return float(frame_rate_str)
    except (ValueError, ZeroDivisionError):
        return None


def rigaya_trim_or_seek(video: Video) -> List[str]:
    """Build time trimming arguments for rigaya encoders.

    In exact mode (fast_seek=False), uses --trim with frame numbers for precise cutting.
    In fast mode (fast_seek=True), uses --seek/--seekto with timestamps.
    Falls back to --seek/--seekto if frame rate is unavailable in exact mode.
    """
    start_time = video.video_settings.start_time
    end_time = video.video_settings.end_time

    if not start_time and not end_time:
        return []

    if not video.video_settings.fast_seek:
        fps = parse_frame_rate(video.frame_rate)
        if fps:
            start_frame = int(start_time * fps) if start_time else 0
            if end_time:
                end_frame = int(end_time * fps)
            else:
                end_frame = int(video.duration * fps)
            return ["--trim", f"{start_frame}:{end_frame}"]

    result = []
    if start_time:
        result.extend(["--seek", str(start_time)])
    if end_time:
        result.extend(["--seekto", str(end_time)])
    return result


def pa_builder(settings: VCEEncCAVCSettings | VCEEncCAV1Settings | VCEEncCSettings):
    if not settings.pre_analysis:
        return ""
    base = (
        f"--pa sc={settings.pa_sc},"
        f"ss={settings.pa_ss},"
        f"activity-type={settings.pa_activity_type},"
        f"caq-strength={settings.pa_caq_strength},"
        f"ltr={'true' if settings.pa_ltr else 'false'},"
    )
    if settings.pa_initqpsc is not None:
        base += f"initqpsc={settings.pa_initqpsc},"
    if settings.pa_lookahead is not None:
        base += f"lookahead={settings.pa_lookahead},"
    if settings.pa_fskip_maxqp is not None:
        base += f"fskip-maxqp={settings.pa_fskip_maxqp},"
    if settings.pa_paq is not None:
        base += f"paq={settings.pa_paq},"
    if settings.pa_taq is not None:
        base += f"taq={settings.pa_taq},"
    if settings.pa_motion_quality is not None:
        base += f"motion-quality={settings.pa_motion_quality},"

    return base.rstrip(",")


def get_stream_pos(streams) -> dict:
    return {x.index: i for i, x in enumerate(streams, start=1)}


def build_audio(audio_tracks: list[AudioTrack], audio_streams) -> List[str]:
    if not audio_tracks:
        return []
    command_list = []
    copies = []
    track_ids = set()
    stream_ids = get_stream_pos(audio_streams)

    for track in sorted(audio_tracks, key=lambda x: x.outdex):
        if not track.enabled:
            continue
        if track.index in track_ids:
            logger.warning("*EncC does not support copy and duplicate of audio tracks!")
        track_ids.add(track.index)
        audio_id = stream_ids[track.index]
        if track.language:
            command_list.extend(["--audio-metadata", f"{audio_id}?language={track.language}"])
        if not track.conversion_codec or track.conversion_codec == "none":
            copies.append(str(audio_id))
        elif track.conversion_codec:
            if track.downmix and track.downmix != "No Downmix":
                downmix = ["--audio-stream", f"{audio_id}?:{track.downmix}"]
            else:
                raw_layout = track.raw_info.get("channel_layout", "") if track.raw_info else ""
                if raw_layout:
                    downmix = ["--audio-stream", f"{audio_id}?:{raw_layout}"]
                else:
                    downmix = []
            bitrate_parts = []
            if track.conversion_codec not in lossless:
                if track.conversion_bitrate:
                    conversion_bitrate = (
                        track.conversion_bitrate
                        if track.conversion_bitrate.lower().endswith(("k", "m", "g", "kb", "mb", "gb"))
                        else f"{track.conversion_bitrate}k"
                    )
                    bitrate_parts = ["--audio-bitrate", f"{audio_id}?{conversion_bitrate}"]
                else:
                    quality_str = audio_quality_converter(
                        track.conversion_aq or 0, track.conversion_codec, track.raw_info.get("channels"), audio_id
                    )
                    bitrate_parts = quality_str.split()
            command_list.extend(downmix)
            command_list.extend(["--audio-codec", f"{audio_id}?{track.conversion_codec}"])
            if track.conversion_profile:
                command_list.extend(["--audio-profile", f"{audio_id}?{track.conversion_profile}"])
            command_list.extend(bitrate_parts)
            command_list.extend(["--audio-metadata", f"{audio_id}?clear"])

        if track.title:
            command_list.extend(["--audio-metadata", f"{audio_id}?title={track.title}"])
            command_list.extend(["--audio-metadata", f"{audio_id}?handler={track.title}"])

        added = ""
        for disposition, is_set in track.dispositions.items():
            if is_set:
                added += f"{disposition},"
        if added:
            command_list.extend(["--audio-disposition", f"{audio_id}?{added.rstrip(',')}"])
        else:
            command_list.extend(["--audio-disposition", f"{audio_id}?unset"])
    if not command_list:
        return []
    result = []
    if copies:
        result.extend(["--audio-copy", ",".join(copies)])
    result.extend(command_list)
    return result


def build_subtitle(subtitle_tracks: list[SubtitleTrack], subtitle_streams, video_height: int) -> List[str]:
    embedded_tracks = [t for t in subtitle_tracks if not t.external]
    external_tracks = [t for t in subtitle_tracks if t.external]
    command_list = []
    copies = []
    stream_ids = get_stream_pos(subtitle_streams)

    scale = ",scale=2.0" if video_height > 1800 else ""

    for track in sorted(embedded_tracks, key=lambda x: x.outdex):
        if not track.enabled:
            continue
        sub_id = stream_ids[track.index]
        if track.burn_in:
            command_list.extend(["--vpp-subburn", f"track={sub_id}{scale}"])
        else:
            copies.append(str(sub_id))
            added = ""
            for disposition, is_set in track.dispositions.items():
                if is_set:
                    added += f"{disposition},"
            if added:
                command_list.extend(["--sub-disposition", f"{sub_id}?{added.rstrip(',')}"])
            else:
                command_list.extend(["--sub-disposition", f"{sub_id}?unset"])

            command_list.extend(["--sub-metadata", f"{sub_id}?language={track.language}"])

    for track in sorted(external_tracks, key=lambda x: x.outdex):
        if not track.enabled:
            continue
        if track.burn_in:
            ext_scale = ",scale=2.0" if video_height > 1800 else ""
            command_list.extend(["--vpp-subburn", f"filename={track.file_path}{ext_scale}"])
        else:
            command_list.extend(["--sub-source", track.file_path])

    if not command_list and not copies:
        return []
    result = []
    if copies:
        result.extend(["--sub-copy", ",".join(copies)])
    result.extend(command_list)
    return result


def build_data(data_tracks: list[DataTrack], data_streams, attachment_streams) -> List[str]:
    if not data_tracks:
        return []
    command_list = []
    data_copies = []
    attachment_copies = []
    data_stream_ids = get_stream_pos(data_streams)
    attachment_stream_ids = get_stream_pos(attachment_streams)

    for track in data_tracks:
        if not track.enabled:
            continue
        if track.codec_type == "data" and track.index in data_stream_ids:
            data_copies.append(str(data_stream_ids[track.index]))
        elif track.codec_type == "attachment" and track.index in attachment_stream_ids:
            attachment_copies.append(str(attachment_stream_ids[track.index]))

    if data_copies:
        command_list.extend(["--data-copy", ",".join(data_copies)])
    if attachment_copies:
        command_list.extend(["--attachment-copy", ",".join(attachment_copies)])
    return command_list


# Mapping of FastFlix FFmpeg denoise preset strings to rigaya VPP equivalents.
# nlmeans -> --vpp-nlmeans (direct equivalent: s->sigma/h, p->patch, r->search)
# atadenoise -> --vpp-knn (closest spatial/temporal alternative)
# hqdn3d -> --vpp-pmd (closest spatial denoiser)
# vaguedenoiser -> --vpp-pmd (no wavelet denoiser in rigaya)
RIGAYA_UNSHARP_MAP: dict[str, list[str]] = {
    "unsharp=5:5:0.5:5:5:0.0": ["--vpp-unsharp", "radius=3,weight=0.3"],
    "unsharp=5:5:1.0:5:5:0.5": ["--vpp-unsharp", "radius=3,weight=0.6"],
    "unsharp=7:7:1.5:7:7:1.0": ["--vpp-unsharp", "radius=5,weight=1.0"],
}

RIGAYA_DENOISE_MAP: dict[str, list[str]] = {
    # nlmeans weak/moderate/strong
    "nlmeans=s=1.0:p=3:r=9": ["--vpp-nlmeans", "sigma=1.0,h=1.0,patch=3,search=9"],
    "nlmeans=s=1.0:p=7:r=15": ["--vpp-nlmeans", "sigma=1.0,h=1.0,patch=7,search=15"],
    "nlmeans=s=10.0:p=13:r=25": ["--vpp-nlmeans", "sigma=10.0,h=10.0,patch=13,search=25"],
    # nlmeans_opencl -> same rigaya nlmeans (natively GPU-accelerated)
    "nlmeans_opencl=s=1.0:p=3:r=9": ["--vpp-nlmeans", "sigma=1.0,h=1.0,patch=3,search=9"],
    "nlmeans_opencl=s=1.0:p=7:r=15": ["--vpp-nlmeans", "sigma=1.0,h=1.0,patch=7,search=15"],
    "nlmeans_opencl=s=10.0:p=13:r=25": ["--vpp-nlmeans", "sigma=10.0,h=10.0,patch=13,search=25"],
    # atadenoise weak/moderate/strong -> knn
    "atadenoise=0a=0.01:0b=0.02:1a=0.01:1b=0.02:2a=0.01:2b=0.02:s=9": [
        "--vpp-knn",
        "radius=3,strength=0.04,lerp=0.2,th_lerp=0.8",
    ],
    "atadenoise=0a=0.02:0b=0.04:1a=0.02:1b=0.04:2a=0.02:2b=0.04:s=9": [
        "--vpp-knn",
        "radius=3,strength=0.08,lerp=0.2,th_lerp=0.8",
    ],
    "atadenoise=0a=0.04:0b=0.12:1a=0.04:1b=0.12:2a=0.04:2b=0.12:s=9": [
        "--vpp-knn",
        "radius=3,strength=0.16,lerp=0.2,th_lerp=0.8",
    ],
    # hqdn3d weak/moderate/strong -> pmd
    "hqdn3d=luma_spatial=2:chroma_spatial=1.5:luma_tmp=3:chroma_tmp=2.25": [
        "--vpp-pmd",
        "apply_count=1,strength=50,threshold=80",
    ],
    "hqdn3d=luma_spatial=4:chroma_spatial=3:luma_tmp=6:chroma_tmp=4.5": [
        "--vpp-pmd",
        "apply_count=2,strength=80,threshold=100",
    ],
    "hqdn3d=luma_spatial=10:chroma_spatial=7.5:luma_tmp=15:chroma_tmp=11.25": [
        "--vpp-pmd",
        "apply_count=2,strength=100,threshold=120",
    ],
    # vaguedenoiser weak/moderate/strong -> pmd
    "vaguedenoiser=threshold=1:method=soft:nsteps=5": ["--vpp-pmd", "apply_count=1,strength=50,threshold=80"],
    "vaguedenoiser=threshold=3:method=soft:nsteps=5": ["--vpp-pmd", "apply_count=2,strength=80,threshold=100"],
    "vaguedenoiser=threshold=6:method=soft:nsteps=5": ["--vpp-pmd", "apply_count=2,strength=100,threshold=120"],
}


def rigaya_extra_options(video: Video) -> List[str]:
    """Build extra VPP filter and encoder arguments for rigaya encoders from advanced panel settings."""
    result: List[str] = []
    vs = video.video_settings

    # Equalizer via --vpp-tweak
    tweak_parts = []
    try:
        if vs.brightness is not None and vs.brightness.strip():
            val = float(vs.brightness)
            if val != 0.0:
                tweak_parts.append(f"brightness={max(-1.0, min(1.0, val))}")
    except ValueError:
        logger.warning(f"Invalid brightness value for rigaya: {vs.brightness}")
    try:
        if vs.contrast is not None and vs.contrast.strip():
            val = float(vs.contrast)
            if val != 1.0:
                tweak_parts.append(f"contrast={max(-2.0, min(2.0, val))}")
    except ValueError:
        logger.warning(f"Invalid contrast value for rigaya: {vs.contrast}")
    try:
        if vs.saturation is not None and vs.saturation.strip():
            val = float(vs.saturation)
            if val != 1.0:
                tweak_parts.append(f"saturation={max(0.0, min(3.0, val))}")
    except ValueError:
        logger.warning(f"Invalid saturation value for rigaya: {vs.saturation}")
    try:
        if vs.gamma is not None and vs.gamma.strip():
            val = float(vs.gamma)
            if val != 1.0:
                tweak_parts.append(f"gamma={max(0.1, min(10.0, val))}")
    except ValueError:
        logger.warning(f"Invalid gamma value for rigaya: {vs.gamma}")
    try:
        if vs.hue is not None and vs.hue.strip():
            val = float(vs.hue)
            if val != 0.0:
                tweak_parts.append(f"hue={max(-180.0, min(180.0, val))}")
    except ValueError:
        logger.warning(f"Invalid hue value for rigaya: {vs.hue}")
    if tweak_parts:
        result.extend(["--vpp-tweak", ",".join(tweak_parts)])

    # Unsharp mask (preset-based, takes priority over CAS sharpen for --vpp-unsharp)
    has_unsharp = False
    if vs.unsharp:
        rigaya_unsharp = RIGAYA_UNSHARP_MAP.get(vs.unsharp)
        if rigaya_unsharp:
            result.extend(rigaya_unsharp)
            has_unsharp = True
        else:
            logger.warning(f"No rigaya unsharp mapping for: {vs.unsharp}")

    # Sharpen (CAS) — only apply if unsharp mask is not already set (both use --vpp-unsharp)
    if not has_unsharp:
        try:
            if vs.sharpen is not None and vs.sharpen.strip():
                val = float(vs.sharpen)
                if val > 0:
                    result.extend(["--vpp-unsharp", f"radius=3,weight={max(0.0, min(1.0, val))}"])
        except ValueError:
            logger.warning(f"Invalid sharpen value for rigaya: {vs.sharpen}")

    # Denoise
    if vs.denoise:
        rigaya_denoise = RIGAYA_DENOISE_MAP.get(vs.denoise)
        if rigaya_denoise:
            result.extend(rigaya_denoise)
        else:
            logger.warning(f"No rigaya denoise mapping for: {vs.denoise}")

    # Deblock
    if vs.deblock:
        if vs.deblock == "weak":
            result.extend(["--vpp-deblock", "strength=30"])
        elif vs.deblock == "strong":
            result.extend(["--vpp-deblock", "strength=60"])

    # Curves preset
    if vs.curves_preset:
        result.extend(["--vpp-curves", f"preset={vs.curves_preset}"])

    # LUT3D
    if vs.lut3d_path:
        result.extend(["--vpp-colorspace", f"lut3d={vs.lut3d_path},lut3d_interp=tetrahedral"])

    # Pad / Letterbox
    if vs.pad_aspect and vs.pad_aspect != "none":
        try:
            num, den = vs.pad_aspect.split(":")
            target_ratio = int(num) / int(den)
            # Start with source dimensions, apply crop
            sw = video.width
            sh = video.height
            if vs.crop:
                sw = sw - vs.crop.left - vs.crop.right
                sh = sh - vs.crop.top - vs.crop.bottom
            # If scale is applied, use scaled dimensions for pad calculation
            if video.output_width is not None and video.output_height is not None:
                sw = video.output_width
                sh = video.output_height
            current_ratio = sw / sh if sh else 1
            if current_ratio < target_ratio:
                new_w = int(round(sh * target_ratio / 2) * 2)
                pad_left = (new_w - sw) // 2
                pad_right = new_w - sw - pad_left
                result.extend(["--vpp-pad", f"{pad_left},{0},{pad_right},{0}"])
            elif current_ratio > target_ratio:
                new_h = int(round(sw / target_ratio / 2) * 2)
                pad_top = (new_h - sh) // 2
                pad_bottom = new_h - sh - pad_top
                result.extend(["--vpp-pad", f"{0},{pad_top},{0},{pad_bottom}"])
        except (ValueError, ZeroDivisionError):
            logger.warning(f"Invalid pad aspect for rigaya: {vs.pad_aspect}")

    # Output FPS via --vpp-fps (won't conflict with --fps used for source_fps)
    if vs.output_fps:
        result.extend(["--vpp-fps", f"fps={vs.output_fps}"])

    # Video track title
    if vs.video_track_title:
        result.extend(["--video-metadata", f"title={vs.video_track_title}"])

    # GOP length
    if vs.gop_length is not None:
        result.extend(["--gop-len", str(vs.gop_length)])

    return result
