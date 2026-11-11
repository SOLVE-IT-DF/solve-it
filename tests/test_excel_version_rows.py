"""The Excel workbook's Info sheet carries the knowledge base version record."""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestExcelVersionRows(unittest.TestCase):

    def test_info_sheet_has_the_version_rows(self):
        info = json.loads((ROOT / "data" / "solveit_version.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "kb.xlsx"
            subprocess.run([sys.executable, str(ROOT / "reporting_scripts" / "generate_excel_from_kb.py"),
                            "-o", str(out)], cwd=ROOT, check=True, capture_output=True)
            with zipfile.ZipFile(out) as z:
                strings = [re.sub(r"<[^>]+>", "", m) for m in
                           re.findall(r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode(), re.S)]
        pairs = dict(zip(strings, strings[1:]))
        self.assertEqual(pairs.get("Data version"), info["version"])
        self.assertEqual(pairs.get("Schema version"), info["schema"])
        self.assertEqual(pairs.get("Source commit"), info["commit"])
        self.assertEqual(pairs.get("Commit time (UTC)"), info["committed_at"])


if __name__ == "__main__":
    unittest.main()
