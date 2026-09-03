from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
STYLE = (ROOT / "cupnavi_core" / "style_system.py").read_text(encoding="utf-8")
VERSION_PY = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")
RELEASE = "2026.09.03-423-PUBLIC-INFO-COLD-START"


def test_v289_release_is_synced():
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == RELEASE
    assert f'APP_BUILD_VERSION = "{RELEASE}"' in APP
    assert f'APP_VERSION = "{RELEASE}"' in VERSION_PY


def test_sidebar_version_is_derived_from_current_release():
    assert "def release_ui_label" in VERSION_PY
    assert 'return f"Version v1.{serial}"' in VERSION_PY
    assert "st.sidebar.caption(release_ui_label(APP_BUILD_VERSION))" in APP
    assert "Version v.1.266" not in APP


def test_mobile_wide_rows_wrap_without_changing_small_forms():
    assert ':has(> [data-testid="column"]:nth-child(4))' in STYLE
    assert "flex-wrap:wrap!important" in STYLE
    assert "min-width:calc(50% - 5px)!important" in STYLE
    # The rule deliberately starts at four columns so ordinary 2/3-column forms
    # keep their current desktop/mobile semantics.
    assert ':nth-child(3)' not in STYLE[STYLE.index("/* v1.289:"):STYLE.index(".public-metric-grid", STYLE.index("/* v1.289:"))]


def test_mobile_metric_labels_can_wrap():
    assert '[data-testid="stMetric"]{min-width:0!important}' in STYLE
    assert '[data-testid="stMetricLabel"]{white-space:normal!important;line-height:1.2!important}' in STYLE
