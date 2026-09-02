"""Phase 3A result architecture: the frozen two-axis measurement/validation
model from EPB_PHASE2_EVIDENCE_SEMANTICS.md Sec 8.

This module implements REPRESENTATION only -- the shape a scorer's result
takes. It does not decide, for any battery, which scientific condition
produces which `MeasurementState`. That mapping is supplied by
`epb.scoring.result_adapter` (Phase 3A: reuses the existing Phase 1
blocked/scoreable condition unchanged) and, in a later phase, by each
battery's frozen Phase 2 evidence-usability rule (Phase 3B).

Two axes (Phase 2 Sec 8.1/8.2), kept as two separate fields because they
answer two different questions that must never be conflated back into one:

- `measurement_state` -- did *this run* produce a computable measurement?
- `validation_status` -- is the measurement *pathway* scientifically
  established, independent of whether this run reached a measurement?

`canonical_consumption_eligible` (Sec 8.3) is derived from both axes. It is
implemented as a read-only property, not a stored field, so no call site can
set it directly or set it inconsistently with the two axes it depends on.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple


class MeasurementState(str, Enum):
    """Axis 1 (Phase 2 Sec 8.1) -- did this run produce a computable result?

    Exact vocabulary frozen by Phase 2; Phase 3A must not rename or add to
    it (this phase's governing prompt Sec 2).
    """

    SCORED = "scored"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NO_APPLICABLE_EVIDENCE = "no_applicable_evidence"
    EXECUTION_FAILURE = "execution_failure"
    SCORING_ERROR = "scoring_error"


class ValidationStatus(str, Enum):
    """Axis 2 (Phase 2 Sec 8.2) -- how scientifically established is this
    measurement pathway, independent of whether this run reached a
    measurement?

    Exact vocabulary frozen by Phase 2; Phase 3A must not rename or add to
    it (this phase's governing prompt Sec 2).
    """

    FROZEN = "frozen"
    PROVISIONAL = "provisional"
    UNRESOLVED = "unresolved"


# Schema-version marker for this result shape, persisted alongside battery
# results so a reader can tell which version of the result architecture
# produced a given record. Deliberately a distinct constant from
# `epb.adapters.base.OBSERVATION_SCHEMA_VERSION` -- that version describes
# per-observation provenance records (Phase 1); this one describes the
# scorer/result-quantity shape (Phase 3A). The two must never be conflated
# or silently reused for each other (this phase's governing prompt Sec 10).
RESULT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class QuantityResult:
    """A single scientific quantity's full two-axis result record.

    One instance represents one measurable quantity (e.g. Mirror Loop's
    `collapse_rate`, or Confabulation's `persistence`) for one run. Batteries
    that report more than one independent quantity (Confabulation) use one
    `QuantityResult` per quantity -- see `epb.scoring.result_adapter.
    ConfabulationResult` -- never a single shared record for both.

    Attributes:
        quantity: Stable dotted identifier for what this measures, e.g.
            "mirror_loop.collapse" or "confabulation.persistence".
        measurement_state: Axis 1 -- see `MeasurementState`.
        validation_status: Axis 2 -- see `ValidationStatus`. Set per-battery
            by the caller (Phase 2 Sec 16/16.2's frozen current statuses);
            never derived from `measurement_state`.
        value: The computed pathology score/rate, only when
            `measurement_state == SCORED`. Always `None` otherwise -- a
            non-`SCORED` state must never carry a numeric substitute
            (this phase's governing prompt Sec 5/Sec 9.15).
        planned: How many evidence opportunities this quantity's Phase 1
            evidence-unit count describes for this run. `None` when not
            determined (e.g. a genuine scoring error before counting).
        applicable: How many of `planned` currently apply, under Phase 1's
            *existing* meaning (transitional -- see module docstring of
            `epb.scoring.result_adapter`; Phase 3B will supply each
            battery's true Phase 2 evidence-unit definition).
        usable: How many of `applicable` were actually valid/usable,
            under the same transitional Phase 1 meaning.
        blocked: Diagnostic detail for each specific evidence item that
            blocked this measurement (task_id/reason/observation_kinds),
            carried over verbatim from `UnscoreableEvidenceError.blocked`
            when `measurement_state == INSUFFICIENT_EVIDENCE`. Empty
            otherwise.
        error: A short diagnostic message, populated only for
            `EXECUTION_FAILURE`/`SCORING_ERROR` -- a genuine implementation
            anomaly, never a scientific evidence condition.
        details: The full legacy Phase 1 result dict, when
            `measurement_state == SCORED` -- preserved verbatim for
            backward-compatible consumers and audit, not re-derived.
        schema_version: `RESULT_SCHEMA_VERSION` at construction time.
    """

    quantity: str
    measurement_state: MeasurementState
    validation_status: ValidationStatus
    value: Optional[float] = None
    planned: Optional[int] = None
    applicable: Optional[int] = None
    usable: Optional[int] = None
    blocked: Tuple[Dict[str, Any], ...] = field(default_factory=tuple)
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    schema_version: int = RESULT_SCHEMA_VERSION

    @property
    def coverage(self) -> Optional[float]:
        """usable / applicable, or None when undefined (Phase 2 Sec 8:
        coverage is defined only when applicable > 0). Never converted to
        0 -- an undefined coverage is not the same claim as zero coverage.
        """
        if not self.applicable:
            return None
        if self.usable is None:
            return None
        return self.usable / self.applicable

    @property
    def canonical_consumption_eligible(self) -> bool:
        """Derived per Phase 2 Sec 8.3. Not a stored field: there is no
        constructor parameter for this value, so a call site cannot set it
        directly or set it inconsistently with the two axes it depends on.
        """
        return (
            self.measurement_state == MeasurementState.SCORED
            and self.validation_status == ValidationStatus.FROZEN
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-safe dict for persistence."""
        return {
            "quantity": self.quantity,
            "measurement_state": self.measurement_state.value,
            "validation_status": self.validation_status.value,
            "value": self.value,
            "planned": self.planned,
            "applicable": self.applicable,
            "usable": self.usable,
            "coverage": self.coverage,
            "canonical_consumption_eligible": self.canonical_consumption_eligible,
            "blocked": list(self.blocked),
            "error": self.error,
            "details": self.details,
            "schema_version": self.schema_version,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "QuantityResult":
        """Reconstruct a QuantityResult from a persisted record.

        `coverage` and `canonical_consumption_eligible` are not read back
        from `data` -- they are always re-derived from the other fields, so
        a hand-edited or stale persisted value can never desynchronize them
        from the two axes that define them.
        """
        return QuantityResult(
            quantity=data["quantity"],
            measurement_state=MeasurementState(data["measurement_state"]),
            validation_status=ValidationStatus(data["validation_status"]),
            value=data.get("value"),
            planned=data.get("planned"),
            applicable=data.get("applicable"),
            usable=data.get("usable"),
            blocked=tuple(data.get("blocked") or []),
            error=data.get("error"),
            details=data.get("details"),
            schema_version=data.get("schema_version", RESULT_SCHEMA_VERSION),
        )
