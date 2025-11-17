"""OpenAI model adapter for EPB."""

from typing import Any, Dict, List, Optional

from openai import OpenAI

from epb.adapters.base import ModelClient, ModelConfig


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

        response = self.client.chat.completions.create(
            model=self.config.model_name,
            messages=messages,
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            top_p=kwargs.get("top_p", self.config.top_p),
        )

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

        response = self.client.chat.completions.create(
            model=self.config.model_name,
            messages=messages,
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            top_p=kwargs.get("top_p", self.config.top_p),
        )

        return response.choices[0].message.content or ""

    def get_name(self) -> str:
        """Get the model's display name.

        Returns:
            The model name from config
        """
        return self.config.model_name
