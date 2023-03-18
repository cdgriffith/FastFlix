# -*- coding: utf-8 -*-
from dataclasses import dataclass
from subprocess import run, PIPE


@dataclass
class VCEEncoder:
    device_number: int
    device_name: str
    encoders: list[str]


def parse_vce_devices(split_text: list[str]):
    device_number = 0
    device_name = ""
    encoders = []

    for line in split_text:
        line = line.strip()
        if line.startswith("device #"):
            start, end = line.split("#", 1)
            device_number, device_name = end.split(":", 1)
        if line.endswith("encode features"):
            encoders.append(line.split()[0])

    return VCEEncoder(device_number=int(device_number), device_name=device_name.strip(), encoders=encoders)


def run_check_features(executable):
    outputs = []
    for i in range(10):
        result = run([executable, "--check-features", str(i)], stdout=PIPE, stderr=PIPE, encoding="utf-8")
        if result.stderr:
            break
        outputs.append(result.stdout.splitlines())

    return outputs
