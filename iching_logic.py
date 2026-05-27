import random

COIN_VALUES = (2, 3)
CHANGING_LINES = {6, 9}
YANG_LINES = {7, 9}


def cast_coin_line(coin_toss=None):
    """Casts one I Ching line using the traditional three-coin method."""
    toss = coin_toss or (lambda: random.choice(COIN_VALUES))
    return sum(toss() for _ in range(3))


def cast_reading():
    """Simulates casting 3 coins 6 times to get 6 lines."""
    return [cast_coin_line() for _ in range(6)]

def get_hexagram_numbers(lines, binary_to_hex_map):
    """Determines hexagram numbers from bottom-to-top line values."""
    primary_binary = "".join("1" if line in YANG_LINES else "0" for line in lines)
    primary_num = binary_to_hex_map.get(primary_binary)
    if primary_num is None:
        raise ValueError(f"No hexagram found for primary binary code: {primary_binary}")

    secondary_num = None
    if any(line in CHANGING_LINES for line in lines):
        secondary_lines = [line if line in [7, 8] else (7 if line == 6 else 8) for line in lines]
        secondary_binary = "".join(
            "1" if line in YANG_LINES else "0" for line in secondary_lines
        )
        secondary_num = binary_to_hex_map.get(secondary_binary)
        if secondary_num is None:
            raise ValueError(f"No hexagram found for secondary binary code: {secondary_binary}")

    return primary_num, secondary_num
