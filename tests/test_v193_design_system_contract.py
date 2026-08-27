from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text().strip()
def test_v193_design_system():
 assert "CUPNAVI PRODUCT DESIGN SYSTEM v1.193" in APP
 assert "inject_v193_product_design_system()" in APP
def test_tokens():
 for t in ["--cn-color-primary:","--cn-color-secondary:","--cn-color-accent:","--cn-color-bg:","--cn-color-surface:","--cn-color-border:","--cn-color-text:","--cn-color-success:","--cn-color-warning:","--cn-color-error:","--cn-color-info:","--cn-space-1:","--cn-space-8:","--cn-radius-sm:","--cn-radius-lg:"]: assert t in APP
def test_accessibility_responsive():
 for t in ["focus-visible","@media(prefers-reduced-motion:reduce)","--cn-control-h:44px","overflow-x:hidden!important","@media(max-width:390px)","@media(min-width:1440px)"]: assert t in APP
def test_release():
 assert VERSION=="2026.08.27-233-E2E-SUBMIT-HARDENING"
 assert "Version v.1.233" in APP
