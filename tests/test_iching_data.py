import unittest

from file_handler import EXPECTED_BINARY_CODES, load_iching_data
from iching_logic import get_hexagram_numbers


class TestIChingData(unittest.TestCase):
    def setUp(self):
        load_iching_data.cache_clear()

    def test_real_source_data_has_complete_unique_hexagram_map(self):
        iching_data, binary_to_hex_map = load_iching_data()

        self.assertEqual(len(iching_data), 64)
        self.assertEqual(set(iching_data), {str(number) for number in range(1, 65)})
        self.assertEqual(len(binary_to_hex_map), 64)
        self.assertEqual(set(binary_to_hex_map), EXPECTED_BINARY_CODES)

    def test_hexagram_48_is_present(self):
        iching_data, binary_to_hex_map = load_iching_data()

        self.assertEqual(binary_to_hex_map["011010"], 48)
        self.assertEqual(iching_data["48"]["name_en"], "The Well")
        self.assertEqual(len(iching_data["48"]["lines"]), 6)

    def test_every_stable_line_pattern_maps_to_hexagram(self):
        _, binary_to_hex_map = load_iching_data()

        for binary_code, expected_hexagram in binary_to_hex_map.items():
            with self.subTest(binary_code=binary_code):
                lines = [7 if bit == "1" else 8 for bit in binary_code]

                primary, secondary = get_hexagram_numbers(lines, binary_to_hex_map)

                self.assertEqual(primary, expected_hexagram)
                self.assertIsNone(secondary)


if __name__ == "__main__":
    unittest.main()
