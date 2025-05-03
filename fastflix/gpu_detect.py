# -*- coding: utf-8 -*-
from dataclasses import dataclass
import logging


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


def windows_gpu_detect():
    import wmi

    computer = wmi.WMI()
    gpu_info = computer.Win32_VideoController()
    detected_gpus = DetectGPU()
    fingerprinter = set()
    for adapter in gpu_info:
        adapter_type = adapter.AdapterCompatibility.split()[0].upper()
        if adapter_type == "NVIDIA":
            detected_gpus.NVIDIA = True
            fingerprinter.add(adapter.VideoProcessor)
        elif adapter_type == "AMD":
            detected_gpus.AMD = True
            fingerprinter.add(adapter.VideoProcessor)
        elif adapter_type == "INTEL":
            detected_gpus.INTEL = True
            fingerprinter.add(adapter.VideoProcessor)
    detected_gpus.fingerprint = "~~".join(sorted(list(fingerprinter)))
    return detected_gpus


def gpu_detect():
    if system == "Windows":
        return windows_gpu_detect()
    else:
        print("Unsupported OS")
        return DetectGPU()


def automatic_rigaya_download(config, app, signal, stop_signal):
    if config.gpu_fingerprint:
        logger.debug(f"GPU fingerprint already set: {config.gpu_fingerprint}")
        return
    signal.emit(0)
    gpus = gpu_detect()
    logger.info(f"Detected GPUs: {gpus}")
    if not gpus.exist():
        return
    config.gpu_fingerprint = gpus.fingerprint

    signal.emit(25)

    if not config.seven_zip or not config.seven_zip.exists():
        config.seven_zip = find_seven_zip_windows()
        if not config.seven_zip:
            config.seven_zip = download_7zip(stop_signal)

    signal.emit(50)

    if gpus.NVIDIA and not config.nvencc:
        logger.info("Going to download NVEncC")
        config.nvencc = download_rigaya(stop_signal, seven_zip_path=config.seven_zip, app_name="NVEnc")

    signal.emit(70)
    if gpus.AMD and not config.vceencc:
        logger.info("Going to download VCEncC")
        config.vceencc = download_rigaya(stop_signal, seven_zip_path=config.seven_zip, app_name="VCEEnc")

    signal.emit(90)
    if gpus.INTEL and not config.qsvencc:
        logger.info("Going to download QSVEncC")
        config.qsvencc = download_rigaya(stop_signal, seven_zip_path=config.seven_zip, app_name="QSVEnc")


def update_rigaya_encoders(config, app, signal, stop_signal):
    signal.emit(0)
    gpus = gpu_detect()
    logger.info(f"Detected GPUs: {gpus}")
    if not gpus.exist():
        return
    config.gpu_fingerprint = gpus.fingerprint

    signal.emit(25)

    if not config.seven_zip or not config.seven_zip.exists():
        config.seven_zip = find_seven_zip_windows()
        if not config.seven_zip:
            config.seven_zip = download_7zip(stop_signal)

    signal.emit(50)

    if gpus.NVIDIA:
        logger.info("Going to download NVEncC")
        config.nvencc = download_rigaya(stop_signal, seven_zip_path=config.seven_zip, app_name="NVEnc")

    signal.emit(70)
    if gpus.AMD:
        logger.info("Going to download VCEncC")
        config.vceencc = download_rigaya(stop_signal, seven_zip_path=config.seven_zip, app_name="VCEEnc")

    signal.emit(90)
    if gpus.INTEL:
        logger.info("Going to download QSVEncC")
        config.qsvencc = download_rigaya(stop_signal, seven_zip_path=config.seven_zip, app_name="QSVEnc")
    signal.emit(100)
