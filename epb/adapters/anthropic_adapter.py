"""Anthropic model adapter for EPB."""

from typing import Any, Dict, List, Optional

import anthropic
from anthropic import Anthropic

from epb.adapters.base import ModelClient, ModelConfig, Observation, ObservationKind

# stop_reason values that represent the model being cut off by a length/
# context limit rather than reaching a natural end_turn. Grounded directly
# against the anthropic-python Message.stop_reason schema (verified
# offline, see EPB_PHASE1_FOUNDATIONAL_REPAIR.md): "end_turn", "max_tokens",
# "stop_sequence", "tool_use", "pause_turn", "refusal",
# "model_context_window_exceeded".
_TRUNCATION_STOP_REASONS = {"max_tokens", "model_context_window_exceeded"}


def _classify_anthropic_response(response: Any) -> Observation:
    """Classify a successful Anthropic Messages response into an Observation.

    This directly fixes the Phase 0 D3 defect: the pre-Phase-1 adapter
    accessed `response.content[0].text` unconditionally, which raises
    AttributeError on a leading non-text content block (a thinking block or
    a tool-use block). Here, the block's `.type` is checked before `.text`
    is ever accessed, so such a response is classified NON_TEXT_TERMINAL
    instead of crashing.

    `stop_reason == "refusal"` is the SDK's native structured refusal
    signal; a model-authored refusal written as ordinary text with a
    different stop_reason (e.g. "end_turn") is left as VALID_TEXT.

    Branch order matters: refusal and truncation stop-reason evidence are
    both checked BEFORE the generic empty/whitespace text-shape checks, so
    that e.g. whitespace-only text produced under `stop_reason ==
    "max_tokens"` is classified TRUNCATED, not WHITESPACE_ONLY_TEXT -- the
    terminal reason is real, observed evidence and must not be silently
    discarded just because the leftover text happens to be blank.
    """
    stop_reason = response.stop_reason
    content = response.content

    if not content:
        if stop_reason == "refusal":
            return Observation(
                text="", kind=ObservationKind.PROVIDER_REFUSAL, finish_reason=stop_reason
            )
        if stop_reason in _TRUNCATION_STOP_REASONS:
            return Observation(
                text="", kind=ObservationKind.TRUNCATED, finish_reason=stop_reason
            )
        return Observation(text="", kind=ObservationKind.EMPTY_TEXT, finish_reason=stop_reason)

    first_block = content[0]

    if getattr(first_block, "type", None) != "text":
        return Observation(
            text="", kind=ObservationKind.NON_TEXT_TERMINAL, finish_reason=stop_reason
        )

    text = first_block.text

    if stop_reason == "refusal":
        return Observation(text=text, kind=ObservationKind.PROVIDER_REFUSAL, finish_reason=stop_reason)

    if stop_reason in _TRUNCATION_STOP_REASONS:
        return Observation(text=text, kind=ObservationKind.TRUNCATED, finish_reason=stop_reason)

    if not text:
        return Observation(text="", kind=ObservationKind.EMPTY_TEXT, finish_reason=stop_reason)

    if text.strip() == "":
        return Observation(
            text=text, kind=ObservationKind.WHITESPACE_ONLY_TEXT, finish_reason=stop_reason
        )

    return Observation(text=text, kind=ObservationKind.VALID_TEXT, finish_reason=stop_reason)


class AnthropicClient(ModelClient):
    """Anthropic model client implementation.

    Uses the Anthropic API to interact with Claude models.
    Requires ANTHROPIC_API_KEY environment variable to be set.
    """

    def __init__(self, config: ModelConfig):
        """Initialize Anthropic client.

        Args:
            config: ModelConfig with Anthropic-specific settings
        """
        super().__init__(config)
        self.client = Anthropic(api_key=self.api_key)

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
            **kwargs: Additional Anthropic API parameters

        Returns:
            A typed Observation. See ModelClient.generate.
        """
        messages = [{"role": "user", "content": prompt}]

        # Build API params - Claude Sonnet 4.5 doesn't allow both temperature and top_p
        api_params = {
            "model": self.config.model_name,
            "messages": messages,
            "system": system_prompt or "",
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
        }
        # Only add temperature (not top_p) to avoid Claude API conflict
        api_params["temperature"] = kwargs.get("temperature", self.config.temperature)

        try:
            response = self.client.messages.create(**api_params)
        except anthropic.AnthropicError as e:
            return Observation(
                text="",
                kind=ObservationKind.PROVIDER_ERROR,
                error=f"{type(e).__name__}: {e}",
            )

        return _classify_anthropic_response(response)

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
            **kwargs: Additional Anthropic API parameters

        Returns:
            A typed Observation. See ModelClient.generate.
        """
        # Build API params - Claude Sonnet 4.5 doesn't allow both temperature and top_p
        api_params = {
            "model": self.config.model_name,
            "messages": turns,
            "system": system_prompt or "",
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
        }
        # Only add temperature (not top_p) to avoid Claude API conflict
        api_params["temperature"] = kwargs.get("temperature", self.config.temperature)

        try:
            response = self.client.messages.create(**api_params)
        except anthropic.AnthropicError as e:
            return Observation(
                text="",
                kind=ObservationKind.PROVIDER_ERROR,
                error=f"{type(e).__name__}: {e}",
            )

        return _classify_anthropic_response(response)

    def get_name(self) -> str:
        """Get the model's display name.

        Returns:
            The model name from config
        """
        return self.config.model_name
