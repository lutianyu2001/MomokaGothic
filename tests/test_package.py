"""The desktop files (second step) agree with the variable fonts of the first step."""

from __future__ import annotations

from pathlib import Path

import pytest
import uharfbuzz as hb
from fontTools.ttLib import TTFont

from mapotofu.build import pools
from mapotofu.package import DIST, file_name

from .conftest import FONTS

SAMPLE = "Aa永国あ。—“"


def _hb(path: Path, index: int = 0) -> hb.Font:
    return hb.Font(hb.Face(hb.Blob.from_file_path(str(path)), index))


def _extents(font: hb.Font, tt: TTFont, text: str, wght: float | None):
    """Advance and extents of the glyph each character shapes to (so that rvrn, which a static
    italic bakes into its cmap, is applied to the variable font too)."""
    if wght is not None:
        font.set_variations({"wght": wght})
    cmap = tt.getBestCmap()
    out = []
    for ch in text:
        if ord(ch) not in cmap:
            continue
        buf = hb.Buffer()
        buf.add_str(ch)
        buf.guess_segment_properties()
        hb.shape(font, buf, {})
        gid = buf.glyph_infos[0].codepoint
        e = font.get_glyph_extents(gid)
        out.append((ch, buf.glyph_positions[0].x_advance, e and (e.x_bearing, e.y_bearing, e.width, e.height)))
    return out


def _close(a, b, tol=2):
    assert [x[:2] for x in a] == [x[:2] for x in b]
    for (_, _, ea), (_, _, eb) in zip(a, b):
        assert (ea is None) == (eb is None)
        if ea:
            assert max(abs(p - q) for p, q in zip(ea, eb)) <= tol, (ea, eb)


VIEWS = [v for vs in pools().values() for v in vs]


@pytest.mark.parametrize("view", VIEWS, ids=lambda v: v.key)
def test_standalone_files_match_first_step(view):
    src = FONTS / f"{view.key}.otf"
    var = DIST / "variable" / file_name(view, None)
    if not (src.exists() and var.exists()):
        pytest.skip("not packaged")
    whole = TTFont(src)
    text = SAMPLE if not view.is_ext else "".join(chr(c) for c in sorted(whole.getBestCmap())[:50])
    single = TTFont(var)
    assert single.getBestCmap() == whole.getBestCmap()
    shared = any(view in vs and len(vs) > 1 for vs in pools().values())
    assert single["maxp"].numGlyphs < whole["maxp"].numGlyphs or not shared
    for w in (250, 400, 650, 800):
        _close(_extents(_hb(var), single, text, w), _extents(_hb(src), whole, text, w))
    from mapotofu.config import STATIC_WEIGHTS

    for weight, value in STATIC_WEIGHTS.items():
        st = DIST / "static" / file_name(view, weight)
        if st.exists():
            _close(_extents(_hb(st), TTFont(st), text, None), _extents(_hb(src), whole, text, value))


def test_collections_store_shared_tables_once():
    for path in sorted((DIST / "otc").glob("*.otc")) if (DIST / "otc").exists() else []:
        from fontTools.ttLib import TTCollection

        from mapotofu.build import pools

        coll = TTCollection(path, lazy=True)
        offsets = {}
        for font in coll.fonts:
            for tag in ("CFF ", "CFF2"):
                if tag in font.reader.tables:
                    offsets.setdefault(tag, set()).add(font.reader.tables[tag].offset)
        ext, italic = path.name.startswith("MomokaExt"), "Italic" in path.name
        expected = sum(any(v.is_ext == ext and v.italic == italic for v in vs) for vs in pools().values())
        for tag, offs in offsets.items():
            assert len(offs) == expected, (path.name, tag, len(offs))  # one per pool
