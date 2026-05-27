import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ai_integration import (
    AIConfigurationError,
    AISettings,
    AIInterpretationError,
    AIRateLimitError,
    build_ai_config,
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

    def test_get_ai_interpretation_uses_configured_request_settings(self):
        client = make_client()
        settings = AISettings(
            model="gpt-test-model",
            max_tokens=450,
            temperature=0.2,
            timeout_seconds=12.5,
            max_retries=1,
        )

        get_ai_interpretation(make_reading(), client, settings=settings)

        create_kwargs = client.chat.completions.create.call_args.kwargs
        self.assertEqual(create_kwargs["model"], "gpt-test-model")
        self.assertEqual(create_kwargs["max_tokens"], 450)
        self.assertEqual(create_kwargs["temperature"], 0.2)
        self.assertEqual(create_kwargs["timeout"], 12.5)

    def test_build_ai_config_reads_secrets_before_environment(self):
        config = build_ai_config(
            secrets={
                "openai": {
                    "api_key": "sk-secret",
                    "model": "gpt-secret",
                    "max_tokens": "500",
                    "temperature": "0.3",
                    "timeout_seconds": "45",
                    "max_retries": "4",
                }
            },
            environ={
                "OPENAI_API_KEY": "sk-env",
                "OPENAI_MODEL": "gpt-env",
                "OPENAI_MAX_TOKENS": "300",
            },
        )

        self.assertTrue(config.enabled)
        self.assertEqual(config.api_key, "sk-secret")
        self.assertEqual(config.settings.model, "gpt-secret")
        self.assertEqual(config.settings.max_tokens, 500)
        self.assertEqual(config.settings.temperature, 0.3)
        self.assertEqual(config.settings.timeout_seconds, 45)
        self.assertEqual(config.settings.max_retries, 4)

    def test_build_ai_config_supports_flat_secret_keys(self):
        config = build_ai_config(
            secrets={
                "OPENAI_API_KEY": "sk-flat-secret",
                "OPENAI_MODEL": "gpt-flat-secret",
            },
            environ={"OPENAI_API_KEY": "sk-env"},
        )

        self.assertEqual(config.api_key, "sk-flat-secret")
        self.assertEqual(config.settings.model, "gpt-flat-secret")

    def test_build_ai_config_rejects_invalid_numeric_settings(self):
        with self.assertRaisesRegex(AIConfigurationError, "OPENAI_MAX_TOKENS must be an integer"):
            build_ai_config(secrets=None, environ={"OPENAI_MAX_TOKENS": "many"})

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
