"""The tests shape the fonts built in this project (build/fonts) with HarfBuzz."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import uharfbuzz as hb
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MAPOTOFU_ROOT", str(ROOT))
FONTS = ROOT / "build" / "fonts"


class Shaper:
    def __init__(self, path: Path | bytes) -> None:
        import io

        data = path if isinstance(path, bytes) else Path(path).read_bytes()
        self.data = data
        self.font = hb.Font(hb.Face(hb.Blob(data)))
        self.tt = TTFont(io.BytesIO(data))
        self.cmap = self.tt.getBestCmap()
        self.order = self.tt.getGlyphOrder()

    def shape(self, text: str, wght: float = 400, vertical: bool = False, lang: str | None = None):
        """[(glyph name, x advance, y advance)]"""
        return [(self.order[g], xa, ya) for g, xa, ya, *_ in self.run(text, wght, vertical, lang)]

    def run(self, text: str, wght: float = 400, vertical: bool = False, lang: str | None = None):
        """[(glyph ID, x advance, y advance, x offset, y offset, extents)]"""
        self.font.set_variations({"wght": wght})
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        if vertical:
            buf.direction = "ttb"
        if lang:
            buf.language = lang
        hb.shape(self.font, buf, {})
        out = []
        for i, p in zip(buf.glyph_infos, buf.glyph_positions):
            e = self.font.get_glyph_extents(i.codepoint)
            ext = (e.x_bearing, e.y_bearing, e.width, e.height) if e else None
            out.append((i.codepoint, p.x_advance, p.y_advance, p.x_offset, p.y_offset, ext))
        return out

    def extents(self, gid: int, wght: float):
        self.font.set_variations({"wght": wght})
        e = self.font.get_glyph_extents(gid)
        return (e.x_bearing, e.y_bearing, e.width, e.height)


@pytest.fixture(scope="session")
def font():
    cache: dict[str, Shaper] = {}

    def get(key: str) -> Shaper:
        path = FONTS / f"{key}.otf"
        if not path.exists():
            pytest.skip(f"{path.name} not built (mapo fonts --only {key})")
        if key not in cache:
            cache[key] = Shaper(path)
        return cache[key]

    return get
