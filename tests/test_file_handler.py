import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from file_handler import (
    JournalValidationError,
    enrich_journal,
    journal_to_markdown,
    load_journal,
    parse_lines,
    reconstruct_reading_from_row,
    save_reading_to_csv,
    update_journal_entry_flags,
)


SAMPLE_ICHING_DATA = {
    "1": {
        "number": 1,
        "name_en": "The Creative",
        "name_zh": "乾",
        "judgment_en": "Creative strength.",
        "image_en": "Heaven moves strongly.",
        "lines": [
            {"line_en": "Hidden dragon."},
            {"line_en": "Dragon in the field."},
            {"line_en": "Careful effort."},
            {"line_en": "Leaping dragon."},
            {"line_en": "Flying dragon."},
            {"line_en": "Arrogant dragon."},
        ],
    },
    "2": {
        "number": 2,
        "name_en": "The Receptive",
        "name_zh": "坤",
        "judgment_en": "Receptive strength.",
        "image_en": "Earth receives.",
        "lines": [
            {"line_en": "Frost underfoot."},
            {"line_en": "Straight and square."},
            {"line_en": "Hidden lines."},
            {"line_en": "Tied sack."},
            {"line_en": "Yellow lower garment."},
            {"line_en": "Dragons battle."},
        ],
    },
}


class TestFileHandler(unittest.TestCase):
    def test_save_and_load_journal_round_trip(self):
        reading = {
            "timestamp": "2026-05-03 14:30:00",
            "question": "What needs attention?",
            "lines": [6, 7, 8, 9, 7, 8],
            "primary_hex": SAMPLE_ICHING_DATA["1"],
            "secondary_hex": SAMPLE_ICHING_DATA["2"],
            "ai_interpretation": "Notice the pattern.",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = Path(temp_dir) / "journal.csv"

            with patch("file_handler.JOURNAL_FILE", str(journal_path)):
                save_reading_to_csv(reading)
                loaded_df = load_journal()

        self.assertEqual(len(loaded_df), 1)
        self.assertEqual(loaded_df.loc[0, "Question"], "What needs attention?")
        self.assertEqual(loaded_df.loc[0, "Lines"], "6,7,8,9,7,8")
        self.assertEqual(loaded_df.loc[0, "Primary Hexagram Number"], 1)
        self.assertEqual(loaded_df.loc[0, "Evolving Hexagram Number"], 2)
        self.assertEqual(loaded_df.loc[0, "AI Interpretation"], "Notice the pattern.")
        self.assertFalse(loaded_df.loc[0, "Favorite"])
        self.assertFalse(loaded_df.loc[0, "Archived"])
        self.assertTrue(str(loaded_df.loc[0, "Entry ID"]).strip())

    def test_save_reading_preserves_existing_journal_entries(self):
        first_reading = {
            "timestamp": "2026-05-03 14:30:00",
            "question": "What needs attention?",
            "lines": [6, 7, 8, 9, 7, 8],
            "primary_hex": SAMPLE_ICHING_DATA["1"],
            "secondary_hex": None,
        }
        second_reading = {
            "timestamp": "2026-05-04 09:15:00",
            "question": "Where should I wait?",
            "lines": [7, 7, 8, 8, 7, 8],
            "primary_hex": SAMPLE_ICHING_DATA["2"],
            "secondary_hex": None,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = Path(temp_dir) / "journal.csv"

            with patch("file_handler.JOURNAL_FILE", str(journal_path)):
                save_reading_to_csv(first_reading)
                save_reading_to_csv(second_reading)
                loaded_df = load_journal()

        self.assertEqual(
            list(loaded_df["Question"]),
            ["What needs attention?", "Where should I wait?"],
        )

    def test_load_journal_returns_empty_dataframe_for_missing_or_empty_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = Path(temp_dir) / "missing.csv"

            with patch("file_handler.JOURNAL_FILE", str(journal_path)):
                self.assertTrue(load_journal().empty)

            journal_path.touch()

            with patch("file_handler.JOURNAL_FILE", str(journal_path)):
                self.assertTrue(load_journal().empty)

    def test_load_journal_raises_for_malformed_csv(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = Path(temp_dir) / "journal.csv"
            journal_path.write_text(
                'Date,Question\n2026-05-03,"unterminated question\n',
                encoding="utf-8",
            )

            with patch("file_handler.JOURNAL_FILE", str(journal_path)):
                with self.assertRaisesRegex(
                    JournalValidationError,
                    "Could not parse journal file",
                ):
                    load_journal()

    def test_save_reading_does_not_overwrite_malformed_journal(self):
        reading = {
            "timestamp": "2026-05-03 14:30:00",
            "question": "What needs attention?",
            "lines": [6, 7, 8, 9, 7, 8],
            "primary_hex": SAMPLE_ICHING_DATA["1"],
            "secondary_hex": None,
        }
        malformed_csv = 'Date,Question\n2026-05-03,"unterminated question\n'

        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = Path(temp_dir) / "journal.csv"
            journal_path.write_text(malformed_csv, encoding="utf-8")

            with patch("file_handler.JOURNAL_FILE", str(journal_path)):
                with self.assertRaisesRegex(
                    JournalValidationError,
                    "Could not parse journal file",
                ):
                    save_reading_to_csv(reading)

            self.assertEqual(journal_path.read_text(encoding="utf-8"), malformed_csv)

    def test_load_journal_adds_missing_columns_for_partial_csv(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = Path(temp_dir) / "journal.csv"
            pd.DataFrame([{"Date": "2026-05-03 14:30:00"}]).to_csv(journal_path, index=False)

            with patch("file_handler.JOURNAL_FILE", str(journal_path)):
                loaded_df = load_journal()

        self.assertIn("Question", loaded_df.columns)
        self.assertIn("Lines", loaded_df.columns)
        self.assertIn("AI Interpretation", loaded_df.columns)
        self.assertIn("Favorite", loaded_df.columns)
        self.assertIn("Archived", loaded_df.columns)
        self.assertIn("Entry ID", loaded_df.columns)
        self.assertIsNone(loaded_df.loc[0, "Question"])
        self.assertFalse(loaded_df.loc[0, "Favorite"])
        self.assertFalse(loaded_df.loc[0, "Archived"])

    def test_enrich_journal_adds_display_and_filter_fields(self):
        journal_df = pd.DataFrame(
            [
                {
                    "Date": "2026-05-03 14:30:00",
                    "Question": "What needs attention?",
                    "Lines": "6,7,8,9,7,8",
                    "Primary Hexagram Number": "1",
                    "Evolving Hexagram Number": "2",
                    "AI Interpretation": "Notice the pattern.",
                },
                {
                    "Date": "not-a-date",
                    "Question": "Where should I wait?",
                    "Lines": "7,7,8,8,7,8",
                    "Primary Hexagram Number": "99",
                    "Evolving Hexagram Number": None,
                    "AI Interpretation": "   ",
                },
            ]
        )

        enriched_df = enrich_journal(journal_df, SAMPLE_ICHING_DATA)

        self.assertEqual(enriched_df.loc[0, "Primary Hexagram"], "1: The Creative")
        self.assertEqual(enriched_df.loc[0, "Evolving Hexagram"], "2: The Receptive")
        self.assertTrue(enriched_df.loc[0, "Has AI Contemplation"])
        self.assertTrue(enriched_df.loc[0, "Has Changing Lines"])
        self.assertEqual(enriched_df.loc[1, "Primary Hexagram"], "99")
        self.assertFalse(enriched_df.loc[1, "Has AI Contemplation"])
        self.assertFalse(enriched_df.loc[1, "Has Changing Lines"])
        self.assertTrue(pd.isna(enriched_df.loc[1, "Date Parsed"]))

    def test_update_journal_entry_flags_persists_favorite_and_archive_state(self):
        reading = {
            "timestamp": "2026-05-03 14:30:00",
            "question": "What needs attention?",
            "lines": [6, 7, 8, 9, 7, 8],
            "primary_hex": SAMPLE_ICHING_DATA["1"],
            "secondary_hex": None,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = Path(temp_dir) / "journal.csv"

            with patch("file_handler.JOURNAL_FILE", str(journal_path)):
                save_reading_to_csv(reading)
                entry_id = load_journal().loc[0, "Entry ID"]
                update_journal_entry_flags(entry_id, favorite=True, archived=True)
                loaded_df = load_journal()

        self.assertTrue(loaded_df.loc[0, "Favorite"])
        self.assertTrue(loaded_df.loc[0, "Archived"])

    def test_journal_to_markdown_includes_hexagram_labels_and_ai_text(self):
        journal_df = pd.DataFrame(
            [
                {
                    "Date": "2026-05-03 14:30:00",
                    "Question": "What needs attention?",
                    "Lines": "6,7,8,9,7,8",
                    "Primary Hexagram": "1: The Creative",
                    "Evolving Hexagram": "2: The Receptive",
                    "AI Interpretation": "Notice the pattern.",
                }
            ]
        )

        markdown = journal_to_markdown(journal_df)

        self.assertIn("# I Ching Reading Journal", markdown)
        self.assertIn("## 2026-05-03 14:30:00 - What needs attention?", markdown)
        self.assertIn("Primary: 1: The Creative", markdown)
        self.assertIn("Evolving: 2: The Receptive", markdown)
        self.assertIn("Lines: 6,7,8,9,7,8", markdown)
        self.assertIn("### AI Contemplation", markdown)
        self.assertIn("Notice the pattern.", markdown)

    def test_reconstruct_reading_from_row_restores_saved_reading_shape(self):
        row = pd.Series(
            {
                "Date": "2026-05-03 14:30:00",
                "Question": "What needs attention?",
                "Lines": "6,7,8,9,7,8",
                "Primary Hexagram Number": 1,
                "Evolving Hexagram Number": 2,
            }
        )

        reading = reconstruct_reading_from_row(row, (SAMPLE_ICHING_DATA, {}))

        self.assertEqual(reading["question"], "What needs attention?")
        self.assertEqual(reading["lines"], [6, 7, 8, 9, 7, 8])
        self.assertEqual(reading["primary_hex"], SAMPLE_ICHING_DATA["1"])
        self.assertEqual(reading["secondary_hex"], SAMPLE_ICHING_DATA["2"])
        self.assertEqual(reading["changing_lines_indices"], [0, 3])
        self.assertEqual(reading["timestamp"], "2026-05-03 14:30:00")

    def test_parse_lines_rejects_malformed_readings(self):
        self.assertEqual(parse_lines("6,7,8,9,7,8"), [6, 7, 8, 9, 7, 8])

        with self.assertRaisesRegex(JournalValidationError, "exactly six lines"):
            parse_lines("6,7,8")

        with self.assertRaisesRegex(JournalValidationError, "Invalid values"):
            parse_lines("6,7,8,9,7,10")

    def test_save_reading_rejects_missing_required_fields(self):
        reading = {
            "timestamp": "2026-05-03 14:30:00",
            "question": "",
            "lines": [6, 7, 8, 9, 7, 8],
            "primary_hex": SAMPLE_ICHING_DATA["1"],
            "secondary_hex": None,
        }

        with self.assertRaisesRegex(JournalValidationError, "question"):
            save_reading_to_csv(reading)

    def test_reconstruct_reading_rejects_unknown_hexagram(self):
        row = pd.Series(
            {
                "Date": "2026-05-03 14:30:00",
                "Question": "What needs attention?",
                "Lines": "6,7,8,9,7,8",
                "Primary Hexagram Number": 99,
                "Evolving Hexagram Number": None,
            }
        )

        with self.assertRaisesRegex(JournalValidationError, "Unknown primary hexagram"):
            reconstruct_reading_from_row(row, SAMPLE_ICHING_DATA)


if __name__ == "__main__":
    unittest.main()
