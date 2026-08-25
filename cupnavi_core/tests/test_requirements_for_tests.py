from pathlib import Path

def test_pypdf_dependency_is_declared_for_pdf_tests():
    dev = Path("requirements-dev.txt").read_text(encoding="utf-8").lower()
    assert "pypdf" in dev

def test_reportlab_dependency_is_declared_for_pdf_generation():
    runtime = Path("requirements.txt").read_text(encoding="utf-8").lower()
    assert "reportlab" in runtime
