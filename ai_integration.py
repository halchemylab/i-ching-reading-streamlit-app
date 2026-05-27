import os
from dataclasses import dataclass
from typing import Optional

import openai


DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_OPENAI_MAX_TOKENS = 900
DEFAULT_OPENAI_TEMPERATURE = 0.7
DEFAULT_OPENAI_TIMEOUT_SECONDS = 30.0
DEFAULT_OPENAI_MAX_RETRIES = 2


class AIInterpretationError(Exception):
    """Raised when the AI interpretation cannot be generated."""


class AIRateLimitError(AIInterpretationError):
    """Raised when the OpenAI API rate limit or quota is reached."""


class AIConfigurationError(AIInterpretationError):
    """Raised when AI configuration values are invalid."""


@dataclass(frozen=True)
class AISettings:
    """Runtime configuration for OpenAI-backed interpretation."""

    model: str = DEFAULT_OPENAI_MODEL
    max_tokens: int = DEFAULT_OPENAI_MAX_TOKENS
    temperature: float = DEFAULT_OPENAI_TEMPERATURE
    timeout_seconds: float = DEFAULT_OPENAI_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_OPENAI_MAX_RETRIES


@dataclass(frozen=True)
class AIConfig:
    """Resolved AI settings plus optional API credentials."""

    api_key: Optional[str]
    settings: AISettings

    @property
    def enabled(self):
        return bool(self.api_key)

    def client_kwargs(self):
        if not self.api_key:
            raise AIConfigurationError("OpenAI API key is missing.")

        return {
            "api_key": self.api_key,
            "timeout": self.settings.timeout_seconds,
            "max_retries": self.settings.max_retries,
        }


def build_ai_config(secrets=None, environ=None):
    """Resolves AI configuration from Streamlit secrets first, then environment."""
    if environ is None:
        environ = os.environ

    settings = AISettings(
        model=_get_config_value(
            secrets,
            environ,
            env_key="OPENAI_MODEL",
            nested_key="model",
            default=DEFAULT_OPENAI_MODEL,
        ),
        max_tokens=_parse_int_config(
            _get_config_value(
                secrets,
                environ,
                env_key="OPENAI_MAX_TOKENS",
                nested_key="max_tokens",
                default=DEFAULT_OPENAI_MAX_TOKENS,
            ),
            "OPENAI_MAX_TOKENS",
            minimum=1,
        ),
        temperature=_parse_float_config(
            _get_config_value(
                secrets,
                environ,
                env_key="OPENAI_TEMPERATURE",
                nested_key="temperature",
                default=DEFAULT_OPENAI_TEMPERATURE,
            ),
            "OPENAI_TEMPERATURE",
            minimum=0,
            maximum=2,
        ),
        timeout_seconds=_parse_float_config(
            _get_config_value(
                secrets,
                environ,
                env_key="OPENAI_TIMEOUT_SECONDS",
                nested_key="timeout_seconds",
                default=DEFAULT_OPENAI_TIMEOUT_SECONDS,
            ),
            "OPENAI_TIMEOUT_SECONDS",
            minimum=1,
        ),
        max_retries=_parse_int_config(
            _get_config_value(
                secrets,
                environ,
                env_key="OPENAI_MAX_RETRIES",
                nested_key="max_retries",
                default=DEFAULT_OPENAI_MAX_RETRIES,
            ),
            "OPENAI_MAX_RETRIES",
            minimum=0,
        ),
    )

    api_key = _get_config_value(
        secrets,
        environ,
        env_key="OPENAI_API_KEY",
        nested_key="api_key",
        default=None,
    )

    return AIConfig(api_key=_blank_to_none(api_key), settings=settings)


def _get_config_value(secrets, environ, env_key, nested_key, default):
    secret_value = _read_secret_value(secrets, env_key, nested_key)
    if _is_present(secret_value):
        return secret_value

    env_value = environ.get(env_key)
    if _is_present(env_value):
        return env_value

    return default


def _read_secret_value(secrets, env_key, nested_key):
    if secrets is None:
        return None

    try:
        flat_value = _mapping_get(secrets, env_key)
        if _is_present(flat_value):
            return flat_value

        openai_section = _mapping_get(secrets, "openai")
        if openai_section is not None:
            return _mapping_get(openai_section, nested_key)
    except (AttributeError, KeyError, TypeError, FileNotFoundError):
        return None

    return None


def _mapping_get(mapping, key):
    if hasattr(mapping, "get"):
        return mapping.get(key)

    return mapping[key]


def _blank_to_none(value):
    if not _is_present(value):
        return None

    return str(value).strip()


def _is_present(value):
    return value is not None and str(value).strip() != ""


def _parse_int_config(value, field_name, minimum=None, maximum=None):
    try:
        parsed_value = int(value)
    except (TypeError, ValueError) as e:
        raise AIConfigurationError(f"{field_name} must be an integer.") from e

    _validate_range(parsed_value, field_name, minimum, maximum)
    return parsed_value


def _parse_float_config(value, field_name, minimum=None, maximum=None):
    try:
        parsed_value = float(value)
    except (TypeError, ValueError) as e:
        raise AIConfigurationError(f"{field_name} must be a number.") from e

    _validate_range(parsed_value, field_name, minimum, maximum)
    return parsed_value


def _validate_range(value, field_name, minimum, maximum):
    if minimum is not None and value < minimum:
        raise AIConfigurationError(f"{field_name} must be at least {minimum}.")
    if maximum is not None and value > maximum:
        raise AIConfigurationError(f"{field_name} must be at most {maximum}.")


def get_ai_interpretation(reading, client, settings=None):
    """Constructs a prompt and gets an interpretation from OpenAI."""
    settings = settings or AISettings()
    primary_hex = reading['primary_hex']
    secondary_hex = reading['secondary_hex']
    
    changing_lines_text = ""
    if reading['changing_lines_indices']:
        changing_lines_text += "The following lines are in a state of transformation:\n"
        for i in reading['changing_lines_indices']:
            line_data = primary_hex['lines'][i]
            changing_lines_text += f"- **Line {i+1}:** {line_data['line_en']}\n"
    else:
        changing_lines_text = "There are no changing lines.\n"

    evolving_hex_text = ""
    if secondary_hex:
        evolving_hex_text = f"""
This is evolving into a new energetic pattern:
- **Evolving Hexagram:** {secondary_hex['number']}. {secondary_hex['name_en']} ({secondary_hex['name_zh']}) - This points to the potential direction of change and the lesson to be integrated.
- **Judgment:** {secondary_hex['judgment_en']}
"""

    prompt = f"""
You are a wise and compassionate guide to the I Ching, the Book of Changes. Your purpose is not to predict the future, but to offer timeless wisdom that illuminates the present moment and empowers the user to make conscious choices.

A user has approached you with the following inquiry: "{reading['question']}"

They have received a reading that reflects the energies surrounding their question:
- **Primary Hexagram:** {primary_hex['number']}. {primary_hex['name_en']} ({primary_hex['name_zh']}) - This represents the current state of things.
- **Judgment:** {primary_hex['judgment_en']}

{changing_lines_text}
{evolving_hex_text}

Please offer a contemplative interpretation organized into the following four sections, using the bolded titles exactly as written:

**The Present Situation:**
Start here. Interpret the primary hexagram and its judgment in the context of the user's question. Describe the current energies at play.

**The Dynamics of Change:**
Next, explain the significance of the changing lines. If there are no changing lines, briefly state that the situation is stable and focus on the primary hexagram's wisdom.

**The Emerging Direction:**
Then, interpret the secondary (evolving) hexagram. Describe the potential future, the direction of change, or the lesson to be integrated. If there is no secondary hexagram, you can omit this section.

**Guidance for Reflection:**
Conclude with a paragraph of practical, supportive advice. Offer questions for reflection or suggest a focus for the user's energy that weaves together all the elements of the reading.

Your tone should be serene, insightful, and supportive throughout.
    """

    system_message = """
You are a wise and compassionate I Ching interpreter.

**Content Safety Policy for I Ching Interpretation**

As a guide to the I Ching, your primary directive is to provide interpretations that are safe, ethical, and supportive. You must strictly adhere to the following principles:

1.  **No Predictions or Guarantees:**
    -   **Do not** predict specific future events, outcomes, or timelines (e.g., "You will get the job," "The relationship will end in three months").
    -   **Do not** offer financial, legal, or medical advice. Frame guidance in terms of psychological, spiritual, and personal reflection.
    -   **Do** use cautious and empowering language, such as "The energy suggests...", "This may be a time for...", "Consider the possibility that...".

2.  **Promote Agency and Responsibility:**
    -   **Do not** present the I Ching's wisdom as a command or an unchangeable fate.
    -   **Do** emphasize the user's personal agency, free will, and responsibility in making choices. The reading is a tool for insight, not a substitute for decision-making.

3.  **Avoid Harmful or Unethical Content:**
    -   **Do not** generate content that is hateful, discriminatory, or violent.
    -   **Do not** encourage self-harm, suicide, or any dangerous activities.
    -   **Do not** provide interpretations that could be construed as manipulative, coercive, or promoting harmful relationship dynamics.
    -   **Do not** create sexually explicit or profane content.

4.  **Maintain a Supportive and Compassionate Tone:**
    -   **Do** be consistently serene, empathetic, and non-judgmental.
    -   **Do not** be alarming, fatalistic, or overly negative, even when interpreting challenging hexagrams. Frame difficulties as opportunities for growth and learning.

5.  **Stay Within the Scope of the I Ching:**
    -   **Do not** invent information or provide guidance that is unrelated to the symbols and wisdom of the I Ching.
    -   **Do** ground your interpretation in the meanings of the hexagrams, lines, and their interplay as provided in the prompt.

By adhering to this policy, you ensure that the user's experience is one of empowerment, clarity, and profound self-reflection.
"""

    try:
        response = client.chat.completions.create(
            model=settings.model,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
            timeout=settings.timeout_seconds,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except openai.RateLimitError as e:
        raise AIRateLimitError(f"OpenAI API rate limit exceeded or insufficient quota: {e}") from e
    except openai.AuthenticationError as e:
        raise AIInterpretationError(
            "OpenAI authentication failed. Check your OPENAI_API_KEY in .env or Streamlit secrets."
        ) from e
    except openai.APITimeoutError as e:
        raise AIInterpretationError(
            f"OpenAI request timed out after {settings.timeout_seconds:g} seconds. Try again or increase OPENAI_TIMEOUT_SECONDS."
        ) from e
    except openai.APIConnectionError as e:
        raise AIInterpretationError(
            "Could not reach OpenAI. Check your network connection and try again."
        ) from e
    except openai.BadRequestError as e:
        raise AIInterpretationError(
            f"OpenAI rejected the request. Check the configured model '{settings.model}' and token limit."
        ) from e
    except openai.APIError as e:
        raise AIInterpretationError("OpenAI returned an API error. Please try again shortly.") from e
    except Exception as e:
        raise AIInterpretationError(f"An error occurred while contacting the AI: {e}") from e
