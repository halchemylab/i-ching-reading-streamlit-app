import unittest

from reading_service import create_reading


SAMPLE_ICHING_DATA = {
    "1": {
        "number": 1,
        "name_en": "The Creative",
        "name_zh": "乾",
    },
    "2": {
        "number": 2,
        "name_en": "The Receptive",
        "name_zh": "坤",
    },
}


class TestReadingService(unittest.TestCase):
    def test_create_reading_builds_primary_and_secondary_hexagrams(self):
        lines = [6, 7, 8, 9, 7, 8]
        binary_to_hex_map = {
            "011010": 1,
            "010011": 2,
        }

        reading = create_reading(
            question="What needs attention?",
            lines=lines,
            iching_data=SAMPLE_ICHING_DATA,
            binary_to_hex_map=binary_to_hex_map,
            timestamp="2026-05-24 09:30:00",
        )

        self.assertEqual(reading["question"], "What needs attention?")
        self.assertEqual(reading["lines"], lines)
        self.assertEqual(reading["primary_hex"], SAMPLE_ICHING_DATA["1"])
        self.assertEqual(reading["secondary_hex"], SAMPLE_ICHING_DATA["2"])
        self.assertEqual(reading["changing_lines_indices"], [0, 3])
        self.assertEqual(reading["timestamp"], "2026-05-24 09:30:00")

    def test_create_reading_handles_stable_reading(self):
        reading = create_reading(
            question="Where should I wait?",
            lines=[7, 7, 8, 8, 7, 8],
            iching_data=SAMPLE_ICHING_DATA,
            binary_to_hex_map={"010011": 2},
            timestamp="2026-05-24 09:45:00",
        )

        self.assertEqual(reading["primary_hex"], SAMPLE_ICHING_DATA["2"])
        self.assertIsNone(reading["secondary_hex"])
        self.assertEqual(reading["changing_lines_indices"], [])

    def test_create_reading_rejects_missing_hexagram_data(self):
        with self.assertRaisesRegex(ValueError, "Missing primary hexagram data"):
            create_reading(
                question="What is missing?",
                lines=[7, 7, 7, 7, 7, 7],
                iching_data=SAMPLE_ICHING_DATA,
                binary_to_hex_map={"111111": 99},
                timestamp="2026-05-24 10:00:00",
            )


if __name__ == "__main__":
    unittest.main()
