#!/usr/bin/env python
# -*- coding: utf-8 -*-
import shutil
from pathlib import Path

here = Path(__file__).parent


def build(*_, **__):
    shutil.copy(here / "CHANGES", here / "fastflix" / "CHANGES")
