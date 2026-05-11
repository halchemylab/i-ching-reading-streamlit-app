import unittest

from ui_components import format_changing_lines, get_key_takeaway


SAMPLE_PRIMARY_HEX = {
    "number": 11,
    "name_en": "Peace",
}

SAMPLE_SECONDARY_HEX = {
    "number": 32,
    "name_en": "Duration",
}


class TestUIComponents(unittest.TestCase):
    def test_get_key_takeaway_summarizes_evolving_reading(self):
        reading = {
            "primary_hex": SAMPLE_PRIMARY_HEX,
            "secondary_hex": SAMPLE_SECONDARY_HEX,
            "changing_lines_indices": [2],
        }

        takeaway = get_key_takeaway(reading)

        self.assertIn("begins with Peace", takeaway)
        self.assertIn("moves toward Duration", takeaway)
        self.assertIn("line 3", takeaway)

    def test_get_key_takeaway_summarizes_stable_reading(self):
        reading = {
            "primary_hex": SAMPLE_PRIMARY_HEX,
            "secondary_hex": None,
            "changing_lines_indices": [],
        }

        takeaway = get_key_takeaway(reading)

        self.assertIn("centers on Peace", takeaway)
        self.assertIn("With no changing lines", takeaway)

    def test_format_changing_lines_handles_multiple_lines(self):
        self.assertEqual(format_changing_lines([0]), "line 1")
        self.assertEqual(format_changing_lines([0, 5]), "lines 1 and 6")
        self.assertEqual(format_changing_lines([0, 2, 5]), "lines 1, 3, and 6")


if __name__ == "__main__":
    unittest.main()
