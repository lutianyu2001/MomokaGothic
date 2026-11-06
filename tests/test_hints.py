"""The hint cache (mapotofu.hintcache) on the built fonts: hints put back into a glyph's own
charstring are those otfautohint gave it."""

from __future__ import annotations

import pytest
from fontTools.ttLib import TTFont

from mapotofu import hintcache
from mapotofu.package import POOLED

from .conftest import FONTS


def test_cached_hints_are_otfautohints():
    """Hints taken out of an otfautohint result and put back into the unhinted charstring give
    the same stems, masks and outline (checked on a sample of glyphs)."""
    from mapotofu import hint

    unhinted_path, hinted_path = FONTS / "Ext-TC-Upright.otf", POOLED / "VF" / "Ext-TC-Upright.otf"
    if not (unhinted_path.exists() and hinted_path.exists()):
        pytest.skip("not built")
    u, h = TTFont(unhinted_path), TTFont(hinted_path)
    order = u.getGlyphOrder()
    h.setGlyphOrder(order)
    hint.set_zones(u)
    ucs, hcs = u["CFF2"].cff.topDictIndex[0].CharStrings, h["CFF2"].cff.topDictIndex[0].CharStrings
    kinds = []
    for name in order[::25]:
        entry = hintcache.extract(ucs[name], hcs[name])
        kinds.append(entry.kind)
        if entry.kind != "h":
            continue
        rebuilt = type(hcs[name])(program=hintcache.apply(entry, ucs[name]), private=hcs[name].private)
        _, head, masks, path = hintcache.split(hintcache.commands(rebuilt))
        _, head2, masks2, path2 = hintcache.split(hintcache.commands(hcs[name]))
        assert hintcache.canonical(head) == hintcache.canonical(head2), name
        if path == path2:
            assert masks == masks2, name
        else:  # otfautohint dropped a moveto: compare on its outline
            normal, index = hintcache.normalize(path)
            assert hintcache.same(normal, path2), name
            assert masks == [(index[p] if p < len(index) else len(path), op, m) for p, op, m in masks2], name
    assert kinds.count("h") > 0.95 * len(kinds)
