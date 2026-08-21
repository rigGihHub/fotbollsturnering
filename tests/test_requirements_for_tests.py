from pathlib import Path

def test_pypdf_dependency_is_declared_for_pdf_tests():
    requirements = Path("requirements.txt").read_text(encoding="utf-8").lower()
    assert "pypdf" in requirements

def test_reportlab_dependency_is_declared_for_pdf_generation():
    requirements = Path("requirements.txt").read_text(encoding="utf-8").lower()
    assert "reportlab" in requirements
