import unittest

from iching_logic import cast_coin_line, cast_reading, get_hexagram_numbers


class TestIChingLogic(unittest.TestCase):
    def test_cast_coin_line_maps_three_coin_sums(self):
        cases = [
            ([2, 2, 2], 6),
            ([3, 2, 2], 7),
            ([3, 3, 2], 8),
            ([3, 3, 3], 9),
        ]

        for tosses, expected_line in cases:
            with self.subTest(tosses=tosses):
                toss_iter = iter(tosses)
                self.assertEqual(cast_coin_line(lambda: next(toss_iter)), expected_line)

    def test_cast_reading_returns_six_valid_lines(self):
        lines = cast_reading()

        self.assertEqual(len(lines), 6)
        self.assertTrue(all(line in {6, 7, 8, 9} for line in lines))

    def test_get_hexagram_numbers_transforms_changing_lines(self):
        binary_to_hex_map = {
            "111111": 1,
            "000000": 2,
            "101010": 63,
            "010101": 64,
        }

        primary, secondary = get_hexagram_numbers(
            [6, 9, 6, 9, 6, 9],
            binary_to_hex_map,
        )

        self.assertEqual(primary, 64)
        self.assertEqual(secondary, 63)

    def test_get_hexagram_numbers_raises_for_missing_primary_mapping(self):
        with self.assertRaisesRegex(ValueError, "primary binary code: 111111"):
            get_hexagram_numbers([9, 9, 9, 9, 9, 9], {})

    def test_get_hexagram_numbers_raises_for_missing_secondary_mapping(self):
        binary_to_hex_map = {
            "111111": 1,
        }

        with self.assertRaisesRegex(ValueError, "secondary binary code: 000000"):
            get_hexagram_numbers([9, 9, 9, 9, 9, 9], binary_to_hex_map)


if __name__ == "__main__":
    unittest.main()
