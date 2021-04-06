# -*- coding: utf-8 -*-
import re

from fastflix.encoders.common.helpers import Command, generate_all
from fastflix.models.fastflix import FastFlix


def build(fastflix: FastFlix):

    beginning, ending = generate_all(fastflix, "copy", disable_filters=True)

    return [
        Command(
            command=f"{beginning} {fastflix.current_video.video_settings.video_encoder_settings.extra} {ending}",
            name="No Video Encoding",
            exe="ffmpeg",
        )
    ]
