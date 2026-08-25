from pathlib import Path

def test_instruction_buttons_have_unique_keys_per_step():
    text = Path("app.py").read_text(encoding="utf-8")
    section = text[
        text.index('if admin_page == "Instruktioner":'):
        text.index('elif admin_page == "Adminöversikt":')
    ]
    assert "for step_index, step in enumerate(guide_steps, start=1):" in section
    assert 'key=f"guide_open_{tid}_{step_index}_{step[\'page\']}"' in section

def test_instruction_key_is_not_based_only_on_page():
    text = Path("app.py").read_text(encoding="utf-8")
    section = text[
        text.index('if admin_page == "Instruktioner":'):
        text.index('elif admin_page == "Adminöversikt":')
    ]
    assert 'key=f"guide_open_{tid}_{step[\'page\']}"' not in section
