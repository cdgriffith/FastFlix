# -*- coding: utf-8 -*-
import os
from pathlib import Path
from pgsrip import pgsrip, Mkv, Options
from babelfish import Language

# Set up environment for tesseract and mkvextract
# Update these paths to match your system
tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
mkvtoolnix_path = r"C:\Program Files\MKVToolNix"

if Path(tesseract_path).exists():
    tesseract_dir = str(Path(tesseract_path).parent)
    os.environ["PATH"] = f"{tesseract_dir}{os.pathsep}{os.environ.get('PATH', '')}"
    os.environ["TESSERACT_CMD"] = tesseract_path

if Path(mkvtoolnix_path).exists():
    os.environ["PATH"] = f"{mkvtoolnix_path}{os.pathsep}{os.environ.get('PATH', '')}"

video = r"F:/Uncompressed Videos/Blade/Blade (1998) [imdbid-tt0120611]/Blade_t00.mkv"
media = Mkv(video)
options = Options(languages={Language("eng")}, overwrite=True, one_per_lang=True)

print("Starting OCR conversion...")
pgsrip.rip(media, options)
print("Done!")
