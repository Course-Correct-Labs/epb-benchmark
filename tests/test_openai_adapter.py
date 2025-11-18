"""Tests for OpenAI adapter token parameter handling."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from epb.adapters.base import ModelConfig
from epb.adapters.openai_adapter import (
    OpenAIClient,
    _is_gpt5_or_reasoning_model,
    _apply_max_token_param,
)


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
    # Setup mock
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Test response"
    mock_client.chat.completions.create.return_value = mock_response

    # Create client
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
    # Setup mock
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Test response"
    mock_client.chat.completions.create.return_value = mock_response

    # Create client
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
    # Setup mock
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Test response"
    mock_client.chat.completions.create.return_value = mock_response

    # Create client
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
    # Setup mock
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Test response"
    mock_client.chat.completions.create.return_value = mock_response

    # Create client
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
    # Setup mock
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Test response"
    mock_client.chat.completions.create.return_value = mock_response

    # Create client
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
