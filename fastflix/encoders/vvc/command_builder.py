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
from fastflix.encoders.common.helpers import Command, generate_all, null
from fastflix.models.encode import VVCSettings
from fastflix.models.fastflix import FastFlix


def build(fastflix: FastFlix):
    settings: VVCSettings = fastflix.current_video.video_settings.video_encoder_settings

    beginning, ending, output_fps = generate_all(fastflix, "libvvenc")

    if settings.tier:
        beginning.extend(["-tier:v", settings.tier])

    if settings.levelidc:
        beginning.extend(["-level", settings.levelidc])

    if not settings.subjopt:
        beginning.extend(["-qpa", "0"])

    if settings.period is not None:
        beginning.extend(["-period", str(settings.period)])

    if settings.threads > 0:
        beginning.extend(["-threads", str(settings.threads)])

    vvc_params = settings.vvc_params.copy() or []

    if settings.ifp:
        vvc_params.append("ifp=1")

    if not fastflix.current_video.video_settings.remove_hdr:
        # Color primaries/transfer/matrix via FFmpeg flags (libvvenc reads these for VUI)
        if fastflix.current_video.video_settings.color_primaries:
            beginning.extend(["-color_primaries", fastflix.current_video.video_settings.color_primaries])
        elif fastflix.current_video.color_primaries:
            cp = fastflix.current_video.color_primaries
            cp = color_primaries_mapping.get(cp, cp)
            if cp in valid_color_primaries:
                beginning.extend(["-color_primaries", cp])

        if fastflix.current_video.video_settings.color_transfer:
            beginning.extend(["-color_trc", fastflix.current_video.video_settings.color_transfer])
        elif fastflix.current_video.color_transfer:
            ct = fastflix.current_video.color_transfer
            ct = color_transfer_mapping.get(ct, ct)
            if ct in valid_color_transfers:
                beginning.extend(["-color_trc", ct])

        if fastflix.current_video.video_settings.color_space:
            beginning.extend(["-colorspace", fastflix.current_video.video_settings.color_space])
        elif fastflix.current_video.color_space:
            cs = fastflix.current_video.color_space
            cs = color_matrix_mapping.get(cs, cs)
            if cs in valid_color_matrix:
                beginning.extend(["-colorspace", cs])

        if is_hdr_bit_depth(settings.pix_fmt):
            master_display = parse_master_display(fastflix.current_video.master_display)
            if master_display:
                vvc_params.append(f"MasteringDisplayColourVolume={master_display.to_vvenc()}")

            if fastflix.current_video.cll:
                vvc_params.append(f"MaxContentLightLevel={fastflix.current_video.cll}")

        current_chroma_loc = fastflix.current_video.current_video_stream.get("chroma_location")
        if current_chroma_loc in chromaloc_mapping:
            beginning.extend(["-chroma_sample_location", str(chromaloc_mapping[current_chroma_loc])])

    pass_log_file = fastflix.current_video.work_path / f"pass_log_file_{secrets.token_hex(10)}"

    vvenc_params = ["-vvenc-params", ":".join(vvc_params)] if vvc_params else []

    extra = shlex.split(settings.extra) if settings.extra else []
    extra_both = shlex.split(settings.extra) if settings.extra and settings.extra_both_passes else []

    if settings.bitrate:
        command_1 = (
            beginning
            + vvenc_params
            + ["-pass", "1", "-passlogfile", str(pass_log_file), "-b:v", settings.bitrate, "-preset:v", settings.preset]
            + extra_both
            + ["-an", "-sn", "-dn"]
            + output_fps
            + ["-f", "mp4", null]
        )
        command_2 = (
            beginning
            + vvenc_params
            + ["-pass", "2", "-passlogfile", str(pass_log_file), "-b:v", settings.bitrate, "-preset:v", settings.preset]
            + extra
            + ending
        )
        return [
            Command(command=command_1, name="First pass bitrate", exe="ffmpeg"),
            Command(command=command_2, name="Second pass bitrate", exe="ffmpeg"),
        ]

    elif settings.qp:
        command = (
            beginning
            + vvenc_params
            + ["-qp:v", str(settings.qp), "-b:v", "0", "-preset:v", settings.preset]
            + extra
            + ending
        )
        return [Command(command=command, name="Single pass CRF", exe="ffmpeg")]

    else:
        return []
