"""A font cut by code point still works (PLAN 10.3): variations, the regular-script weight
switch and contextual rules survive in a slice that keeps its interacting groups whole."""

from __future__ import annotations

import io

import pytest
from fontTools import subset
from fontTools.ttLib import TTFont

from mapotofu.slices import groups

from .conftest import Shaper

TEXTS = ["->=!=<=", "Wavy AV fi", "——“永国”あ。", "ぁ—（漢）"]
WEIGHTS = (250, 300, 400, 520, 800)


def cut(shaper: Shaper, seed: set[int]) -> Shaper:
    keep = set(seed)
    for g in groups(shaper.tt):
        if g & seed:
            keep |= g
    opts = subset.Options()
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    opts.glyph_names = False
    opts.hinting = False
    font = TTFont(io.BytesIO(shaper.data))
    s = subset.Subsetter(opts)
    s.populate(unicodes=keep)
    s.subset(font)
    buf = io.BytesIO()
    font.save(buf)
    return Shaper(buf.getvalue())


def strip(run):
    return [r[1:] for r in run]


@pytest.mark.parametrize("key", ["Gothic-SC-Upright", "Gothic-SC-Italic", "Mono-J-Upright"])
def test_slice_shapes_like_whole_font(font, key):
    whole = font(key)
    seed = {ord(c) for t in TEXTS for c in t} & whole.cmap.keys()
    part = cut(whole, seed)
    assert "CFF2" in part.tt and "fvar" in part.tt
    assert part.tt["CFF2"].cff.topDictIndex[0].VarStore is not None
    if key.endswith("Italic"):
        assert part.tt["GSUB"].table.FeatureVariations is not None
    for text in TEXTS:
        text = "".join(c for c in text if ord(c) in whole.cmap)
        for w in WEIGHTS:
            for vertical in (False, True):
                assert strip(part.run(text, w, vertical)) == strip(whole.run(text, w, vertical)), (text, w, vertical)


def test_groups_keep_ligatures_together(font):
    mono = font("Mono-J-Upright")
    found = [g for g in groups(mono.tt) if ord("-") in g]
    assert found and ord(">") in found[0]
    gothic = font("Gothic-SC-Upright")
    assert any(0x2014 in g for g in groups(gothic.tt))
