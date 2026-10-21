# -*- coding: utf-8 -*-
from dataclasses import dataclass
import logging
import re


from fastflix.program_downloads import find_seven_zip_windows, download_rigaya, download_7zip

import platform

system = platform.system()
logger = logging.getLogger("fastflix")


@dataclass
class DetectGPU:
    NVIDIA: bool = False
    AMD: bool = False
    INTEL: bool = False
    fingerprint: str = None

    def exist(self):
        return self.NVIDIA or self.AMD or self.INTEL

    def __str__(self):
        output = "GPU types detected: "
        if self.NVIDIA:
            output += " NVIDIA "
        if self.AMD:
            output += " AMD "
        if self.INTEL:
            output += " INTEL "
        return output


def classify_vendor(name: str | None) -> str | None:
    """Map a WMI AdapterCompatibility string to NVIDIA / AMD / INTEL, or None if unknown."""
    if not name:
        return None
    lowered = name.lower()
    if "nvidia" in lowered:
        return "NVIDIA"
    if "advanced micro devices" in lowered or "ati technologies" in lowered or re.search(r"\bamd\b", lowered):
        return "AMD"
    if "intel" in lowered:
        return "INTEL"
    return None


def windows_gpu_detect():
    import wmi

    computer = wmi.WMI()
    gpu_info = computer.Win32_VideoController()
    detected_gpus = DetectGPU()
    fingerprinter = set()
    for adapter in gpu_info:
        vendor = classify_vendor(adapter.AdapterCompatibility)
        if vendor is None:
            continue
        setattr(detected_gpus, vendor, True)
        if adapter.VideoProcessor:
            fingerprinter.add(adapter.VideoProcessor)
    detected_gpus.fingerprint = "~~".join(sorted(fingerprinter))
    return detected_gpus


def gpu_detect():
    if system == "Windows":
        return windows_gpu_detect()
    else:
        print("Unsupported OS")
        return DetectGPU()


def _ensure_seven_zip(config, stop_signal) -> bool:
    if not config.seven_zip or not config.seven_zip.exists():
        config.seven_zip = find_seven_zip_windows() or download_7zip(stop_signal)
    if not config.seven_zip:
        logger.error("7-Zip is not available (download cancelled or failed), cannot download encoders")
        return False
    return True


def _download_encoders(config, gpus, signal, stop_signal, only_missing: bool) -> bool:
    """Download rigaya encoders for detected GPUs. Returns True only if every requested download succeeded."""
    if not _ensure_seven_zip(config, stop_signal):
        return False

    ok = True
    for percent, present, attr, app_name in (
        (50, gpus.NVIDIA, "nvencc", "NVEnc"),
        (70, gpus.AMD, "vceencc", "VCEEnc"),
        (90, gpus.INTEL, "qsvencc", "QSVEnc"),
    ):
        signal.emit(percent)
        if not present or (only_missing and getattr(config, attr)):
            continue
        logger.info(f"Going to download {app_name}")
        result = download_rigaya(stop_signal, seven_zip_path=config.seven_zip, app_name=app_name)
        if result:
            setattr(config, attr, result)
        else:
            logger.error(f"Could not download {app_name}")
            ok = False
    return ok


def automatic_rigaya_download(config, app, signal, stop_signal):
    if config.gpu_fingerprint:
        logger.debug(f"GPU fingerprint already set: {config.gpu_fingerprint}")
        return
    signal.emit(0)
    gpus = gpu_detect()
    logger.info(f"Detected GPUs: {gpus}")
    if not gpus.exist():
        return

    signal.emit(25)
    if _download_encoders(config, gpus, signal, stop_signal, only_missing=True):
        config.gpu_fingerprint = gpus.fingerprint


def update_rigaya_encoders(config, app, signal, stop_signal):
    signal.emit(0)
    gpus = gpu_detect()
    logger.info(f"Detected GPUs: {gpus}")
    if not gpus.exist():
        return

    signal.emit(25)
    if _download_encoders(config, gpus, signal, stop_signal, only_missing=False):
        config.gpu_fingerprint = gpus.fingerprint
    signal.emit(100)
