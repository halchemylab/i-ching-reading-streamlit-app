import random
import streamlit as st

COIN_VALUES = (2, 3)


def cast_coin_line(coin_toss=None):
    """Casts one I Ching line using the traditional three-coin method."""
    toss = coin_toss or (lambda: random.choice(COIN_VALUES))
    return sum(toss() for _ in range(3))


def cast_reading():
    """Simulates casting 3 coins 6 times to get 6 lines."""
    return [cast_coin_line() for _ in range(6)]

def get_hexagram_numbers(lines, binary_to_hex_map):
    """Determines the primary and secondary hexagram numbers from the lines using a pre-computed map."""
    primary_binary = "".join(['1' if l in [7, 9] else '0' for l in reversed(lines)])
    primary_num = binary_to_hex_map.get(primary_binary)

    secondary_num = None
    if any(line in [6, 9] for line in lines):
        secondary_lines = [l if l in [7, 8] else (7 if l == 6 else 8) for l in lines]
        secondary_binary = "".join(['1' if l in [7, 9] else '0' for l in reversed(secondary_lines)])
        secondary_num = binary_to_hex_map.get(secondary_binary)
    
    if primary_num is None: 
        st.warning("Could not determine primary hexagram. Defaulting to 1.")
        primary_num = 1
    if secondary_num is None and any(line in [6, 9] for line in lines): 
        st.warning("Could not determine evolving hexagram. Defaulting to 2.")
        secondary_num = 2

    return primary_num, secondary_num
