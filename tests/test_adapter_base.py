"""Tests for the typed Observation contract (Phase 1 Area 1).

These tests cover the Observation/ObservationKind data model itself:
serialization round-tripping and the legacy-read compatibility boundary
(Sec 13.1) that lets pre-Phase-1 bare-string artifacts be read without
inventing provenance that was never recorded.
"""

from epb.adapters.base import Observation, ObservationKind


def test_observation_to_dict_round_trip():
    """A typed Observation survives a to_dict/from_dict round trip."""
    obs = Observation(
        text="Hello world",
        kind=ObservationKind.VALID_TEXT,
        finish_reason="stop",
        error=None,
    )
    restored = Observation.from_dict(obs.to_dict())
    assert restored.text == "Hello world"
    assert restored.kind == ObservationKind.VALID_TEXT
    assert restored.finish_reason == "stop"
    assert restored.error is None


def test_observation_to_dict_preserves_error_kinds():
    """Error-kind observations preserve their diagnostic message."""
    obs = Observation(
        text="",
        kind=ObservationKind.PROVIDER_ERROR,
        error="RateLimitError: rate limit exceeded",
    )
    d = obs.to_dict()
    assert d["kind"] == "provider_error"
    assert d["error"] == "RateLimitError: rate limit exceeded"
    assert d["text"] == ""

    restored = Observation.from_dict(d)
    assert restored.kind == ObservationKind.PROVIDER_ERROR
    assert restored.error == "RateLimitError: rate limit exceeded"


def test_observation_from_dict_unrecognized_kind_becomes_legacy_unknown():
    """An unrecognized/corrupt kind string does not crash the loader."""
    restored = Observation.from_dict({"text": "some text", "kind": "not_a_real_kind"})
    assert restored.kind == ObservationKind.LEGACY_UNKNOWN
    assert restored.text == "some text"


def test_observation_from_dict_malformed_record_does_not_crash():
    """A malformed / unexpected record type is handled, not raised."""
    for bad in (None, [], 42, {}):
        restored = Observation.from_dict(bad)
        assert restored.kind in (ObservationKind.LEGACY_UNKNOWN,)
        assert restored.text == ""


# --- Legacy bare-string compatibility (Sec 13.1) ---
#
# Pre-Phase-1 artifacts store the raw string the old adapters produced via
# `response.choices[0].message.content or ""` / `content[0].text`. The
# loader must classify these without inventing a provider cause it was
# never told.

def test_legacy_nonempty_string_is_legacy_unknown_not_valid_text():
    """A non-empty, non-whitespace legacy string preserves its text exactly
    but is NOT classified VALID_TEXT.

    VALID_TEXT asserts that the observation system directly observed enough
    provider/runtime information (finish/stop-reason evidence ruling out
    truncation, a tool-call terminal state, or a structured refusal) to
    know this was a genuine, clean completion. A pre-Phase-1 bare string
    carries none of that metadata -- Phase 1's own classifiers prove why
    non-emptiness alone can't stand in for it: a non-empty response can
    still be TRUNCATED when finish/stop metadata says so. So a legacy
    non-empty string is classified LEGACY_UNKNOWN, never VALID_TEXT, no
    matter how clean the text looks.
    """
    text = "The mitochondria is the powerhouse of the cell."
    obs = Observation.from_dict(text)
    assert obs.kind == ObservationKind.LEGACY_UNKNOWN
    assert obs.text == text  # original text preserved byte-for-byte


def test_legacy_whitespace_only_string_is_legacy_unknown_not_whitespace_only_text():
    """Whitespace-only legacy text is LEGACY_UNKNOWN, not WHITESPACE_ONLY_TEXT.

    Correction: an earlier version of this rule classified whitespace-only
    legacy text as WHITESPACE_ONLY_TEXT on the premise that the live
    classifiers assign that kind from text shape alone. That premise no
    longer holds -- the live classifiers now give truncation/refusal/
    non-text-terminal evidence precedence over whitespace shape whenever
    that evidence is available (e.g. "   " + finish_reason == "length" is
    TRUNCATED). A pre-Phase-1 bare string never retained that evidence, so
    stored whitespace-only text proves only that the retained text is
    whitespace -- not that the original observation was genuinely
    WHITESPACE_ONLY_TEXT rather than a masked truncation or other terminal
    condition. The stored text remains available via `.text` for direct
    shape inspection; it is just no longer promoted to a provider/runtime-
    state kind.
    """
    obs = Observation.from_dict("   \n\t  ")
    assert obs.kind == ObservationKind.LEGACY_UNKNOWN
    assert obs.text == "   \n\t  "  # original text preserved byte-for-byte


def test_legacy_exact_empty_string_is_unknown_not_empty_text():
    """An exact-empty legacy string is the genuinely ambiguous Phase 0 case.

    It must NOT be classified EMPTY_TEXT, because that would assert "the
    provider genuinely returned nothing" -- an inference about provider
    cause the historical artifact never recorded (it could equally have
    been a masked refusal, truncation, tool-call, or provider error under
    the pre-Phase-1 contract). It is classified LEGACY_UNKNOWN instead.
    """
    obs = Observation.from_dict("")
    assert obs.kind == ObservationKind.LEGACY_UNKNOWN
    assert obs.text == ""


def test_legacy_unknown_never_produced_by_a_typed_record():
    """A fully-formed new-schema record is never coerced to LEGACY_UNKNOWN."""
    obs = Observation.from_dict({"text": "", "kind": "empty_text", "finish_reason": "stop"})
    assert obs.kind == ObservationKind.EMPTY_TEXT
