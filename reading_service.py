"""Pure reading construction helpers."""

from iching_logic import get_hexagram_numbers


def create_reading(question, lines, iching_data, binary_to_hex_map, timestamp):
    """Builds a complete reading dictionary from cast lines and source data."""
    primary_hex_num, secondary_hex_num = get_hexagram_numbers(lines, binary_to_hex_map)
    primary_hex = get_hexagram(iching_data, primary_hex_num, "primary")
    secondary_hex = (
        get_hexagram(iching_data, secondary_hex_num, "secondary")
        if secondary_hex_num
        else None
    )

    return {
        "question": question,
        "lines": lines,
        "primary_hex": primary_hex,
        "secondary_hex": secondary_hex,
        "changing_lines_indices": [
            index for index, line in enumerate(lines) if line in [6, 9]
        ],
        "timestamp": timestamp,
    }


def get_hexagram(iching_data, hexagram_number, label):
    """Returns a hexagram by number with a domain-specific error if missing."""
    hexagram = iching_data.get(str(hexagram_number))
    if not hexagram:
        raise ValueError(f"Missing {label} hexagram data for number: {hexagram_number}")

    return hexagram
