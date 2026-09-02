"""OpenAI model adapter for EPB."""

from typing import Any, Dict, List, Optional

import openai
from openai import OpenAI

from epb.adapters.base import ModelClient, ModelConfig, Observation, ObservationKind


def _is_gpt5_or_reasoning_model(model_name: str) -> bool:
    """
    Check for GPT-5 series and reasoning models.
    These all require `max_completion_tokens` instead of `max_tokens`.

    Args:
        model_name: The model name to check

    Returns:
        True if this is a GPT-5 or reasoning model (o1, o3)
    """
    if not model_name:
        return False
    lower = model_name.lower()
    # GPT-5 series: gpt-5, gpt-5-mini, gpt-5-nano, gpt-5.1, gpt-5.1-mini, etc.
    # Reasoning models: o1, o1-mini, o1-preview, o3, o3-mini
    return any(pattern in lower for pattern in ["gpt-5", "o1", "o3"])


def _apply_max_token_param(
    body: Dict[str, Any],
    model_name: str,
    max_tokens: Optional[int],
) -> None:
    """
    Mutate the request body to include the correct max token parameter
    depending on whether this is a GPT-4, GPT-5, or reasoning model.

    For GPT-4 and earlier: uses `max_tokens`
    For GPT-5 and reasoning models (o1, o3): uses `max_completion_tokens`

    Args:
        body: The request body dict to mutate
        model_name: The model name
        max_tokens: The maximum tokens value from config (logical limit)
    """
    # Always remove any stale values first
    body.pop("max_tokens", None)
    body.pop("max_completion_tokens", None)

    if max_tokens is None:
        return

    if _is_gpt5_or_reasoning_model(model_name):
        # GPT-5 and reasoning models expect `max_completion_tokens`
        body["max_completion_tokens"] = max_tokens
    else:
        # GPT-4 and earlier expect `max_tokens`
        body["max_tokens"] = max_tokens


# finish_reason values for which the SDK never populates message.content at
# all -- the model's turn ended in a non-text terminal state (a tool/function
# call) rather than a text response. Grounded directly against the
# openai-python Choice.finish_reason schema (verified offline, see
# EPB_PHASE1_FOUNDATIONAL_REPAIR.md): "stop", "length", "tool_calls",
# "content_filter", "function_call".
_NON_TEXT_FINISH_REASONS = {"tool_calls", "function_call"}


def _classify_openai_response(response: Any) -> Observation:
    """Classify a successful OpenAI ChatCompletion response into an Observation.

    Preserves, rather than discards, the two structured signals the
    pre-Phase-1 adapter never read: `message.refusal` (the SDK's native
    refusal field) and `choices[0].finish_reason`. A model-authored refusal
    written as ordinary assistant text is left as VALID_TEXT -- refusal
    *language* alone is not turned into a failure state; only the
    structured `.refusal` field or a `content_filter` finish_reason (a
    platform-level intervention, not model-authored text) does that.

    Branch order matters: any available provider-terminal evidence
    (refusal, content_filter, a non-text terminal state, or truncation)
    is checked BEFORE the generic empty/whitespace text-shape checks, so
    that e.g. whitespace-only content produced under `finish_reason ==
    "length"` is classified TRUNCATED, not WHITESPACE_ONLY_TEXT -- the
    terminal reason is real, observed evidence and must not be silently
    discarded just because the leftover text happens to be blank.
    """
    choice = response.choices[0]
    message = choice.message
    finish_reason = choice.finish_reason
    refusal = getattr(message, "refusal", None)
    content = message.content

    if refusal:
        return Observation(
            text=refusal,
            kind=ObservationKind.PROVIDER_REFUSAL,
            finish_reason=finish_reason,
        )

    if finish_reason == "content_filter":
        return Observation(
            text=content or "",
            kind=ObservationKind.PROVIDER_REFUSAL,
            finish_reason=finish_reason,
        )

    if finish_reason in _NON_TEXT_FINISH_REASONS and not content:
        return Observation(
            text="", kind=ObservationKind.NON_TEXT_TERMINAL, finish_reason=finish_reason
        )

    if finish_reason == "length":
        return Observation(
            text=content or "", kind=ObservationKind.TRUNCATED, finish_reason=finish_reason
        )

    if not content:
        return Observation(text="", kind=ObservationKind.EMPTY_TEXT, finish_reason=finish_reason)

    if content.strip() == "":
        return Observation(
            text=content, kind=ObservationKind.WHITESPACE_ONLY_TEXT, finish_reason=finish_reason
        )

    return Observation(text=content, kind=ObservationKind.VALID_TEXT, finish_reason=finish_reason)


class OpenAIClient(ModelClient):
    """OpenAI model client implementation.

    Uses the OpenAI API to interact with GPT models.
    Requires OPENAI_API_KEY environment variable to be set.
    """

    def __init__(self, config: ModelConfig):
        """Initialize OpenAI client.

        Args:
            config: ModelConfig with OpenAI-specific settings
        """
        super().__init__(config)
        self.client = OpenAI(api_key=self.api_key)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> Observation:
        """Generate a response to a single prompt.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            **kwargs: Additional OpenAI API parameters

        Returns:
            A typed Observation. See ModelClient.generate.
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        # Build request body
        body = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "top_p": kwargs.get("top_p", self.config.top_p),
        }

        # Apply the correct token parameter based on model type
        _apply_max_token_param(
            body=body,
            model_name=self.config.model_name,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
        )

        try:
            response = self.client.chat.completions.create(**body)
        except openai.OpenAIError as e:
            return Observation(
                text="",
                kind=ObservationKind.PROVIDER_ERROR,
                error=f"{type(e).__name__}: {e}",
            )

        return _classify_openai_response(response)

    def generate_chat(
        self,
        turns: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> Observation:
        """Generate a response given conversation history.

        Args:
            turns: List of conversation turns with 'role' and 'content'
            system_prompt: Optional system prompt
            **kwargs: Additional OpenAI API parameters

        Returns:
            A typed Observation. See ModelClient.generate.
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.extend(turns)

        # Build request body
        body = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "top_p": kwargs.get("top_p", self.config.top_p),
        }

        # Apply the correct token parameter based on model type
        _apply_max_token_param(
            body=body,
            model_name=self.config.model_name,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
        )

        try:
            response = self.client.chat.completions.create(**body)
        except openai.OpenAIError as e:
            return Observation(
                text="",
                kind=ObservationKind.PROVIDER_ERROR,
                error=f"{type(e).__name__}: {e}",
            )

        return _classify_openai_response(response)

    def get_name(self) -> str:
        """Get the model's display name.

        Returns:
            The model name from config
        """
        return self.config.model_name
