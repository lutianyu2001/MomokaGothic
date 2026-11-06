"""What the fonts do with text (SPEC 3, 4, PLAN 5), checked by shaping with HarfBuzz."""

from __future__ import annotations

import pytest


def adv(shaper, text, **kw):
    return [a for _, a, _ in shaper.shape(text, **kw)]


@pytest.mark.parametrize("region", ["SC", "TC", "J"])
def test_quotes_and_dashes_by_family(font, region):
    gothic = font(f"Gothic-{region}-Upright")
    assert adv(gothic, "“”‘’") == [1000] * 4
    assert adv(gothic, "—…") == [1000, 1000]
    assert adv(gothic, "·") == [1000]
    mono = font(f"Mono-{region}-Upright")
    assert adv(mono, "“”—…·") == [500] * 5
    ui = font(f"UI-{region}-Upright")
    assert all(a < 1000 for a in adv(ui, "“”"))
    assert adv(ui, "—") == [1000]


def test_mono_widths_are_half_or_full(font):
    mono = font("Mono-J-Upright")
    text = "aW0@→★■あア漢，。「」"
    for w in (250, 400, 800):
        assert set(adv(mono, text, wght=w)) <= {500, 1000}
    assert adv(mono, "aW0@") == [500] * 4
    assert adv(mono, "あ漢，") == [1000] * 3


def test_mono_ligatures(font):
    mono = font("Mono-J-Upright")
    lig = [g for g, _, _ in mono.shape("->")]
    plain = [mono.order[mono.tt.getGlyphID(mono.cmap[ord(c)])] for c in "->"]
    assert lig != plain


def test_ui_tabular_figures(font):
    ui = font("UI-SC-Upright")
    assert len(set(adv(ui, "0123456789"))) == 1


def test_continuation_dash(font):
    gothic = font("Gothic-SC-Upright")
    one = gothic.shape("—")
    many = gothic.shape("———")
    assert many[0][0] == one[0][0]
    assert many[1][0] != one[0][0] and many[1][0] == many[2][0]


def test_vertical_em_dash_uses_horizontal_bar_form(font):
    gothic = font("Gothic-SC-Upright")
    assert gothic.shape("—", vertical=True)[0][0] == gothic.shape("―", vertical=True)[0][0]


def test_no_hangul(font):
    for key in ("Gothic-SC-Upright", "Mono-J-Upright"):
        cmap = font(key).cmap
        assert not any(0xAC00 <= cp <= 0xD7AF or 0x1100 <= cp <= 0x11FF for cp in cmap)


def test_ideographs_split_into_tiers(font):
    from mapotofu.tiers import tiers

    t = tiers()
    main = font("Gothic-SC-Upright").cmap
    ext = font("Ext-SC-Upright").cmap
    shared = font("Ext-CJK-Upright").cmap
    assert t.main["SC"] <= main.keys()
    assert not (t.ext["SC"] & main.keys())
    assert t.ext["SC"] <= ext.keys()
    assert t.shared <= shared.keys()


@pytest.mark.parametrize("key", ["Gothic-SC-Italic", "Gothic-J-Italic", "Ext-CJK-Italic"])
def test_italic_regular_script_switches_with_weight(font, key):
    from mapotofu.config import KAI_SOURCES
    from mapotofu.sources import kai

    f = font(key)
    gb = kai(KAI_SOURCES["gbR"]).cmap
    ch = "永" if ord("永") in f.cmap else chr(next(cp for cp in sorted(f.cmap) if cp in gb and cp > 0x3400))
    if key.startswith("Gothic-J"):  # two weights of Klee One
        light, regular = (f.shape(ch, wght=w)[0][0] for w in (300, 400))
        assert light != regular and f.shape(ch, wght=800)[0][0] == regular
        return
    light, regular, medium = (f.shape(ch, wght=w)[0][0] for w in (300, 400, 600))
    assert len({light, regular, medium}) == 3
    assert f.shape(ch, wght=250)[0][0] == light
    assert f.shape(ch, wght=800)[0][0] == medium
    assert regular == f.order[f.tt.getGlyphID(f.cmap[ord(ch)])]


def test_italic_latin_varies_and_ideographs_do_not(font):
    f = font("Gothic-SC-Italic")
    a = f.tt.getGlyphID(f.cmap[ord("a")])
    yong = f.tt.getGlyphID(f.cmap[ord("永")])
    assert f.extents(a, 300) != f.extents(a, 700)
    assert f.extents(yong, 400) == f.extents(yong, 420)


def test_pool_shares_glyph_tables():
    from mapotofu.assemble import POOLED
    from mapotofu.build import pools

    from .conftest import FONTS

    for pool, views in pools().items():
        paths = [FONTS / f"{v.key}.otf" for v in views]
        if len(paths) < 2 or not all(p.exists() for p in paths):
            continue
        from fontTools.ttLib import TTFont

        fonts = [TTFont(p, lazy=True) for p in paths]
        for tag in POOLED:
            assert len({f.reader[tag] for f in fonts}) == 1, (pool, tag)


@pytest.mark.parametrize("key", ["Gothic-SC-Upright", "Gothic-SC-Italic", "Mono-J-Upright"])
def test_one_feature_per_tag_in_each_language_system(font, key):
    from mapotofu.layout import langsystems

    tt = font(key).tt
    for tag in ("GSUB", "GPOS"):
        t = tt[tag].table
        for script, lang, ls in langsystems(t):
            tags = [t.FeatureList.FeatureRecord[i].FeatureTag for i in ls.FeatureIndex]
            assert len(tags) == len(set(tags)), (tag, script, lang)


def test_latin_kerning(font):
    f = font("Gothic-SC-Italic")
    assert adv(f, "Wa")[0] < adv(f, "W")[0]
