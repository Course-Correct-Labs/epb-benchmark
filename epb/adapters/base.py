"""Base adapter interface for EPB model clients."""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class ObservationKind(str, Enum):
    """Typed classification of what a single model-generation call produced.

    Phase 0/0.5 established that the pre-Phase-1 contract (a bare `str`
    return value) collapsed materially different provider outcomes --
    genuine empty completion, provider refusal, truncation, a non-text
    terminal response, and an outright SDK/provider failure -- into an
    indistinguishable `""` before any battery's scoring code ever saw them.
    This is the smallest taxonomy that keeps those outcomes distinguishable,
    sized to what the currently-supported OpenAI and Anthropic SDKs actually
    expose (see EPB_PHASE1_FOUNDATIONAL_REPAIR.md for the offline SDK
    introspection this was grounded against). It is deliberately not
    expanded for provider features (tools, extended thinking) that no
    current EPB config uses.
    """

    VALID_TEXT = "valid_text"
    EMPTY_TEXT = "empty_text"
    WHITESPACE_ONLY_TEXT = "whitespace_only_text"
    PROVIDER_REFUSAL = "provider_refusal"
    TRUNCATED = "truncated"
    NON_TEXT_TERMINAL = "non_text_terminal"
    PROVIDER_ERROR = "provider_error"
    ORCHESTRATION_ERROR = "orchestration_error"
    # Only ever produced when reading a pre-Phase-1 artifact whose bare-string
    # shape does not let us safely infer one of the kinds above. Never
    # produced by a live adapter call.
    LEGACY_UNKNOWN = "legacy_unknown"


# Schema-version marker for the richer per-observation record shape
# introduced in this phase. Persisted alongside battery results so a reader
# (human or code) can tell a new typed-observation record apart from a
# pre-Phase-1 bare string without guessing. Deliberately independent of
# `epb.__version__` / the pyproject.toml package version -- see this
# phase's governing prompt Sec 0.6 and EPB_PHASE0_5_VNEXT_DESIGN.md Sec 18.
OBSERVATION_SCHEMA_VERSION = 1


@dataclass
class Observation:
    """A single typed outcome of one model-generation call.

    Attributes:
        text: The extracted text, when any exists. Populated for
            VALID_TEXT, EMPTY_TEXT (as ""), WHITESPACE_ONLY_TEXT, TRUNCATED,
            and PROVIDER_REFUSAL (when the provider surfaces refusal text).
            Always "" for NON_TEXT_TERMINAL, PROVIDER_ERROR, and
            ORCHESTRATION_ERROR -- there is no model text to report there.
        kind: The ObservationKind classification.
        finish_reason: The raw provider-reported finish/stop-reason string
            where the provider exposes one (e.g. OpenAI "length", Anthropic
            "max_tokens"). None when not available or not applicable.
        error: A short, safe (no secrets, no raw provider objects)
            diagnostic message. Populated only for PROVIDER_ERROR,
            ORCHESTRATION_ERROR, and NON_TEXT_TERMINAL.
    """

    text: str
    kind: ObservationKind
    finish_reason: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-safe dict for persistence."""
        return {
            "text": self.text,
            "kind": self.kind.value,
            "finish_reason": self.finish_reason,
            "error": self.error,
        }

    @staticmethod
    def from_dict(data: Any) -> "Observation":
        """Reconstruct an Observation from a persisted JSONL record.

        Accepts both the new typed-record shape (a dict with "text"/"kind")
        and pre-Phase-1 bare strings, per the legacy-read compatibility
        boundary: a bare string is classified from the text alone, never
        by guessing why it looks the way it does.

        VALID_TEXT is not a text-shape category -- it is a claim that the
        observation system directly observed enough provider/runtime
        information (a finish/stop reason ruling out truncation, a
        tool-call/non-text terminal state, or a structured refusal signal)
        to classify the response as a genuine, clean completion. A
        pre-Phase-1 bare string carries none of that metadata: the old
        adapters wrote only `response.choices[0].message.content or ""` /
        `content[0].text`, discarding finish_reason/stop_reason entirely
        (Checkpoint Sec 4). Phase 1's own OpenAI/Anthropic classifiers prove
        why non-emptiness alone cannot stand in for that evidence: a
        non-empty response can still be TRUNCATED when finish/stop metadata
        says so. So a non-empty, non-whitespace legacy string is classified
        LEGACY_UNKNOWN, not VALID_TEXT -- its text is preserved exactly, but
        no provider/runtime state (clean completion, truncation, refusal,
        error) is invented for it.

        An exact-empty stored string is likewise LEGACY_UNKNOWN rather than
        EMPTY_TEXT, for the same reason: Phase 0 documented it as the
        genuinely ambiguous case (it could have been a real empty
        completion, a masked refusal, a masked truncation, or a masked
        tool-call/error), and EMPTY_TEXT -- like VALID_TEXT -- is only ever
        assigned by a live adapter after finish/stop-reason evidence rules
        those alternatives out.

        Whitespace-only stored text is ALSO LEGACY_UNKNOWN, not
        WHITESPACE_ONLY_TEXT -- this is a correction to an earlier version
        of this method, which treated whitespace-only shape as safe to
        classify on its own because (at the time) the live classifiers
        assigned WHITESPACE_ONLY_TEXT purely from `text.strip() == ""`
        without consulting finish/stop-reason evidence. That premise
        stopped being true once the live OpenAI/Anthropic classifiers were
        corrected to give truncation/refusal/non-text-terminal evidence
        precedence over generic text shape (e.g. `"   "` with
        `finish_reason == "length"` is TRUNCATED, not
        WHITESPACE_ONLY_TEXT, whenever that evidence is available). A
        pre-Phase-1 bare string never retained that evidence either way, so
        a stored whitespace-only string proves only that the retained text
        is whitespace -- not that the original observation state was
        WHITESPACE_ONLY_TEXT rather than a masked truncation or other
        terminal condition. The stored text's shape remains inspectable
        directly via `.text` if ever needed; it is simply no longer
        promoted into a provider/runtime-state kind here.
        """
        if isinstance(data, str):
            # Every pre-Phase-1 bare string -- empty, whitespace-only, or
            # non-empty alike -- is LEGACY_UNKNOWN: none of them can be
            # promoted to EMPTY_TEXT, WHITESPACE_ONLY_TEXT, or VALID_TEXT
            # without inventing provider/runtime provenance the historical
            # artifact never recorded. Original text preserved exactly.
            return Observation(text=data, kind=ObservationKind.LEGACY_UNKNOWN)

        if isinstance(data, dict):
            kind_value = data.get("kind")
            try:
                kind = ObservationKind(kind_value)
            except ValueError:
                kind = ObservationKind.LEGACY_UNKNOWN
            return Observation(
                text=data.get("text") or "",
                kind=kind,
                finish_reason=data.get("finish_reason"),
                error=data.get("error"),
            )

        # Anything else unexpected (None, a list, ...): treat as an unknown-
        # provenance record rather than crash a scorer on a malformed entry.
        return Observation(text="", kind=ObservationKind.LEGACY_UNKNOWN)


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
    ) -> Observation:
        """Generate a response to a single prompt.

        Args:
            prompt: The user prompt to send to the model
            system_prompt: Optional system prompt to set context
            **kwargs: Additional provider-specific parameters

        Returns:
            A typed Observation describing what the provider returned.
            Expected provider-level failure modes (SDK exceptions, refusals,
            truncation, non-text terminal responses) are classified into the
            Observation rather than raised; only a genuinely unanticipated
            error should propagate as an exception.
        """
        pass

    @abstractmethod
    def generate_chat(
        self,
        turns: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> Observation:
        """Generate a response given a conversation history.

        Args:
            turns: List of conversation turns, each with 'role' and 'content'
                  Example: [{"role": "user", "content": "Hello"},
                           {"role": "assistant", "content": "Hi!"}]
            system_prompt: Optional system prompt to set context
            **kwargs: Additional provider-specific parameters

        Returns:
            A typed Observation describing what the provider returned. See
            `generate` for the failure-handling contract.
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get the model's display name.

        Returns:
            A string identifying the model (e.g., "gpt-4", "claude-3-sonnet")
        """
        pass
