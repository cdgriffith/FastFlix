# -*- coding: utf-8 -*-
import secrets
import shlex

from fastflix.encoders.common.hdr_metadata import (
    chromaloc_mapping,
    color_matrix_mapping,
    color_primaries_mapping,
    color_transfer_mapping,
    is_hdr_bit_depth,
    parse_master_display,
    valid_color_matrix,
    valid_color_primaries,
    valid_color_transfers,
)
from fastflix.encoders.common.helpers import Command, generate_all, hevc_tag_args, null
from fastflix.models.encode import x265Settings
from fastflix.models.fastflix import FastFlix


def quote_x265_value(value: str) -> str:
    """Single-quote a value for -x265-params (ffmpeg splits on ':' and honours quotes, so 'C:/x' is kept whole)."""
    return "'" + str(value).replace("'", "'\\''") + "'"


def build(fastflix: FastFlix):
    settings: x265Settings = fastflix.current_video.video_settings.video_encoder_settings

    beginning, ending, output_fps = generate_all(fastflix, "libx265")
    beginning.extend(hevc_tag_args(fastflix.current_video.video_settings.output_path))

    if settings.tune and settings.tune != "default":
        beginning.extend(["-tune:v", settings.tune])

    if settings.profile and settings.profile != "default":
        beginning.extend(["-profile:v", settings.profile])

    x265_params = settings.x265_params.copy() or []

    x265_params.append(f"aq-mode={settings.aq_mode}")
    x265_params.append(f"repeat-headers={'1' if settings.repeat_headers else '0'}")
    x265_params.append(f"{'' if settings.intra_smoothing else 'no-'}strong-intra-smoothing=1")
    x265_params.append(f"bframes={settings.bframes}")
    x265_params.append(f"b-adapt={settings.b_adapt}")
    x265_params.append(f"frame-threads={settings.frame_threads}")

    if not fastflix.current_video.video_settings.remove_hdr:
        if fastflix.current_video.video_settings.color_primaries:
            x265_params.append(f"colorprim={fastflix.current_video.video_settings.color_primaries}")
        elif fastflix.current_video.color_primaries:
            if fastflix.current_video.color_primaries in valid_color_primaries:
                x265_params.append(f"colorprim={fastflix.current_video.color_primaries}")
            elif fastflix.current_video.color_primaries in color_primaries_mapping:
                x265_params.append(f"colorprim={color_primaries_mapping[fastflix.current_video.color_primaries]}")

        if fastflix.current_video.video_settings.color_transfer:
            x265_params.append(f"transfer={fastflix.current_video.video_settings.color_transfer}")
        elif fastflix.current_video.color_transfer:
            if fastflix.current_video.color_transfer in valid_color_transfers:
                x265_params.append(f"transfer={fastflix.current_video.color_transfer}")
            elif fastflix.current_video.color_transfer in color_transfer_mapping:
                x265_params.append(f"transfer={color_transfer_mapping[fastflix.current_video.color_transfer]}")

        if fastflix.current_video.video_settings.color_space:
            x265_params.append(f"colormatrix={fastflix.current_video.video_settings.color_space}")
        elif fastflix.current_video.color_space:
            if fastflix.current_video.color_space in valid_color_matrix:
                x265_params.append(f"colormatrix={fastflix.current_video.color_space}")
            elif fastflix.current_video.color_space in color_matrix_mapping:
                x265_params.append(f"colormatrix={color_matrix_mapping[fastflix.current_video.color_space]}")

        if is_hdr_bit_depth(settings.pix_fmt):
            hdr10 = settings.hdr10
            x265_params.append(f"hdr10_opt={'1' if settings.hdr10_opt else '0'}")

            master_display = parse_master_display(fastflix.current_video.master_display)
            if master_display:
                hdr10 = True
                x265_params.append(f"master-display={master_display.to_x265()}")

            if fastflix.current_video.cll:
                hdr10 = True
                x265_params.append(f"max-cll={fastflix.current_video.cll}")

            x265_params.append(f"hdr10={'1' if hdr10 else '0'}")

        current_chroma_loc = fastflix.current_video.current_video_stream.get("chroma_location")
        if current_chroma_loc in chromaloc_mapping:
            x265_params.append(f"chromaloc={chromaloc_mapping[current_chroma_loc]}")

    if settings.hdr10plus_metadata:
        x265_params.append(f"dhdr10-info='{settings.hdr10plus_metadata}'")
        if settings.dhdr10_opt:
            x265_params.append("dhdr10_opt=1")

    if settings.intra_encoding:
        x265_params.append("keyint=1")

    if settings.intra_refresh:
        x265_params.append("intra-refresh=1")

    if settings.lossless:
        x265_params.append("lossless=1")

    if fastflix.current_video.video_settings.maxrate:
        x265_params.append(f"vbv-maxrate={fastflix.current_video.video_settings.maxrate}")
        x265_params.append(f"vbv-bufsize={fastflix.current_video.video_settings.bufsize}")

    pass_log_file = quote_x265_value(
        (fastflix.current_video.work_path / f"pass_log_file_{secrets.token_hex(10)}.log").as_posix()
    )

    def get_x265_params(params=()):
        if not isinstance(params, (list, tuple)):
            params = [params]
        all_params = x265_params + list(params)
        return ["-x265-params", ":".join(all_params)] if all_params else []

    extra = shlex.split(settings.extra) if settings.extra else []
    extra_both = shlex.split(settings.extra) if settings.extra and settings.extra_both_passes else []

    if settings.lossless:
        # Lossless mode — no rate control needed, x265 handles it via lossless=1 param
        command = beginning + get_x265_params() + ["-preset:v", settings.preset] + extra + ending
        return [Command(command=command, name="Single pass lossless", exe="ffmpeg")]

    if settings.bitrate:
        if settings.bitrate_passes == 2:
            command_1 = (
                beginning
                + get_x265_params(["pass=1", "no-slow-firstpass=1", f"stats={pass_log_file}"])
                + ["-b:v", settings.bitrate, "-preset:v", settings.preset]
                + extra_both
                + ["-an", "-sn", "-dn"]
                + output_fps
                + ["-f", "mp4", null]
            )
            command_2 = (
                beginning
                + get_x265_params(["pass=2", f"stats={pass_log_file}"])
                + ["-b:v", settings.bitrate, "-preset:v", settings.preset]
                + extra
                + ending
            )
            return [
                Command(command=command_1, name="First pass bitrate", exe="ffmpeg"),
                Command(command=command_2, name="Second pass bitrate", exe="ffmpeg"),
            ]
        else:
            command = (
                beginning
                + get_x265_params()
                + ["-b:v", settings.bitrate, "-preset:v", settings.preset]
                + extra
                + ending
            )
            return [Command(command=command, name="Single pass bitrate", exe="ffmpeg")]

    elif settings.crf:
        command = (
            beginning + get_x265_params() + ["-crf:v", str(settings.crf), "-preset:v", settings.preset] + extra + ending
        )
        return [Command(command=command, name="Single pass CRF", exe="ffmpeg")]

    else:
        return []
