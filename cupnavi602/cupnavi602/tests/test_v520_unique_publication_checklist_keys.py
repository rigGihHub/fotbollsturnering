from pathlib import Path

SRC = Path("cupnavi_core/admin_publication_view.py").read_text(encoding="utf-8")

def test_publication_checklist_uses_unique_key_per_step():
    assert "for step_index, (label, ready, page) in enumerate(steps):" in SRC
    assert 'key=f"publish_check_{tournament_id}_{step_index}_{label}"' in SRC
    assert 'key=f"publish_check_{tournament_id}_{page}"' not in SRC

def test_shared_destination_pages_are_allowed_without_key_collision():
    assert '("Cupinfo", cupinfo_ready, "Cupinställningar")' in SRC
    assert '("Planer & tider", pitches_ready, "Cupinställningar")' in SRC
