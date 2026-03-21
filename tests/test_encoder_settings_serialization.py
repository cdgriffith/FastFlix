# -*- coding: utf-8 -*-
import warnings

import pytest

from fastflix.models.encode import setting_types
from fastflix.models.video import VideoSettings


@pytest.mark.parametrize("encoder_name,settings_cls", list(setting_types.items()), ids=list(setting_types.keys()))
def test_encoder_settings_serialization_no_warnings(encoder_name, settings_cls):
    """Every encoder settings type must serialize through VideoSettings without Pydantic warnings.

    This catches missing entries in the VideoSettings.video_encoder_settings Union type,
    which is exactly the bug that occurred when FFmpegAV1NVENCSettings was added to
    models/encode.py but not to the Union in models/video.py.
    """
    settings = settings_cls()
    vs = VideoSettings(video_encoder_settings=settings)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        data = vs.model_dump()

    pydantic_warnings = [w for w in caught if "PydanticSerializationUnexpectedValue" in str(w.message)]
    assert not pydantic_warnings, (
        f"Pydantic serialization warnings for {encoder_name} ({settings_cls.__name__}). "
        f"Did you forget to add it to the Union in VideoSettings.video_encoder_settings (models/video.py)?"
    )

    restored = VideoSettings.model_validate(data)
    assert restored.video_encoder_settings is not None
