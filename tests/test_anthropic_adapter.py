"""Tests for the Anthropic adapter's typed Observation classification
(Phase 1 Area 1 / Area 2).

No test file for this adapter existed before Phase 1 (Checkpoint Sec 9 /
EPB_PHASE0_5_VNEXT_DESIGN.md Sec 7.2/7.3/17): the `content[0].text`
AttributeError risk (Checkpoint Defect 3 / D3) was entirely unexercised by
any test. This file closes that gap and covers provider-response
classification generally.
"""

import anthropic
import pytest
from unittest.mock import Mock, patch, MagicMock

from epb.adapters.base import ModelConfig, ObservationKind
from epb.adapters.anthropic_adapter import AnthropicClient, _classify_anthropic_response


def _text_block(text):
    block = Mock()
    block.type = "text"
    block.text = text
    return block


def _non_text_block(block_type="tool_use"):
    """A content block that has no `.text` attribute at all, matching the
    real SDK shape (ToolUseBlock/ThinkingBlock don't expose `.text`) --
    using a plain object rather than a Mock, since Mock() would silently
    auto-create a `.text` attribute and mask the exact defect being tested.
    """
    class _Block:
        pass
    block = _Block()
    block.type = block_type
    return block


def _make_response(content=None, stop_reason="end_turn"):
    response = Mock()
    response.content = content if content is not None else []
    response.stop_reason = stop_reason
    return response


def test_classify_valid_text():
    obs = _classify_anthropic_response(
        _make_response(content=[_text_block("Hello there!")], stop_reason="end_turn")
    )
    assert obs.kind == ObservationKind.VALID_TEXT
    assert obs.text == "Hello there!"
    assert obs.finish_reason == "end_turn"


def test_classify_empty_content_list_is_empty_text():
    """An empty content list with an ordinary stop_reason: genuine empty completion."""
    obs = _classify_anthropic_response(_make_response(content=[], stop_reason="end_turn"))
    assert obs.kind == ObservationKind.EMPTY_TEXT
    assert obs.text == ""


def test_classify_exact_empty_text_block():
    obs = _classify_anthropic_response(
        _make_response(content=[_text_block("")], stop_reason="end_turn")
    )
    assert obs.kind == ObservationKind.EMPTY_TEXT


def test_classify_whitespace_only_text_block():
    obs = _classify_anthropic_response(
        _make_response(content=[_text_block("   \n  ")], stop_reason="end_turn")
    )
    assert obs.kind == ObservationKind.WHITESPACE_ONLY_TEXT
    assert obs.text == "   \n  "


def test_classify_max_tokens_truncation_with_text():
    obs = _classify_anthropic_response(
        _make_response(content=[_text_block("The answer is")], stop_reason="max_tokens")
    )
    assert obs.kind == ObservationKind.TRUNCATED
    assert obs.text == "The answer is"
    assert obs.finish_reason == "max_tokens"


def test_classify_max_tokens_truncation_with_empty_content():
    obs = _classify_anthropic_response(_make_response(content=[], stop_reason="max_tokens"))
    assert obs.kind == ObservationKind.TRUNCATED
    assert obs.text == ""


def test_classify_truncation_outranks_whitespace_shape():
    """Precedence regression: a whitespace-only text block under
    stop_reason == "max_tokens" must classify TRUNCATED, not
    WHITESPACE_ONLY_TEXT -- real, observed terminal evidence must not be
    silently overwritten by a generic text-shape check just because the
    leftover text is blank.
    """
    obs = _classify_anthropic_response(
        _make_response(content=[_text_block("   ")], stop_reason="max_tokens")
    )
    assert obs.kind == ObservationKind.TRUNCATED
    assert obs.text == "   "
    assert obs.finish_reason == "max_tokens"


def test_classify_context_window_exceeded_is_truncated():
    """model_context_window_exceeded is folded into TRUNCATED (Sec 4.1:
    smallest taxonomy that preserves the needed distinction -- both
    represent a length/context limit cutting the model off).
    """
    obs = _classify_anthropic_response(
        _make_response(content=[], stop_reason="model_context_window_exceeded")
    )
    assert obs.kind == ObservationKind.TRUNCATED


def test_classify_native_refusal_stop_reason():
    """Anthropic's structured 'refusal' stop_reason (verified present in the
    installed SDK's Message.stop_reason schema) is PROVIDER_REFUSAL.
    """
    obs = _classify_anthropic_response(_make_response(content=[], stop_reason="refusal"))
    assert obs.kind == ObservationKind.PROVIDER_REFUSAL
    assert obs.finish_reason == "refusal"


def test_classify_native_refusal_with_text_block_present():
    obs = _classify_anthropic_response(
        _make_response(content=[_text_block("I can't help with that.")], stop_reason="refusal")
    )
    assert obs.kind == ObservationKind.PROVIDER_REFUSAL
    assert obs.text == "I can't help with that."


def test_classify_leading_non_text_block_is_non_text_terminal_not_a_crash():
    """The Phase 0 D3 regression test: a leading non-text content block
    (e.g. a tool-use or thinking block) must not raise AttributeError from
    accessing `.text` on a block that doesn't have one.
    """
    obs = _classify_anthropic_response(
        _make_response(content=[_non_text_block("tool_use")], stop_reason="tool_use")
    )
    assert obs.kind == ObservationKind.NON_TEXT_TERMINAL
    assert obs.text == ""


def test_classify_leading_thinking_block_is_non_text_terminal_not_a_crash():
    """Same regression, for a thinking block specifically."""
    obs = _classify_anthropic_response(
        _make_response(content=[_non_text_block("thinking")], stop_reason="end_turn")
    )
    assert obs.kind == ObservationKind.NON_TEXT_TERMINAL
    assert obs.text == ""


def test_classify_ordinary_text_refusal_language_stays_valid_text():
    """A model-authored refusal written as ordinary text (stop_reason
    'end_turn', no native refusal signal) remains VALID_TEXT.
    """
    obs = _classify_anthropic_response(
        _make_response(content=[_text_block("I cannot help with that request.")], stop_reason="end_turn")
    )
    assert obs.kind == ObservationKind.VALID_TEXT
    assert obs.text == "I cannot help with that request."


@patch("epb.adapters.anthropic_adapter.Anthropic")
def test_generate_classifies_provider_error(mock_anthropic_class):
    """An SDK exception is caught and classified as PROVIDER_ERROR, not raised."""
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    mock_client.messages.create.side_effect = anthropic.RateLimitError(
        "rate limited", response=Mock(status_code=429, headers={}, request=Mock()), body=None
    )

    config = ModelConfig(provider="anthropic", model_name="claude-3-5-sonnet-20241022", api_key_env="ANTHROPIC_API_KEY")

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        client = AnthropicClient(config)
        obs = client.generate("Test prompt")

    assert obs.kind == ObservationKind.PROVIDER_ERROR
    assert obs.text == ""
    assert "RateLimitError" in obs.error


@patch("epb.adapters.anthropic_adapter.Anthropic")
def test_generate_chat_does_not_crash_on_leading_tool_use_block(mock_anthropic_class):
    """End-to-end regression for Checkpoint Defect 3 through the real
    generate_chat() call path, not just the classifier directly.
    """
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    mock_client.messages.create.return_value = _make_response(
        content=[_non_text_block("tool_use")], stop_reason="tool_use"
    )

    config = ModelConfig(provider="anthropic", model_name="claude-3-5-sonnet-20241022", api_key_env="ANTHROPIC_API_KEY")

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        client = AnthropicClient(config)
        obs = client.generate_chat([{"role": "user", "content": "hi"}])

    assert obs.kind == ObservationKind.NON_TEXT_TERMINAL
    assert obs.text == ""


@patch("epb.adapters.anthropic_adapter.Anthropic")
def test_generate_returns_valid_text_end_to_end(mock_anthropic_class):
    """Full generate() call path still returns ordinary valid text unchanged
    in substance from pre-Phase-1 behavior (now carried in Observation.text).
    """
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    mock_client.messages.create.return_value = _make_response(
        content=[_text_block("A valid answer.")], stop_reason="end_turn"
    )

    config = ModelConfig(provider="anthropic", model_name="claude-3-5-sonnet-20241022", api_key_env="ANTHROPIC_API_KEY")

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        client = AnthropicClient(config)
        obs = client.generate("Test prompt")

    assert obs.kind == ObservationKind.VALID_TEXT
    assert obs.text == "A valid answer."


@patch("epb.adapters.anthropic_adapter.Anthropic")
def test_generate_does_not_send_top_p_with_temperature(mock_anthropic_class):
    """Regression: pre-existing Claude API constraint (temperature/top_p
    mutual exclusion) must remain unaffected by the Observation migration.
    """
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    mock_client.messages.create.return_value = _make_response(
        content=[_text_block("ok")], stop_reason="end_turn"
    )

    config = ModelConfig(provider="anthropic", model_name="claude-3-5-sonnet-20241022", api_key_env="ANTHROPIC_API_KEY")

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        client = AnthropicClient(config)
        client.generate("Test prompt")

    call_kwargs = mock_client.messages.create.call_args[1]
    assert "top_p" not in call_kwargs
    assert "temperature" in call_kwargs
