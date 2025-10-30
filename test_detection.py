# -*- coding: utf-8 -*-
import sys

sys.path.insert(0, ".")

from fastflix.models.config import find_ocr_tool

print("Testing tesseract detection...")
tesseract = find_ocr_tool("tesseract")
print(f"Tesseract found at: {tesseract}")

print("\nTesting mkvmerge detection...")
mkvmerge = find_ocr_tool("mkvmerge")
print(f"MKVMerge found at: {mkvmerge}")
