"""Anthropic model adapter for EPB."""

from typing import Any, Dict, List, Optional

from anthropic import Anthropic

from epb.adapters.base import ModelClient, ModelConfig


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
    ) -> str:
        """Generate a response to a single prompt.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            **kwargs: Additional Anthropic API parameters

        Returns:
            The model's response text
        """
        messages = [{"role": "user", "content": prompt}]

        response = self.client.messages.create(
            model=self.config.model_name,
            messages=messages,
            system=system_prompt or "",
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            top_p=kwargs.get("top_p", self.config.top_p),
        )

        # Extract text from response
        if response.content and len(response.content) > 0:
            return response.content[0].text
        return ""

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
            **kwargs: Additional Anthropic API parameters

        Returns:
            The model's response text
        """
        response = self.client.messages.create(
            model=self.config.model_name,
            messages=turns,
            system=system_prompt or "",
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            top_p=kwargs.get("top_p", self.config.top_p),
        )

        # Extract text from response
        if response.content and len(response.content) > 0:
            return response.content[0].text
        return ""

    def get_name(self) -> str:
        """Get the model's display name.

        Returns:
            The model name from config
        """
        return self.config.model_name
