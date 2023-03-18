# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from subprocess import run, PIPE


@dataclass
class Encoder:
    name = "UNSET"
    device_number: int = 0
    device_name: str = ""
    formats: list[str] = field(default_factory=list)


class VCEEncoder(Encoder):
    name = "VCE"


class NVENCEncoder(Encoder):
    name = "NVENC"


class QSVEncoder(Encoder):
    name = "QSV"


def parse_vce_devices(split_text: list[str]):
    encoder = VCEEncoder()

    for line in split_text:
        line = line.strip()
        if line.startswith("device #"):
            start, end = line.split("#", 1)
            device_number, device_name = end.split(":", 1)
            encoder.device_name = device_name.strip()
            encoder.device_number = int(device_number)

        if line.endswith("encode features"):
            encoder.formats.append(line.split()[0].strip())
    return encoder


def parse_nvenc_devices(split_text: list[str]):
    encoder = NVENCEncoder()

    for line in split_text:
        line = line.strip()
        if line.startswith("#"):
            device_number, device_name = line.split(":", 1)
            encoder.device_name = device_name.split("(", 1)[0].strip()
            encoder.device_number = int(device_number[1:])
        if line.startswith("Codec:"):
            encoder.formats.append(line.split(":", 1)[1].strip())
    return encoder


def parse_qsv_devices(split_text: list[str]):
    encoder = QSVEncoder()

    for line in split_text:
        line = line.strip()
        if line.startswith("GPU"):
            device_name = line.split(":", 1)[1]
            encoder.device_name = device_name.split("(", 1)[0].strip()
        if line.startswith("Codec:"):
            encoder.formats.append(line.split(":", 1)[1].strip())
    return encoder


def run_check_features(executable, encoder="UNSET"):
    outputs = []
    if encoder == "qsv":
        result = run([executable, "--check-features"], stdout=PIPE, stderr=PIPE, encoding="utf-8")
        outputs.append(result.stdout.splitlines())
    else:
        for i in range(10):
            result = run([executable, "--check-features", str(i)], stdout=PIPE, stderr=PIPE, encoding="utf-8")
            if result.stderr:
                break
            outputs.append(result.stdout.splitlines())

    return outputs
