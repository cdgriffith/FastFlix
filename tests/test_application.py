# -*- coding: utf-8 -*-
from box import Box
from qtpy.QtWidgets import QApplication

from fastflix.application import init_encoders

fake_app = QApplication([])
fake_app.fastflix = Box(default_box=True)


def test_init_encoders():
    init_encoders(fake_app)
    assert "encoders" in fake_app.fastflix
