# -*- coding: utf-8 -*-
import shlex

from fastflix.encoders.common.helpers import Command, generate_all
from fastflix.models.fastflix import FastFlix


def build(fastflix: FastFlix):
    beginning, ending, output_fps = generate_all(fastflix, "copy", disable_filters=True, audio=False, subs=False)
    video_title = fastflix.current_video.video_settings.video_title
    video_track_title = fastflix.current_video.video_settings.video_track_title
    ffmpeg = fastflix.config.ffmpeg
    source = fastflix.current_video.source

    beginning = [str(ffmpeg), "-y", "-i", str(source)]

    title = ["-metadata", f"title={video_title}"] if video_title else []
    track_title = ["-metadata:s:v:0", f"title={video_track_title}"] if video_track_title else []

    extra = (
        shlex.split(fastflix.current_video.video_settings.video_encoder_settings.extra)
        if fastflix.current_video.video_settings.video_encoder_settings.extra
        else []
    )

    audio = fastflix.current_video.video_settings.video_encoder_settings.add_audio_track
    subs = fastflix.current_video.video_settings.video_encoder_settings.add_subtitle_track

    if audio and subs:
        return [
            Command(
                command=(
                    beginning
                    + ["-i", str(audio), "-i", str(subs)]
                    + ["-map", "0", "-map", "1:a", "-map", "2:s"]
                    + title
                    + track_title
                    + ["-c", "copy"]
                    + extra
                    + ending
                ),
                name="Add audio and subtitle track",
                exe="ffmpeg",
            )
        ]

    if audio:
        return [
            Command(
                command=(
                    beginning
                    + ["-i", str(audio)]
                    + ["-map", "0", "-map", "1:a"]
                    + title
                    + track_title
                    + ["-c", "copy"]
                    + extra
                    + ending
                ),
                name="Add audio track",
                exe="ffmpeg",
            )
        ]

    if subs:
        return [
            Command(
                command=(
                    beginning
                    + ["-i", str(subs)]
                    + ["-map", "0", "-map", "1:s"]
                    + title
                    + track_title
                    + ["-c", "copy"]
                    + extra
                    + ending
                ),
                name="Add subtitle track",
                exe="ffmpeg",
            )
        ]
