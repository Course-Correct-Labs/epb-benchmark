"""Tests for the OpenAI adapter: token parameter handling (unchanged from
pre-Phase-1) and the typed Observation classification introduced in Phase 1
Area 1.
"""

import openai
import pytest
from unittest.mock import Mock, patch, MagicMock

from epb.adapters.base import ModelConfig, ObservationKind
from epb.adapters.openai_adapter import (
    OpenAIClient,
    _is_gpt5_or_reasoning_model,
    _apply_max_token_param,
    _classify_openai_response,
)


def _make_response(content=None, refusal=None, finish_reason="stop"):
    """Build a mock ChatCompletion response with explicit, non-Mock-default
    field values -- Mock()'s auto-attribute behavior makes every unset
    attribute a truthy Mock object, which would silently misclassify every
    response as PROVIDER_REFUSAL if `refusal`/`finish_reason` were left
    unset rather than explicitly assigned.
    """
    response = Mock()
    choice = Mock()
    message = Mock()
    message.content = content
    message.refusal = refusal
    choice.message = message
    choice.finish_reason = finish_reason
    response.choices = [choice]
    return response


def test_is_gpt5_or_reasoning_model_gpt4():
    """Test that GPT-4 models are not detected as GPT-5/reasoning."""
    assert _is_gpt5_or_reasoning_model("gpt-4") is False
    assert _is_gpt5_or_reasoning_model("gpt-4-turbo") is False
    assert _is_gpt5_or_reasoning_model("gpt-4.1-mini") is False
    assert _is_gpt5_or_reasoning_model("gpt-4o") is False


def test_is_gpt5_or_reasoning_model_gpt5():
    """Test that GPT-5 models are correctly detected."""
    assert _is_gpt5_or_reasoning_model("gpt-5") is True
    assert _is_gpt5_or_reasoning_model("gpt-5-mini") is True
    assert _is_gpt5_or_reasoning_model("gpt-5-nano") is True
    assert _is_gpt5_or_reasoning_model("gpt-5.1") is True
    assert _is_gpt5_or_reasoning_model("gpt-5.1-mini") is True
    assert _is_gpt5_or_reasoning_model("GPT-5-Mini") is True  # Case insensitive


def test_is_gpt5_or_reasoning_model_o1():
    """Test that o1 reasoning models are correctly detected."""
    assert _is_gpt5_or_reasoning_model("o1") is True
    assert _is_gpt5_or_reasoning_model("o1-mini") is True
    assert _is_gpt5_or_reasoning_model("o1-preview") is True
    assert _is_gpt5_or_reasoning_model("O1-Mini") is True  # Case insensitive


def test_is_gpt5_or_reasoning_model_o3():
    """Test that o3 reasoning models are correctly detected."""
    assert _is_gpt5_or_reasoning_model("o3") is True
    assert _is_gpt5_or_reasoning_model("o3-mini") is True
    assert _is_gpt5_or_reasoning_model("O3-MINI") is True  # Case insensitive


def test_is_gpt5_or_reasoning_model_empty():
    """Test with empty or None model name."""
    assert _is_gpt5_or_reasoning_model("") is False
    assert _is_gpt5_or_reasoning_model(None) is False


def test_apply_max_token_param_gpt4():
    """Test that GPT-4 models get max_tokens parameter."""
    body = {}
    _apply_max_token_param(body, "gpt-4.1-mini", 256)

    assert body["max_tokens"] == 256
    assert "max_completion_tokens" not in body


def test_apply_max_token_param_gpt5():
    """Test that GPT-5 models get max_completion_tokens parameter."""
    body = {}
    _apply_max_token_param(body, "gpt-5-mini", 256)

    assert body["max_completion_tokens"] == 256
    assert "max_tokens" not in body


def test_apply_max_token_param_o1():
    """Test that o1 reasoning models get max_completion_tokens parameter."""
    body = {}
    _apply_max_token_param(body, "o1-mini", 256)

    assert body["max_completion_tokens"] == 256
    assert "max_tokens" not in body


def test_apply_max_token_param_o3():
    """Test that o3 reasoning models get max_completion_tokens parameter."""
    body = {}
    _apply_max_token_param(body, "o3-mini", 256)

    assert body["max_completion_tokens"] == 256
    assert "max_tokens" not in body


def test_apply_max_token_param_none():
    """Test that None max_tokens results in no parameter."""
    body = {}
    _apply_max_token_param(body, "gpt-4", None)

    assert "max_tokens" not in body
    assert "max_completion_tokens" not in body


def test_apply_max_token_param_removes_stale():
    """Test that stale parameters are removed."""
    body = {"max_tokens": 100, "max_completion_tokens": 200}
    _apply_max_token_param(body, "gpt-4", 256)

    assert body["max_tokens"] == 256
    assert "max_completion_tokens" not in body


@patch("epb.adapters.openai_adapter.OpenAI")
def test_openai_client_gpt4_integration(mock_openai_class):
    """Test that GPT-4 integration uses max_tokens."""
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    mock_client.chat.completions.create.return_value = _make_response(content="Test response")

    config = ModelConfig(
        provider="openai",
        model_name="gpt-4.1-mini",
        api_key_env="OPENAI_API_KEY",
        max_tokens=256,
    )

    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        client = OpenAIClient(config)
        client.generate("Test prompt")

    # Verify the API was called with max_tokens
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["max_tokens"] == 256
    assert "max_completion_tokens" not in call_kwargs


@patch("epb.adapters.openai_adapter.OpenAI")
def test_openai_client_gpt5_integration(mock_openai_class):
    """Test that GPT-5 integration uses max_completion_tokens."""
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    mock_client.chat.completions.create.return_value = _make_response(content="Test response")

    config = ModelConfig(
        provider="openai",
        model_name="gpt-5-mini",
        api_key_env="OPENAI_API_KEY",
        max_tokens=256,
    )

    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        client = OpenAIClient(config)
        client.generate("Test prompt")

    # Verify the API was called with max_completion_tokens
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["max_completion_tokens"] == 256
    assert "max_tokens" not in call_kwargs


@patch("epb.adapters.openai_adapter.OpenAI")
def test_openai_client_o1_integration(mock_openai_class):
    """Test that o1 reasoning models use max_completion_tokens."""
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    mock_client.chat.completions.create.return_value = _make_response(content="Test response")

    config = ModelConfig(
        provider="openai",
        model_name="o1-mini",
        api_key_env="OPENAI_API_KEY",
        max_tokens=256,
    )

    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        client = OpenAIClient(config)
        client.generate("Test prompt")

    # Verify the API was called with max_completion_tokens
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["max_completion_tokens"] == 256
    assert "max_tokens" not in call_kwargs


@patch("epb.adapters.openai_adapter.OpenAI")
def test_openai_client_chat_gpt4(mock_openai_class):
    """Test that generate_chat also uses correct token param for GPT-4."""
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    mock_client.chat.completions.create.return_value = _make_response(content="Test response")

    config = ModelConfig(
        provider="openai",
        model_name="gpt-4",
        api_key_env="OPENAI_API_KEY",
        max_tokens=512,
    )

    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        client = OpenAIClient(config)
        turns = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
            {"role": "user", "content": "How are you?"},
        ]
        client.generate_chat(turns)

    # Verify the API was called with max_tokens
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["max_tokens"] == 512
    assert "max_completion_tokens" not in call_kwargs


@patch("epb.adapters.openai_adapter.OpenAI")
def test_openai_client_chat_o3(mock_openai_class):
    """Test that generate_chat uses max_completion_tokens for o3."""
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    mock_client.chat.completions.create.return_value = _make_response(content="Test response")

    config = ModelConfig(
        provider="openai",
        model_name="o3-mini",
        api_key_env="OPENAI_API_KEY",
        max_tokens=512,
    )

    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        client = OpenAIClient(config)
        turns = [
            {"role": "user", "content": "Solve this problem"},
        ]
        client.generate_chat(turns)

    # Verify the API was called with max_completion_tokens
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["max_completion_tokens"] == 512
    assert "max_tokens" not in call_kwargs


# --- Observation classification (Phase 1 Area 1 / Area 2) ---


def test_classify_valid_text():
    obs = _classify_openai_response(_make_response(content="Hello there!", finish_reason="stop"))
    assert obs.kind == ObservationKind.VALID_TEXT
    assert obs.text == "Hello there!"
    assert obs.finish_reason == "stop"


def test_classify_none_content_is_empty_text():
    """content=None with an ordinary finish_reason -- a genuine empty completion."""
    obs = _classify_openai_response(_make_response(content=None, finish_reason="stop"))
    assert obs.kind == ObservationKind.EMPTY_TEXT
    assert obs.text == ""


def test_classify_exact_empty_string_is_empty_text():
    obs = _classify_openai_response(_make_response(content="", finish_reason="stop"))
    assert obs.kind == ObservationKind.EMPTY_TEXT


def test_classify_whitespace_only_text():
    obs = _classify_openai_response(_make_response(content="   \n  ", finish_reason="stop"))
    assert obs.kind == ObservationKind.WHITESPACE_ONLY_TEXT
    assert obs.text == "   \n  "


def test_classify_truncation_with_content():
    """finish_reason='length' with partial text: text is preserved, kind is TRUNCATED."""
    obs = _classify_openai_response(_make_response(content="The answer is", finish_reason="length"))
    assert obs.kind == ObservationKind.TRUNCATED
    assert obs.text == "The answer is"
    assert obs.finish_reason == "length"


def test_classify_truncation_with_no_content():
    obs = _classify_openai_response(_make_response(content=None, finish_reason="length"))
    assert obs.kind == ObservationKind.TRUNCATED
    assert obs.text == ""


def test_classify_truncation_outranks_whitespace_shape():
    """Precedence regression: whitespace-only content under finish_reason
    == "length" must classify TRUNCATED, not WHITESPACE_ONLY_TEXT --
    real, observed terminal evidence must not be silently overwritten by
    a generic text-shape check just because the leftover text is blank.
    """
    obs = _classify_openai_response(_make_response(content="   ", finish_reason="length"))
    assert obs.kind == ObservationKind.TRUNCATED
    assert obs.text == "   "
    assert obs.finish_reason == "length"


def test_classify_structured_refusal():
    """The SDK's native `.refusal` field takes priority over `.content`."""
    obs = _classify_openai_response(
        _make_response(content=None, refusal="I can't help with that.", finish_reason="stop")
    )
    assert obs.kind == ObservationKind.PROVIDER_REFUSAL
    assert obs.text == "I can't help with that."


def test_classify_content_filter_is_provider_refusal():
    """A platform-level content filter is a provider-side intervention, not model text."""
    obs = _classify_openai_response(_make_response(content=None, finish_reason="content_filter"))
    assert obs.kind == ObservationKind.PROVIDER_REFUSAL
    assert obs.finish_reason == "content_filter"


def test_classify_tool_calls_is_non_text_terminal():
    """finish_reason='tool_calls' with no content: nothing usable as text exists."""
    obs = _classify_openai_response(_make_response(content=None, finish_reason="tool_calls"))
    assert obs.kind == ObservationKind.NON_TEXT_TERMINAL
    assert obs.text == ""


def test_classify_ordinary_text_refusal_language_stays_valid_text():
    """A model-authored refusal written as ordinary text (no structured
    .refusal, no content_filter) remains VALID_TEXT -- refusal *language*
    alone must not be turned into a provider-failure state.
    """
    obs = _classify_openai_response(
        _make_response(content="I cannot help with that request.", finish_reason="stop")
    )
    assert obs.kind == ObservationKind.VALID_TEXT
    assert obs.text == "I cannot help with that request."


@patch("epb.adapters.openai_adapter.OpenAI")
def test_generate_classifies_provider_error(mock_openai_class):
    """An SDK exception is caught and classified as PROVIDER_ERROR, not raised."""
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    mock_client.chat.completions.create.side_effect = openai.RateLimitError(
        "rate limited", response=Mock(status_code=429, headers={}), body=None
    )

    config = ModelConfig(provider="openai", model_name="gpt-4", api_key_env="OPENAI_API_KEY")

    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        client = OpenAIClient(config)
        obs = client.generate("Test prompt")

    assert obs.kind == ObservationKind.PROVIDER_ERROR
    assert obs.text == ""
    assert "RateLimitError" in obs.error


@patch("epb.adapters.openai_adapter.OpenAI")
def test_generate_chat_classifies_provider_error(mock_openai_class):
    """generate_chat has the same provider-error handling as generate."""
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    mock_client.chat.completions.create.side_effect = openai.APIConnectionError(request=Mock())

    config = ModelConfig(provider="openai", model_name="gpt-4", api_key_env="OPENAI_API_KEY")

    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        client = OpenAIClient(config)
        obs = client.generate_chat([{"role": "user", "content": "hi"}])

    assert obs.kind == ObservationKind.PROVIDER_ERROR
    assert obs.text == ""


@patch("epb.adapters.openai_adapter.OpenAI")
def test_generate_returns_valid_text_end_to_end(mock_openai_class):
    """Full generate() call path still returns ordinary valid text unchanged
    in substance from pre-Phase-1 behavior (now carried in Observation.text).
    """
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    mock_client.chat.completions.create.return_value = _make_response(content="A valid answer.")

    config = ModelConfig(provider="openai", model_name="gpt-4", api_key_env="OPENAI_API_KEY")

    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        client = OpenAIClient(config)
        obs = client.generate("Test prompt")

    assert obs.kind == ObservationKind.VALID_TEXT
    assert obs.text == "A valid answer."
