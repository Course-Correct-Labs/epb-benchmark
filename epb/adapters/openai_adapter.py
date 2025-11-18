"""OpenAI model adapter for EPB."""

from typing import Any, Dict, List, Optional

from openai import OpenAI

from epb.adapters.base import ModelClient, ModelConfig


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
    ) -> str:
        """Generate a response to a single prompt.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            **kwargs: Additional OpenAI API parameters

        Returns:
            The model's response text
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

        response = self.client.chat.completions.create(**body)

        return response.choices[0].message.content or ""

    def generate_chat(
        self,
        turns: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """Generate a response given conversation history.

        Args:
            turns: List of conversation turns with 'role' and 'content'
            system_prompt: Optional system prompt
            **kwargs: Additional OpenAI API parameters

        Returns:
            The model's response text
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

        response = self.client.chat.completions.create(**body)

        return response.choices[0].message.content or ""

    def get_name(self) -> str:
        """Get the model's display name.

        Returns:
            The model name from config
        """
        return self.config.model_name
