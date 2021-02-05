#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path

from box import Box

from fastflix.models.queue import get_queue

here = Path(__file__).parent


def test_queue_load():
    get_queue(here / "media" / "queue.yaml")
