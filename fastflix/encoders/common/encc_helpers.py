# -*- coding: utf-8 -*-
import logging

from fastflix.models.video import SubtitleTrack, AudioTrack
from fastflix.encoders.common.audio import lossless
from fastflix.models.fastflix import FastFlix
from fastflix.models.encode import VCEEncCAVCSettings, VCEEncCAV1Settings, VCEEncCSettings

logger = logging.getLogger("fastflix")


def rigaya_avformat_reader(fastflix: FastFlix) -> str:
    # Avisynth reader 	avs
    # VapourSynth reader 	vpy
    # avi reader 	avi
    # y4m reader 	y4m
    # raw reader 	yuv
    # avhw/avsw reader 	others
    ending = fastflix.current_video.source.suffix
    if fastflix.current_video.video_settings.video_encoder_settings.decoder not in ("Hardware", "Software"):
        if ending.lower() in (".avs", ".vpy", ".avi", ".y4m", ".yuv"):
            return ""
    return "--avhw" if fastflix.current_video.video_settings.video_encoder_settings.decoder == "Hardware" else "--avsw"


def rigaya_auto_options(fastflix: FastFlix) -> str:
    reader_format = rigaya_avformat_reader(fastflix)
    if not reader_format:
        output = ""
        if fastflix.current_video.video_settings.color_space:
            output += f"--colormatrix {fastflix.current_video.video_settings.color_space} "
        if fastflix.current_video.video_settings.color_transfer:
            output += f"--transfer {fastflix.current_video.video_settings.color_transfer} "
        if fastflix.current_video.video_settings.color_primaries:
            output += f"--colorprim {fastflix.current_video.video_settings.color_primaries} "
        return output

    return " ".join(
        [
            "--chromaloc auto",
            "--colorrange auto",
            "--colormatrix",
            (fastflix.current_video.video_settings.color_space or "auto"),
            "--transfer",
            (fastflix.current_video.video_settings.color_transfer or "auto"),
            "--colorprim",
            (fastflix.current_video.video_settings.color_primaries or "auto"),
        ]
    )


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


def build_audio(audio_tracks: list[AudioTrack], audio_streams):
    command_list = []
    copies = []
    track_ids = set()
    stream_ids = get_stream_pos(audio_streams)

    for track in sorted(audio_tracks, key=lambda x: x.outdex):
        if track.index in track_ids:
            logger.warning("*EncC does not support copy and duplicate of audio tracks!")
        track_ids.add(track.index)
        audio_id = stream_ids[track.index]
        if track.language:
            command_list.append(f"--audio-metadata {audio_id}?language={track.language}")
        if not track.conversion_codec or track.conversion_codec == "none":
            copies.append(str(audio_id))
        elif track.conversion_codec:
            downmix = f"--audio-stream {audio_id}?:{track.downmix}" if track.downmix else ""
            bitrate = ""
            if track.conversion_codec not in lossless:
                bitrate = f"--audio-bitrate {audio_id}?{track.conversion_bitrate.rstrip('k')} "
            command_list.append(
                f"{downmix} --audio-codec {audio_id}?{track.conversion_codec} {bitrate} "
                f"--audio-metadata {audio_id}?clear"
            )

        if track.title:
            command_list.append(
                f'--audio-metadata {audio_id}?title="{track.title}" '
                f'--audio-metadata {audio_id}?handler="{track.title}" '
            )

        added = ""
        for disposition, is_set in track.dispositions.items():
            if is_set:
                added += f"{disposition},"
        if added:
            command_list.append(f"--audio-disposition {audio_id}?{added.rstrip(',')}")
        else:
            command_list.append(f"--audio-disposition {audio_id}?unset")

    return f" --audio-copy {','.join(copies)} {' '.join(command_list)}" if copies else f" {' '.join(command_list)}"


def build_subtitle(subtitle_tracks: list[SubtitleTrack], subtitle_streams, video_height: int) -> str:
    command_list = []
    copies = []
    stream_ids = get_stream_pos(subtitle_streams)

    scale = ",scale=2.0" if video_height > 1800 else ""

    for track in sorted(subtitle_tracks, key=lambda x: x.outdex):
        sub_id = stream_ids[track.index]
        if track.burn_in:
            command_list.append(f"--vpp-subburn track={sub_id}{scale}")
        else:
            copies.append(str(sub_id))
            added = ""
            for disposition, is_set in track.dispositions.items():
                if is_set:
                    added += f"{disposition},"
            if added:
                command_list.append(f"--sub-disposition {sub_id}?{added.rstrip(',')}")
            else:
                command_list.append(f"--sub-disposition {sub_id}?unset")

            command_list.append(f"--sub-metadata  {sub_id}?language='{track.language}'")

    commands = f" --sub-copy {','.join(copies)} {' '.join(command_list)}" if copies else f" {' '.join(command_list)}"
    if commands:
        return f"{commands} -m default_mode:infer_no_subs"
    return ""
