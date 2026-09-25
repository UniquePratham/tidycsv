"""Automated tests for the TidyCSV cleaning core (run from this directory:
python test_tidycsv.py)."""
import io
import sys
import tempfile
import unittest
from pathlib import Path

import tidycsv


class ParseTests(unittest.TestCase):
    def test_basic_parse(self):
        headers, rows = tidycsv.parse("a,b,c\n1,2,3\n4,5,6\n")
        self.assertEqual(headers, ["a", "b", "c"])
        self.assertEqual(rows, [["1", "2", "3"], ["4", "5", "6"]])

    def test_bom_is_stripped(self):
        headers, _ = tidycsv.parse("﻿name,email\nx,y@z.io\n")
        self.assertEqual(headers[0], "name")

    def test_ragged_rows_are_padded(self):
        _, rows = tidycsv.parse("a,b,c\n1,2\n3,4,5,6\n")
        self.assertEqual(rows[0], ["1", "2", ""])
        self.assertEqual(rows[1], ["3", "4", "5"])

    def test_quoted_fields_with_commas(self):
        headers, rows = tidycsv.parse('note,value\n"hello, world",1\n')
        self.assertEqual(headers, ["note", "value"])
        self.assertEqual(rows[0][0], "hello, world")

    def test_empty_input(self):
        self.assertEqual(tidycsv.parse(""), ([], []))


class DetectTests(unittest.TestCase):
    def test_whitespace_and_empty_and_duplicate(self):
        text = "name,email\n Alice ,a@example.com\n\n Alice ,a@example.com\n"
        headers, rows = tidycsv.parse(text)
        rules = {i.rule for i in tidycsv.detect(headers, rows)}
        self.assertIn("whitespace", rules)
        self.assertIn("empty_rows", rules)
        self.assertIn("duplicate_rows", rules)

    def test_header_noise(self):
        headers, rows = tidycsv.parse("name,name,\n,,1\n")
        issues = tidycsv.detect(headers, rows)
        noise = [i for i in issues if i.rule == "header_noise"]
        self.assertEqual(len(noise), 2)  # duplicate + blank

    def test_invalid_email_flagged(self):
        headers, rows = tidycsv.parse("email\nnot-an-email\nok@example.com\n")
        issues = tidycsv.detect(headers, rows)
        bad = [i for i in issues if i.rule == "invalid_email"]
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0].original, "not-an-email")

    def test_mixed_dates_flagged(self):
        headers, rows = tidycsv.parse(
            "when\n2024-01-05\n13/01/2024\n05.02.2024\n2024-03-09\n2024-04-10\n"
        )
        issues = tidycsv.detect(headers, rows)
        self.assertIn("mixed_dates", {i.rule for i in issues})

    def test_uniform_dates_not_flagged_as_mixed(self):
        headers, rows = tidycsv.parse("when\n2024-01-05\n2024-02-06\n2024-03-07\n")
        issues = tidycsv.detect(headers, rows)
        self.assertNotIn("mixed_dates", {i.rule for i in issues})

    def test_clean_file_has_no_issues(self):
        headers, rows = tidycsv.parse("id,name\n1,alice\n2,bob\n")
        self.assertEqual(tidycsv.detect(headers, rows), [])


class ToIsoTests(unittest.TestCase):
    def test_iso_passthrough(self):
        self.assertEqual(tidycsv.to_iso("2024-01-05"), "2024-01-05")

    def test_unambiguous_day_first(self):
        self.assertEqual(tidycsv.to_iso("25/12/2024"), "2024-12-25")

    def test_unambiguous_month_first(self):
        self.assertEqual(tidycsv.to_iso("03/15/2024"), "2024-03-15")

    def test_ambiguous_left_untouched(self):
        self.assertIsNone(tidycsv.to_iso("03/04/2024"))
        self.assertIsNone(tidycsv.to_iso("03.04.2024"))

    def test_non_date_returns_none(self):
        self.assertIsNone(tidycsv.to_iso("hello"))


class CleanTests(unittest.TestCase):
    def test_strips_and_drops(self):
        headers, rows = tidycsv.parse("name,email\n Alice ,a@x.io\n\n Alice ,a@x.io\n")
        out_headers, out_rows, notes = tidycsv.clean(headers, rows)
        self.assertEqual(out_headers, ["name", "email"])
        self.assertEqual(out_rows, [["Alice", "a@x.io"]])
        joined = " ".join(notes)
        self.assertIn("dropped 1 empty row(s)", joined)
        self.assertIn("dropped 1 duplicate row(s)", joined)

    def test_header_repair(self):
        headers, rows = tidycsv.parse("name,name\n,\n")
        out_headers, _, notes = tidycsv.clean(headers, rows)
        self.assertEqual(out_headers, ["name", "name_2"])
        self.assertTrue(any("header" in n for n in notes))

    def test_unambiguous_dates_normalized(self):
        headers, rows = tidycsv.parse("when\n2024-01-05\n13/01/2024\n13/02/2024\n")
        _, out_rows, notes = tidycsv.clean(headers, rows)
        self.assertEqual(out_rows[1], ["2024-01-13"])
        self.assertEqual(out_rows[2], ["2024-02-13"])
        self.assertTrue(any("date" in n for n in notes))

    def test_ambiguous_dates_kept(self):
        headers, rows = tidycsv.parse("when\n05/06/2024\n07/08/2024\n")
        _, out_rows, _ = tidycsv.clean(headers, rows)
        self.assertEqual(out_rows[0], ["05/06/2024"])

    def test_invalid_email_not_silently_rewritten(self):
        headers, rows = tidycsv.parse("email\nnot-an-email\n")
        _, out_rows, _ = tidycsv.clean(headers, rows)
        self.assertEqual(out_rows, [["not-an-email"]])

    def test_no_op_clean_reports_nothing_to_do(self):
        headers, rows = tidycsv.parse("id\n1\n")
        _, _, notes = tidycsv.clean(headers, rows)
        self.assertEqual(notes, ["no changes needed"])


class RenderRoundtripTests(unittest.TestCase):
    def test_report_contains_counts(self):
        headers, rows = tidycsv.parse("name\n Alice \n")
        text = tidycsv.render(headers, rows, tidycsv.detect(headers, rows))
        self.assertIn("whitespace", text)
        self.assertIn("TidyCSV report", text)

    def test_report_clean_file(self):
        headers, rows = tidycsv.parse("id\n1\n")
        text = tidycsv.render(headers, rows, [])
        self.assertIn("No issues found.", text)

    def test_to_csv_roundtrip(self):
        headers, rows = tidycsv.parse('note,value\n"a, b",1\n')
        again_headers, again_rows = tidycsv.parse(tidycsv.to_csv(headers, rows))
        self.assertEqual(again_headers, headers)
        self.assertEqual(again_rows, rows)


class CliTests(unittest.TestCase):
    def _write(self, text):
        tmp = tempfile.NamedTemporaryFile(
            "w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        )
        tmp.write(text)
        tmp.close()
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))
        return tmp.name

    def test_report_only(self):
        source = self._write("name,email\n Alice ,bad\n")
        captured = io.StringIO()
        original = sys.stdout
        sys.stdout = captured
        try:
            code = tidycsv.main([source, "--report-only"])
        finally:
            sys.stdout = original
        self.assertEqual(code, 0)
        self.assertIn("whitespace", captured.getvalue())

    def test_output_written(self):
        source = self._write("name,email\n Alice ,a@x.io\n\n Alice ,a@x.io\n")
        out = self._write("placeholder,ignore\nx,y\n")
        code = tidycsv.main([source, "-o", out])
        self.assertEqual(code, 0)
        result = Path(out).read_text(encoding="utf-8")
        self.assertIn("Alice", result)
        self.assertNotIn("placeholder", result)

    def test_missing_file_returns_2(self):
        self.assertEqual(tidycsv.main(["no-such-file.csv", "--report-only"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
