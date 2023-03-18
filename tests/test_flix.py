# -*- coding: utf-8 -*-
from pathlib import Path

from box import Box

from fastflix.models.config import Config

from fastflix.rigaya_helpers import parse_vce_devices, VCEEncoder

fake_app = Box(default_box=True)
fake_app.fastflix.config = Config()


def test_parse_vce():
    example_text = """
device #0: AMD Radeon
H.264/AVC encode features
10bit depth:     no
acceleration:    Hardware-accelerated
max profile:     High
max level:       unknown
max bitrate:     2147483 kbps
ref frames:      1-16
Bframe support:  no
HW instances:    1
max streams:     16
timeout support: yes

H.264/AVC input:
Width:       128 - 4096
Height:      128 - 4096
alignment:   32
Interlace:   no
pix format:  NV12[1](native), YUV420P[7], YV12[2], BGRA[3], RGBA[5], ARGB[4]
memory type: DX11(native), OPENCL, OPENGL, HOST

H.264/AVC output:
Width:       128 - 4096
Height:      128 - 4096
alignment:   32
Interlace:   no
pix format:  UNKNOWN[0](native)
memory type: DX11(native), OPENCL, OPENGL, HOST

H.265/HEVC encode features
10bit depth:     yes
acceleration:    Hardware-accelerated
max profile:     main
max level:       unknown
max bitrate:     2147483 kbps
ref frames:      1-16
max streams:     16
timeout support: yes

H.265/HEVC input:
Width:       128 - 4096
Height:      128 - 4096
alignment:   32
Interlace:   no
pix format:  NV12[1](native), YUV420P[7], YV12[2], BGRA[3], RGBA[5], ARGB[4]
memory type: DX11(native), OPENCL, OPENGL, HOST

H.265/HEVC output:
Width:       128 - 4096
Height:      128 - 4096
alignment:   32
Interlace:   no
pix format:  UNKNOWN[0](native)
memory type: DX11(native), OPENCL, OPENGL, HOST"""

    assert parse_vce_devices(example_text.splitlines()) == VCEEncoder(
        device_number=0, device_name="AMD Radeon", encoders=["H.264/AVC", "H.265/HEVC"]
    )
