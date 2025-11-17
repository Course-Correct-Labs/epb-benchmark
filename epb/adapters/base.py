"""Base adapter interface for EPB model clients."""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ModelConfig:
    """Configuration for a model adapter.

    Attributes:
        provider: The model provider ("openai", "anthropic", etc.)
        model_name: The specific model name
        api_key_env: Name of the environment variable containing the API key
        temperature: Sampling temperature (default: 0.7)
        max_tokens: Maximum tokens to generate (default: 1000)
        top_p: Nucleus sampling parameter (default: 1.0)
    """

    provider: str
    model_name: str
    api_key_env: str = "API_KEY"
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0

    def get_api_key(self) -> str:
        """Retrieve API key from environment variable.

        Returns:
            API key string

        Raises:
            ValueError: If API key environment variable is not set
        """
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise ValueError(
                f"API key not found. Please set the {self.api_key_env} environment variable."
            )
        return api_key


class ModelClient(ABC):
    """Abstract base class for model adapters.

    All model adapters must implement this interface to be compatible with EPB.
    This allows EPB to treat different models as black boxes with a uniform interface.
    """

    def __init__(self, config: ModelConfig):
        """Initialize the model client with configuration.

        Args:
            config: ModelConfig instance with provider, model name, and parameters
        """
        self.config = config
        self.api_key = config.get_api_key()

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """Generate a response to a single prompt.

        Args:
            prompt: The user prompt to send to the model
            system_prompt: Optional system prompt to set context
            **kwargs: Additional provider-specific parameters

        Returns:
            The model's response as a string
        """
        pass

    @abstractmethod
    def generate_chat(
        self,
        turns: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """Generate a response given a conversation history.

        Args:
            turns: List of conversation turns, each with 'role' and 'content'
                  Example: [{"role": "user", "content": "Hello"},
                           {"role": "assistant", "content": "Hi!"}]
            system_prompt: Optional system prompt to set context
            **kwargs: Additional provider-specific parameters

        Returns:
            The model's response as a string
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get the model's display name.

        Returns:
            A string identifying the model (e.g., "gpt-4", "claude-3-sonnet")
        """
        pass
