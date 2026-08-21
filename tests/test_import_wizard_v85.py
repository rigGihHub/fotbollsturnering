from pathlib import Path

def app_text():
    return Path("app.py").read_text(encoding="utf-8")

def test_import_is_five_step_guided_flow():
    text=app_text()
    assert "cn-import-steps" in text
    for step in ("Välj typ","Ladda upp","Matcha kolumner","Granska","Importera"):
        assert step in text

def test_import_has_column_mapping_and_auto_detection():
    text=app_text()
    assert "auto_map_columns(import_df.columns, fields)" in text
    assert "— Använd inte —" in text

def test_import_has_review_metrics_and_confirmation():
    text=app_text()
    assert '"Redo att importera"' in text
    assert '"Hoppar över"' in text
    assert '"Fel att rätta"' in text
    assert "Jag har granskat importen" in text

def test_csv_uses_separator_and_encoding_detection():
    text=app_text()
    assert 'sep=None' in text
    assert '"utf-8-sig", "utf-8", "cp1252", "latin-1"' in text

def test_xlsx_supports_sheet_selection():
    text=app_text()
    assert "pd.ExcelFile" in text
    assert "excel_file.sheet_names" in text

def test_import_is_transactional_and_marks_schedule_dirty_for_teams():
    text=app_text()
    start=text.index('if admin_page == "Import":')
    end=text.index('if admin_page == "Tabeller":',start)
    block=text[start:end]
    assert 'con.execute("BEGIN IMMEDIATE")' in block
    assert "con.rollback()" in block
    assert "schedule_dirty=1,is_published=0" in block

def test_import_can_download_error_report():
    text=app_text()
    assert "Ladda ner felrapport" in text
