# -*- coding: utf-8 -*-
import importlib.util
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _load_build_distribution():
    spec = importlib.util.spec_from_file_location("build_distribution", ROOT / "scripts" / "build_distribution.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_configure_pth_file_adds_lib_and_pywin32_dirs(tmp_path):
    """#774: lib/pywin32.pth is never processed for ../lib, so its dirs must be in the ._pth file."""
    pth = tmp_path / "python313._pth"
    pth.write_text("python313.zip\n.\n\n# Uncomment to run site.main() automatically\n#import site\n")

    _load_build_distribution().configure_pth_file(tmp_path)

    lines = pth.read_text().splitlines()
    assert "import site" in lines
    assert "#import site" not in lines
    for entry in ("../lib", "../lib/win32", "../lib/win32/lib", "../lib/Pythonwin"):
        assert lines.count(entry) == 1


def test_configure_pth_file_is_idempotent(tmp_path):
    pth = tmp_path / "python313._pth"
    pth.write_text("python313.zip\n.\n#import site\n")
    module = _load_build_distribution()
    module.configure_pth_file(tmp_path)
    first = pth.read_text()
    module.configure_pth_file(tmp_path)
    assert pth.read_text() == first
