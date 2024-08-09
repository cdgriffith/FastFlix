#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import platform


def write_and_exit(msg):
    sys.stdout.write(msg)
    sys.stdout.flush()
    sys.exit(0)


write_and_exit("arm64" if "arm64" in platform.platform() else "x86_64")
