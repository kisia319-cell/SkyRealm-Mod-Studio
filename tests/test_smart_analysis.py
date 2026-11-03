import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.smart_analysis import scan_javascript


class SmartAnalysisTests(unittest.TestCase):
    def test_ignores_patterns_inside_strings(self):
        findings = scan_javascript('const text = "console.log( TODO eval( )";\n')
        self.assertEqual(findings, [])

    def test_ignores_patterns_inside_comments_except_todo(self):
        findings = scan_javascript('// console.log(1); TODO finish\n/* while(true) FIXME */\n')
        self.assertEqual(len(findings), 2)
        self.assertTrue(all("незавершённая" in item[1] for item in findings))

    def test_finds_actual_risky_code(self):
        findings = scan_javascript('eval("x");\nwhile (true) {}\nconsole.log("x");\n')
        self.assertEqual(len(findings), 3)
        self.assertEqual([item[0] for item in findings], [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
