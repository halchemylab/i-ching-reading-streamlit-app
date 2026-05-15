import unittest
from datetime import date

import pandas as pd

from journal_ui import apply_journal_filters


class TestJournalUI(unittest.TestCase):
    def make_journal_df(self):
        return pd.DataFrame(
            [
                {
                    "Date Parsed": pd.Timestamp("2026-05-01"),
                    "Question": "What should I continue?",
                    "AI Interpretation": "",
                    "Primary Hexagram": "1: The Creative",
                    "Evolving Hexagram": None,
                    "Favorite": True,
                    "Archived": False,
                    "Has AI Contemplation": False,
                    "Has Changing Lines": False,
                },
                {
                    "Date Parsed": pd.Timestamp("2026-05-02"),
                    "Question": "What should I release?",
                    "AI Interpretation": "Let the old pattern rest.",
                    "Primary Hexagram": "2: The Receptive",
                    "Evolving Hexagram": None,
                    "Favorite": False,
                    "Archived": True,
                    "Has AI Contemplation": True,
                    "Has Changing Lines": True,
                },
            ]
        )

    def test_apply_journal_filters_hides_archived_by_default(self):
        filtered_df = apply_journal_filters(self.make_journal_df())

        self.assertEqual(list(filtered_df["Question"]), ["What should I continue?"])

    def test_apply_journal_filters_can_show_archived_readings(self):
        filtered_df = apply_journal_filters(self.make_journal_df(), show_archived=True)

        self.assertEqual(
            list(filtered_df["Question"]),
            ["What should I release?", "What should I continue?"],
        )

    def test_apply_journal_filters_can_show_favorites_only(self):
        filtered_df = apply_journal_filters(
            self.make_journal_df(),
            favorites_only=True,
            show_archived=True,
            date_range=(date(2026, 5, 1), date(2026, 5, 2)),
        )

        self.assertEqual(list(filtered_df["Question"]), ["What should I continue?"])


if __name__ == "__main__":
    unittest.main()
