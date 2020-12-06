# -*- coding: utf-8 -*-
import re

from fastflix.encoders.common.helpers import Command, generate_all
from fastflix.models.fastflix import FastFlix


def build(fastflix: FastFlix):

    beginning, ending = generate_all(fastflix, "copy", disable_filters=True)

    return [
        Command(
            re.sub("[ ]+", " ", f"{beginning} {ending}"),
            ["ffmpeg", "output"],
            False,
            name="No Video Encoding",
            exe="ffmpeg",
        )
    ]
