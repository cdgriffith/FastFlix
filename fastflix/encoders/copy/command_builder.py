# -*- coding: utf-8 -*-
import re
from pprint import pprint
from fastflix.encoders.common.helpers import Command, generate_all
from fastflix.models.fastflix import FastFlix


def build(fastflix: FastFlix):
    beginning, ending, output_fps = generate_all(fastflix, "copy", disable_filters=True)
    rotation = 0
    if not fastflix.current_video.current_video_stream:
        return []
    if "rotate" in fastflix.current_video.current_video_stream.get("tags", {}):
        rotation = abs(int(fastflix.current_video.current_video_stream.tags.rotate))
    elif "rotation" in fastflix.current_video.current_video_stream.get("side_data_list", [{}])[0]:
        rotation = abs(int(fastflix.current_video.current_video_stream.side_data_list[0].rotation))

    rot = ""
    # if fastflix.current_video.video_settings.rotate != 0:
    #     rot = f"-display_rotation:s:v {rotation + (fastflix.current_video.video_settings.rotate * 90)}"
    if fastflix.current_video.video_settings.output_path.name.lower().endswith("mp4"):
        rot = f"-metadata:s:v rotate={rotation + (fastflix.current_video.video_settings.rotate * 90)}"

    return [
        Command(
            command=f"{beginning} {rot} {fastflix.current_video.video_settings.video_encoder_settings.extra} {ending}",
            name="No Video Encoding",
            exe="ffmpeg",
        )
    ]
