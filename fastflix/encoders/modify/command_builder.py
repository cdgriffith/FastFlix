# -*- coding: utf-8 -*-
from fastflix.encoders.common.helpers import Command, generate_all
from fastflix.models.fastflix import FastFlix
from fastflix.shared import clean_file_string


def build(fastflix: FastFlix):
    beginning, ending, output_fps = generate_all(fastflix, "copy", disable_filters=True, audio=False, subs=False)
    video_title = fastflix.current_video.video_settings.video_title
    video_track_title = fastflix.current_video.video_settings.video_track_title
    ffmpeg = fastflix.config.ffmpeg
    source = fastflix.current_video.source

    if video_title:
        video_title = video_title.replace('"', '\\"')
    title = f'-metadata title="{video_title}"' if video_title else ""
    source = clean_file_string(source)
    ffmpeg = clean_file_string(ffmpeg)
    if video_track_title:
        video_track_title = video_track_title.replace('"', '\\"')
    track_title = f'-metadata:s:v:0 title="{video_track_title}"'

    beginning = " ".join(
        [
            f'"{ffmpeg}"',
            "-y",
            f'-i "{source}"',
            " ",  # Leave space after commands
        ]
    )

    audio = fastflix.current_video.video_settings.video_encoder_settings.add_audio_track
    subs = fastflix.current_video.video_settings.video_encoder_settings.add_subtitle_track

    if audio and subs:
        audio_path_clean = clean_file_string(audio)
        subs_path_clean = clean_file_string(subs)
        return [
            Command(
                command=f'{beginning} -i "{audio_path_clean}" -i "{subs_path_clean}" -map 0 -map 1:a -map 2:s  {title} {track_title if video_track_title else ""} -c copy {fastflix.current_video.video_settings.video_encoder_settings.extra} {ending}',
                name="Add audio and subtitle track",
                exe="ffmpeg",
            )
        ]

    if audio:
        audio_path_clean = clean_file_string(audio)
        return [
            Command(
                command=f'{beginning} -i "{audio_path_clean}" -map 0 -map 1:a {title} {track_title if video_track_title else ""} -c copy {fastflix.current_video.video_settings.video_encoder_settings.extra} {ending}',
                name="Add audio track",
                exe="ffmpeg",
            )
        ]

    if subs:
        subs_path_clean = clean_file_string(subs)
        return [
            Command(
                command=f'{beginning} -i "{subs_path_clean}" -map 0 -map 1:s {title} {track_title if video_track_title else ""} -c copy {fastflix.current_video.video_settings.video_encoder_settings.extra} {ending}',
                name="Add subtitle track",
                exe="ffmpeg",
            )
        ]
