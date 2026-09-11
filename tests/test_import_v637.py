from io import BytesIO
import unittest

from openpyxl import Workbook

from cupnavi_api.import_repository import _parse


class ImportV637Tests(unittest.TestCase):
    def test_swedish_semicolon_csv_headers(self):
        rows = _parse("Lag;Åldersklass;Grupp\nÖSK P12;P12;Grupp A\n".encode("utf-8"), "lag.csv")
        self.assertEqual(rows[0]["name"], "ÖSK P12")
        self.assertEqual(rows[0]["age_class"], "P12")
        self.assertEqual(rows[0]["group"], "Grupp A")

    def test_xlsx_headers(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["Lagnamn", "Grupp", "Primärfärg"])
        sheet.append(["Adolfsberg", "Grupp B", "#112233"])
        stream = BytesIO()
        workbook.save(stream)
        workbook.close()
        rows = _parse(stream.getvalue(), "teams.xlsx")
        self.assertEqual(rows[0]["name"], "Adolfsberg")
        self.assertEqual(rows[0]["primary_color"], "#112233")

    def test_name_column_is_required(self):
        with self.assertRaisesRegex(ValueError, "lagnamn"):
            _parse("Grupp;Åldersklass\nA;P11\n".encode("utf-8"), "teams.csv")

    def test_unsupported_file_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "CSV och XLSX"):
            _parse(b"x", "teams.pdf")


if __name__ == "__main__":
    unittest.main()
