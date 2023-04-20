# -*- coding: utf-8 -*-
from dataclasses import dataclass, field, asdict
from subprocess import run, PIPE


@dataclass
class Encoder:
    name = "UNSET"
    device_number: int = 0
    device_name: str = ""
    formats: list[str] = field(default_factory=list)


@dataclass
class VCEEncoder(Encoder):
    name = "VCE"


@dataclass
class NVENCEncoder(Encoder):
    name = "NVENC"


@dataclass
class QSVEncoder(Encoder):
    name = "QSV"


def parse_vce_devices(split_text: list[str]) -> VCEEncoder:
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


def parse_nvenc_devices(split_text: list[str]) -> NVENCEncoder:
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


def parse_qsv_devices(split_text: list[str]) -> QSVEncoder:
    encoder = QSVEncoder()

    for line in split_text:
        line = line.strip()
        if line.startswith("GPU"):
            device_name = line.split(":", 1)[1]
            encoder.device_name = device_name.split("(", 1)[0].strip()
        if line.startswith("Codec:"):
            encoder.formats.append(line.split(":", 1)[1].strip())
    return encoder


def run_check_features(executable, is_qsv=False):
    outputs = []
    if is_qsv:
        result = run([executable, "--check-features"], stdout=PIPE, stderr=PIPE, encoding="utf-8")
        outputs.append(result.stdout.splitlines())
    else:
        for i in range(10):
            result = run([executable, "--check-features", str(i)], stdout=PIPE, stderr=PIPE, encoding="utf-8")
            if result.stderr:
                break
            outputs.append(result.stdout.splitlines())

    return outputs


def get_all_encoder_formats_and_devices(executable, is_qsv=False, is_nvenc=False, is_vce=False) -> (dict, list[str]):
    devices = {}
    encoders = set()
    for output in run_check_features(executable=executable, is_qsv=is_qsv):
        if is_vce:
            data = parse_vce_devices(output)
            encoders.update(data.formats)
        elif is_nvenc:
            data = parse_nvenc_devices(output)
            encoders.update(data.formats)
        elif is_qsv:
            data = parse_qsv_devices(output)
            data.formats = [x.split(" ")[0] for x in data.formats]
            encoders.update(data.formats)
        else:
            raise Exception("Must set at least one encoder type")
        devices[data.device_number] = {"name": data.device_name, "encoders": data.formats}
    return devices, list(encoders)
