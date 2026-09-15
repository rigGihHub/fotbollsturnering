from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_desktop_public_header_is_compact_without_shrinking_mobile():
    css = (ROOT / "frontend-next/src/app/public-atmosphere-v2671.css").read_text()

    desktop = css.split("@media(min-width:901px){", 1)[1]
    assert ".page-shell--matchday .cup-cover{min-height:0!important" in desktop
    assert "padding:14px 22px 15px!important" in desktop
    assert ".cup-cover__content{margin-top:8px!important" in desktop
    assert ".edition-nav--desktop{margin:10px 0 22px!important" in desktop
    assert ".cup-cover__facts span{padding:4px 8px!important" in desktop
