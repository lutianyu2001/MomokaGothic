"""Line metrics of the built fonts."""

from __future__ import annotations

import pytest
from fontTools.ttLib import TTFont

from mapotofu.build import all_views

from .conftest import FONTS


@pytest.mark.parametrize("view", all_views(), ids=lambda v: v.key)
def test_windows_metrics_cover_every_glyph(view):
    # Windows clips what passes usWinAscent and usWinDescent.
    path = FONTS / f"{view.key}.otf"
    if not path.exists():
        pytest.skip("not built")
    font = TTFont(path)
    head, os2 = font["head"], font["OS/2"]
    assert os2.usWinAscent >= head.yMax and os2.usWinDescent >= -head.yMin
    assert os2.usWinAscent >= os2.sTypoAscender and os2.usWinDescent >= -os2.sTypoDescender
