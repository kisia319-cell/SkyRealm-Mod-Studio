import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from editors.debugger_tools import parse_breakpoints


class DebuggerUtilityTests(unittest.TestCase):
    def test_parses_and_deduplicates_breakpoints(self):
        self.assertEqual(parse_breakpoints("1, 4, 4, 12"), [1, 4, 12])

    def test_rejects_invalid_breakpoints(self):
        for value in ("0", "-1", "abc", "2.5"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_breakpoints(value)


if __name__ == "__main__":
    unittest.main()
