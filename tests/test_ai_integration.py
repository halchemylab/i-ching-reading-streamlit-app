import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ai_integration import (
    AIInterpretationError,
    AIRateLimitError,
    get_ai_interpretation,
)


SAMPLE_PRIMARY_HEX = {
    "number": 11,
    "name_en": "Peace",
    "name_zh": "泰",
    "judgment_en": "Small departs, great approaches.",
    "lines": [
        {"line_en": "Pulling up grass brings companions."},
        {"line_en": "Bearing with the uncultivated."},
        {"line_en": "No plain not followed by a slope."},
        {"line_en": "Fluttering down, not rich with neighbors."},
        {"line_en": "The sovereign gives his daughter in marriage."},
        {"line_en": "The city wall falls back into the moat."},
    ],
}

SAMPLE_SECONDARY_HEX = {
    "number": 32,
    "name_en": "Duration",
    "name_zh": "恆",
    "judgment_en": "Perseverance furthers.",
}


def make_reading(changing_lines_indices=None, secondary_hex=None):
    return {
        "question": "How should I approach this collaboration?",
        "primary_hex": SAMPLE_PRIMARY_HEX,
        "secondary_hex": secondary_hex,
        "changing_lines_indices": changing_lines_indices or [],
    }


def make_client(response_text="A contemplative response."):
    client = Mock()
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=response_text),
            )
        ]
    )
    return client


class TestAIIntegration(unittest.TestCase):
    def test_get_ai_interpretation_returns_response_text(self):
        client = make_client("Look for harmony and steady action.")

        result = get_ai_interpretation(make_reading(), client)

        self.assertEqual(result, "Look for harmony and steady action.")

    def test_prompt_includes_question_hexagrams_and_changing_lines(self):
        client = make_client()
        reading = make_reading(
            changing_lines_indices=[0, 4],
            secondary_hex=SAMPLE_SECONDARY_HEX,
        )

        get_ai_interpretation(reading, client)

        create_kwargs = client.chat.completions.create.call_args.kwargs
        self.assertEqual(create_kwargs["model"], "gpt-4o-mini")
        messages = create_kwargs["messages"]
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")

        prompt = messages[1]["content"]
        self.assertIn('A user has approached you with the following inquiry: "How should I approach this collaboration?"', prompt)
        self.assertIn("**Primary Hexagram:** 11. Peace (泰)", prompt)
        self.assertIn("**Judgment:** Small departs, great approaches.", prompt)
        self.assertIn("The following lines are in a state of transformation:", prompt)
        self.assertIn("**Line 1:** Pulling up grass brings companions.", prompt)
        self.assertIn("**Line 5:** The sovereign gives his daughter in marriage.", prompt)
        self.assertIn("**Evolving Hexagram:** 32. Duration (恆)", prompt)
        self.assertIn("**Judgment:** Perseverance furthers.", prompt)

    def test_prompt_handles_reading_without_changing_lines_or_evolving_hexagram(self):
        client = make_client()

        get_ai_interpretation(make_reading(), client)

        prompt = client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
        self.assertIn("There are no changing lines.", prompt)
        self.assertNotIn("This is evolving into a new energetic pattern:", prompt)
        self.assertNotIn("**Evolving Hexagram:**", prompt)

    def test_rate_limit_error_is_translated(self):
        class FakeRateLimitError(Exception):
            pass

        client = make_client()
        client.chat.completions.create.side_effect = FakeRateLimitError("quota reached")

        with patch("ai_integration.openai.RateLimitError", FakeRateLimitError):
            with self.assertRaisesRegex(AIRateLimitError, "rate limit exceeded"):
                get_ai_interpretation(make_reading(), client)

    def test_generic_api_error_is_translated(self):
        client = make_client()
        client.chat.completions.create.side_effect = RuntimeError("service unavailable")

        with self.assertRaisesRegex(AIInterpretationError, "contacting the AI"):
            get_ai_interpretation(make_reading(), client)


if __name__ == "__main__":
    unittest.main()
